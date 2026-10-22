"""Thin full-episode adapter over maintained RWKV-PEFT and Hugging Face PEFT.

Layer equations and recurrence are the attributed upstream implementation.
Only token/state layout, parameter selection and artifact boundaries live here.
"""
import os
import sys
from pathlib import Path
from types import SimpleNamespace
import torch
from torch import nn
from . import statetune_core as core
from .rwkv7_layout import RWKV7Layout

TARGET_SUFFIXES=('receptance','key','value','output')
_SOURCE=None


def load_source(reference):
    """Bind the full locally adapted PEFT source, including uncommitted owner work."""
    global _SOURCE
    manifest=core.read_sealed_json(reference['path'],reference['sha256']);root=Path(manifest['root']).resolve()
    for row in manifest['files']:core.verify_file(root/row['path'],row['sha256'])
    if _SOURCE is not None:core.require(_SOURCE==reference['sha256'],'different PEFT source is already loaded')
    for name,module in list(sys.modules.items()):
        if name=='rwkvt' or name.startswith('rwkvt.'):
            file=getattr(module,'__file__',None)
            if file is not None:
                sealed=Path(file).resolve().is_relative_to(root)
            else:
                # PEP 420 packages (rwkvt.operator) have no __file__. Every
                # search location must be the sealed package directory.
                paths=list(getattr(module,'__path__',()))
                directory=root.joinpath(*name.split('.'))
                sealed=bool(paths) and all(Path(path).resolve()==directory for path in paths)
                sealed=sealed and any((root/row['path']).is_relative_to(directory) for row in manifest['files'])
            core.require(sealed,'unsealed PEFT module was imported: '+name)
    if str(root) not in sys.path:sys.path.insert(0,str(root))
    _SOURCE=reference['sha256']
    return manifest


PRECISIONS=dict(float16='float16',bfloat16='bfloat16',float32='float32')
TRITON_F32=('ieee','tf32','tf32x3')


def configure_precision(precision):
    """Freeze every numerical choice that the qualification gates measured.

    torch.backends.cuda.matmul.allow_tf32 does not reach Triton: tl.dot on
    FP32 operands follows TRITON_F32_DEFAULT (TF32 when unset). Trainable
    State and adapters always stay FP32; only the frozen base may be lowered,
    and any lowering must be qualified again under the same gates.
    """
    import torch
    core.require(isinstance(precision,dict) and set(precision)=={'base','state','adapter','triton_f32_default'},
                 'explicit base/state/adapter/Triton precision is required')
    core.require(precision['base'] in PRECISIONS,'unsupported PEFT base precision')
    core.require(precision['state']=='float32' and precision['adapter']=='float32','trainable State and adapters must be FP32')
    triton=precision['triton_f32_default'];core.require(triton in TRITON_F32,'unsupported Triton FP32 precision')
    core.require(os.environ.get('TRITON_F32_DEFAULT',triton)==triton,'TRITON_F32_DEFAULT differs from registration')
    os.environ['TRITON_F32_DEFAULT']=triton
    if 'triton' in sys.modules:
        knobs=getattr(getattr(sys.modules['triton'],'knobs',None),'language',None)
        core.require(knobs is None or getattr(knobs,'fp32_default',triton)==triton,'loaded Triton FP32 precision differs')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    return dict(precision,torch_matmul_allow_tf32=False,cudnn_allow_tf32=False)


def verify_precision(model,precision):
    """Fail before any forward if a cast silently changed a frozen choice."""
    import torch
    base=getattr(torch,precision['base']);trainable=trainable_parameters(model)
    core.require(all(p.dtype==torch.float32 for p in trainable.values()),'trainable parameter is not FP32')
    states=[name for name,_ in model.named_parameters() if name.endswith('.time_state')]
    core.require(bool(states) and all(p.dtype==torch.float32 for n,p in model.named_parameters() if n in states),'time_state is not FP32')
    frozen=[p for n,p in model.named_parameters() if n not in trainable and n not in states]
    core.require(bool(frozen) and all(p.dtype==base for p in frozen),'frozen base precision differs from registration')
    core.require(os.environ.get('TRITON_F32_DEFAULT')==precision['triton_f32_default'],'Triton FP32 precision changed')
    core.require(not torch.backends.cuda.matmul.allow_tf32 and not torch.backends.cudnn.allow_tf32,'PyTorch TF32 was re-enabled')


def configure():
    expected=dict(WKV='fla',RWKV_TRAIN_TYPE='infctx',RWKV_MY_TESTING='x070',FUSED_KERNEL='0',
                  RWKV_HEAD_SIZE_A='64',RWKV_FLOAT_MODE='bf16')
    for key,value in expected.items():
        core.require(key not in os.environ or os.environ[key]==value,f'PEFT backend environment differs: {key}')
        os.environ[key]=value


def construct(layout,*,context_tokens):
    """Construct on the caller's device (normally meta) without changing equations."""
    configure()
    core.require(_SOURCE is not None,'explicit locally adapted PEFT source manifest is required')
    from rwkvt.rwkv7.model import RWKV7
    core.require(layout.head_size==64,'RWKV-PEFT backend requires head size64')
    args=SimpleNamespace(n_embd=layout.width,n_layer=layout.layers,dim_att=layout.width,
        head_size_a=layout.head_size,head_size_divisor=8,vocab_size=layout.vocab,
        my_testing='x070',chunk_ctx=context_tokens,ctx_len=context_tokens,grad_cp=1,
        train_type='infctx',peft='state',dropout=0)

    class CarriedRWKV7(RWKV7):
        def forward(self,tokens,state=None,*,return_state=False):
            core.require(tokens.ndim==2 and tokens.shape[0]==1 and 0<tokens.shape[1]<=self.context_tokens,
                         'PEFT requires one complete nonempty chunk')
            if state is None:
                shifts=self.emb.weight.new_zeros(self.layout.layers,2,1,self.layout.width)
                wkv=torch.stack([block.att.time_state.transpose(-1,-2) for block in self.blocks]).unsqueeze(1)
            else:
                core.require(len(state)==self.layout.layers and all(len(layer)==3 for layer in state),'PEFT carried State layer count differs')
                core.require(all(layer[0].dtype==torch.float32 and tuple(layer[0].shape)==(1,self.layout.heads,64,64)
                    and all(tuple(x.shape)==(1,self.layout.width) and x.dtype==self.emb.weight.dtype for x in layer[1:]) for layer in state),
                    'PEFT requires FP32 recurrence plus two token shifts')
                wkv=torch.stack([layer[0] for layer in state])
                shifts=torch.stack([torch.stack([layer[1],layer[2]]) for layer in state])
            logits,next_shifts,next_wkv=super().forward_infctx(tokens,shifts,wkv)
            carried=tuple((next_wkv[i],next_shifts[i,0],next_shifts[i,1]) for i in range(self.layout.layers))
            return (logits,carried) if return_state else logits

    model=CarriedRWKV7(args);model.layout=layout;model.context_tokens=context_tokens
    model.config={'model_type':'rwkv','tie_word_embeddings':False};model.name_or_path=''
    for block in model.blocks:
        block.att.register_parameter('time_state',nn.Parameter(torch.zeros(layout.heads,64,64,dtype=torch.float32)))
    return model


def trainable_parameters(model):
    values={name:p for name,p in model.named_parameters() if p.requires_grad}
    core.require(bool(values),'PEFT optimizer has no trainable parameters')
    return values


def select_method(model,method,*,rank=64,alpha=128):
    core.require(method in ('statetune','lora'),'unknown PEFT method')
    if method=='statetune':
        core.freeze_for_state_tuning(model,layers=model.layout.layers)
        return model
    from peft import LoraConfig,get_peft_model
    targets=[name for name,module in model.named_modules() if isinstance(module,nn.Linear) and name.startswith('blocks.') and name.rsplit('.',1)[-1] in TARGET_SUFFIXES]
    core.require(len(targets)==model.layout.layers*6,'LoRA must cover all four attention and both FFN linears')
    wrapped=get_peft_model(model,LoraConfig(r=rank,lora_alpha=alpha,lora_dropout=0,bias='none',
                                          target_modules=targets,task_type=None))
    core.require(all('lora_' in name for name in trainable_parameters(wrapped)),'LoRA made a base parameter trainable')
    wrapped.eval()
    return wrapped


def build(spec,*,method,device='cuda'):
    import json
    precision=spec.get('precision');attested=configure_precision(precision)
    dtype=getattr(torch,precision['base'])
    load_source(spec['peft_source'])
    layout=RWKV7Layout.from_config(json.loads((Path(spec['model_artifact'])/'config.json').read_text()))
    with torch.device('meta'):model=construct(layout,context_tokens=spec['context_tokens'])
    core.load_frozen_base(model,spec['base']['path'],spec['base']['sha256'],layers=layout.layers)
    for block in model.blocks:
        block.att.time_state=nn.Parameter(torch.zeros(layout.heads,64,64,dtype=torch.float32))
    model.to(device=device,dtype=dtype)
    # Only the freshly zero-initialized State exists here. Restore FP32 before
    # selecting trainables, loading a trained State, or attaching FP32 adapters.
    # A later whole-model cast would change those parameters as well.
    for block in model.blocks:
        block.att.time_state=nn.Parameter(block.att.time_state.detach().float())
    model=select_method(model,method)
    if method=='lora':
        # PEFT follows a FP32 base but would otherwise keep autocast choices implicit.
        for name,value in trainable_parameters(model).items():value.data=value.data.float()
    verify_precision(model,precision)
    model.precision=attested
    model.eval()
    return model


def save_adapter(model,path):
    """Use PEFT's standard adapter-only format, never a copied base checkpoint."""
    path=Path(path);core.require(not path.exists(),'adapter output already exists')
    core.require(all('lora_' in name for name in trainable_parameters(model)),'not a LoRA model')
    model.save_pretrained(str(path),safe_serialization=True,save_embedding_layers=False)
    return {p.name:dict(path=str(p),sha256=core.sha256_file(p)) for p in sorted(path.iterdir()) if p.is_file()}


def merge_checkpoint(model,output,*,base_path,base_sha256,target_dtype='base'):
    """Merge with PEFT and round adapted weights once to the serving precision.

    The native loader consumes FP16 weights. Rounding a merged FP32 update
    back to BF16 first can erase an update that FP16 serving can represent.
    The registered target dtype applies only to
    adapted matrices; every non-adapted tensor stays bitwise equal to the base.
    """
    core.require(target_dtype in ('base','float16','bfloat16','float32'),'unsupported LoRA merge target dtype')
    path=Path(output);core.require(not path.exists(),'merged output already exists')
    targets={name.removeprefix('base_model.model.')+'.weight' for name,module in model.named_modules()
             if hasattr(module,'lora_A') and name.rsplit('.',1)[-1] in TARGET_SUFFIXES}
    core.require(len(targets)==model.layout.layers*6,'incomplete LoRA merge targets')
    base=torch.load(core.verify_file(base_path,base_sha256),map_location='cpu',weights_only=True,mmap=True)
    # PEFT otherwise rounds delta to the base dtype before adding it. Promote
    # first so a half-base adapter is added in FP32 and rounded only at export.
    base_dtype=next(model.parameters()).dtype
    model.float()
    merged=model.merge_and_unload(safe_merge=True)
    core.require(all(bool(torch.count_nonzero(block.att.time_state)==0) for block in merged.blocks),'LoRA initial State changed')
    values=merged.state_dict();state={}
    core.require(set(values)-{n for n in values if n.endswith('.time_state')}==set(base),'merged key set differs from base')
    for name,original in base.items():
        dtype=getattr(torch,target_dtype) if name in targets and target_dtype!='base' else original.dtype
        value=values[name].detach().to(device='cpu',dtype=dtype) if name in targets else original.clone()
        core.require(value.shape==original.shape and bool(torch.isfinite(value).all()),'merged tensor differs: '+name)
        core.require(name in targets or torch.equal(values[name].detach().cpu(),original.to(base_dtype).float()),
                     'non-adapted tensor changed: '+name)
        state[name]=value
    core.require(any(not torch.equal(state[name],base[name]) for name in targets),'merged LoRA changes no target weight')
    with path.open('xb') as stream:torch.save(state,stream);stream.flush();os.fsync(stream.fileno())
    return dict(path=str(path),sha256=core.sha256_file(path),base_sha256=base_sha256,
                changed_tensors=sorted(targets),target_dtype=target_dtype)
