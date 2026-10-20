"""Opt-in LoRA for RWKV7 attention/FFN linears, with the carried native State."""
import math
from pathlib import Path
import torch
from torch import nn
from torch.nn import functional as F

from . import cc_view_experiment as cc
from .statetune_core import require,sha256_file,verify_file
from .statetune_native_model import NativeGradientModel,norm_float,pure_producer

ADAPTER_SCHEMA='rwkv-lh.cc-view-lora.v1'


class LoRALinear(nn.Module):
    def __init__(self,base,*,rank,alpha):
        super().__init__();require(isinstance(base,nn.Linear) and base.bias is None,'LoRA requires a bias-free linear')
        require(type(rank) is int and rank>0 and alpha>0,'invalid LoRA rank/alpha')
        self.base=base;self.rank=rank;self.alpha=alpha;self.scale=alpha/rank
        base.requires_grad_(False)
        self.lora_a=nn.Parameter(torch.empty(rank,base.in_features,device=base.weight.device,dtype=torch.float32))
        self.lora_b=nn.Parameter(torch.zeros(base.out_features,rank,device=base.weight.device,dtype=torch.float32))
        nn.init.kaiming_uniform_(self.lora_a,a=math.sqrt(5))

    def forward(self,value):
        original=self.base(value)
        low=F.linear(F.linear(value,self.lora_a.to(value.dtype)),self.lora_b.to(value.dtype))
        return (original.float()+low.float()*self.scale).to(original.dtype)

    def delta(self):return (self.lora_b.float()@self.lora_a.float())*self.scale


def adapter_parameters(model):
    return {name:value for name,value in model.named_parameters() if name.endswith(('.lora_a','.lora_b')) or name in ('lora_a','lora_b')}


class CCViewLoRAModel(NativeGradientModel):
    """Differentiate all adapted linears, retaining the same recurrence kernel.

    NativeGradientModel custom backward nodes intentionally freeze base weights;
    this layer uses their documented equations so adapter gradients are actual
    parameter derivatives rather than detached patches to a frozen kernel.
    """
    def layer(self,x,previous_ffn,first,wkv,att_shift,ffn_shift,index):
        from .statetune_native_recurrence import recurrent
        block=self.blocks[index];att=block.att
        if index==0:normalized=norm_float(x,block.ln1).half()
        else:
            summed=x.float()+previous_ffn.float();normalized=norm_float(summed,block.ln1).half();x=summed.half()
        r,w,k,v,a,b,g,first=pure_producer(normalized,first,att_shift,att)
        batch,tokens,width=r.shape;shape=(batch,tokens,att.heads,width//att.heads)
        if wkv is None:wkv=att.time_state.transpose(-1,-2).unsqueeze(0).expand(batch,-1,-1,-1)
        y,carried=recurrent(*(value.reshape(shape).contiguous() for value in (r,w,k,v,a,b)),
            initial_state=wkv.contiguous(),decay_bias=att.w0.reshape(shape[-2:]).contiguous())
        norm=F.group_norm(y.float().reshape(batch*tokens,width),att.heads,
                         att.ln_x.weight.float(),att.ln_x.bias.float(),att.ln_x.eps).reshape(shape)
        residual=(r.float().reshape(shape)*k.float().reshape(shape)*att.r_k.float()).sum(-1,keepdim=True)*v.float().reshape(shape)
        attention=att.output(((norm+residual).reshape_as(g)*g.float()).half())
        summed=x.float()+attention.float();ffn_input=norm_float(summed,block.ln2).half()
        ffn=block.ffn(ffn_input,ffn_shift)
        return summed.half(),ffn,first,carried,normalized[:,-1].clone(),ffn_input[:,-1].clone()


def attach(model,*,rank=64,alpha=128):
    targets=[(name,module) for name,module in model.named_modules()
             if isinstance(module,nn.Linear) and name.startswith('blocks.') and ('.att.' in name or '.ffn.' in name)]
    require(len(targets)==model.layout.layers*6,'expected all four attention and both FFN linear modules in every layer')
    model.requires_grad_(False)
    for name,module in targets:
        parent,key=name.rsplit('.',1);setattr(model.get_submodule(parent),key,LoRALinear(module,rank=rank,alpha=alpha))
    model.__class__=CCViewLoRAModel
    model.eval()
    require(all(not p.requires_grad for n,p in model.named_parameters() if n not in adapter_parameters(model)),
            'LoRA base or initial State was made trainable')
    return [name for name,_ in targets]


def save_adapter(model,path,*,base_sha256):
    path=Path(path);require(not path.exists(),'adapter output already exists')
    modules={name:module for name,module in model.named_modules() if isinstance(module,LoRALinear)}
    require(bool(modules),'no LoRA modules')
    payload=dict(schema_version=ADAPTER_SCHEMA,input_protocol=cc.PROTOCOL,base_sha256=base_sha256,
        targets=list(modules),rank=next(iter(modules.values())).rank,alpha=next(iter(modules.values())).alpha,
        parameters={name:value.detach().cpu().clone() for name,value in adapter_parameters(model).items()})
    with path.open('xb') as stream:torch.save(payload,stream)
    return dict(path=str(path),sha256=sha256_file(path))


def load_adapter(model,path,expected_sha,*,base_sha256):
    value=torch.load(verify_file(path,expected_sha),map_location='cpu',weights_only=True)
    modules={name:module for name,module in model.named_modules() if isinstance(module,LoRALinear)}
    parameters=adapter_parameters(model)
    require(value['schema_version']==ADAPTER_SCHEMA and value['input_protocol']==cc.PROTOCOL
            and value['base_sha256']==base_sha256 and value['targets']==list(modules)
            and set(value['parameters'])==set(parameters),'LoRA identity or target modules differ')
    with torch.no_grad():
        for name,target in parameters.items():
            source=value['parameters'][name]
            require(source.shape==target.shape and bool(torch.isfinite(source).all()),'LoRA parameter geometry/finiteness differs')
            target.copy_(source.to(target))


def merge_checkpoint(model,base_path,base_sha256,output):
    """Write a new ordinary checkpoint; the authorized frozen base is read-only."""
    path=Path(output);require(not path.exists(),'merged output already exists')
    weights=torch.load(verify_file(base_path,base_sha256),map_location='cpu',weights_only=True,mmap=True)
    require(isinstance(weights,dict),'base checkpoint must be a flat tensor mapping')
    merged=dict(weights);changed=[]
    for name,module in model.named_modules():
        if not isinstance(module,LoRALinear):continue
        key=name+'.weight';original=weights[key]
        delta=module.delta().detach().cpu()
        require(delta.shape==original.shape and bool(torch.isfinite(delta).all()),'merged LoRA delta differs')
        merged[key]=(original.float()+delta).to(original.dtype);changed.append(key)
    require(len(changed)==model.layout.layers*6,'incomplete LoRA merge')
    with path.open('xb') as stream:torch.save(merged,stream)
    return dict(path=str(path),sha256=sha256_file(path),changed_tensors=changed,base_sha256=base_sha256)


def check_numerics(model,tokens,*,atol,rtol,state_atol,state_rtol):
    """One frozen real sample: batch/tokenwise logits and cross-chunk State."""
    require(tokens.ndim==2 and tokens.shape[0]==1 and tokens.shape[1]>=4,'numerical probe needs one nonempty sequence')
    def states_close(left,right):
        return all(torch.allclose(a,b,atol=state_atol,rtol=state_rtol) for x,y in zip(left,right) for a,b in zip(x,y))
    with torch.no_grad():
        full,full_state=model(tokens,return_state=True)
        state=None;rows=[]
        for index in range(tokens.shape[1]):
            logits,state=model(tokens[:,index:index+1],state,return_state=True);rows.append(logits)
        tokenwise=torch.cat(rows,dim=1)
        batch_error=float((full.float()-tokenwise.float()).abs().max())
        require(torch.allclose(full,tokenwise,atol=atol,rtol=rtol),'LoRA batch/tokenwise logits exceed frozen BF16 tolerance')
        require(states_close(full_state,state),'LoRA tokenwise State differs')
        middle=tokens.shape[1]//2
        left,boundary=model(tokens[:,:middle],return_state=True)
        right,chunked_state=model(tokens[:,middle:],boundary,return_state=True)
        chunked=torch.cat((left,right),dim=1)
        chunk_error=float((full.float()-chunked.float()).abs().max())
        require(torch.allclose(full,chunked,atol=atol,rtol=rtol) and states_close(full_state,chunked_state),
                'LoRA chunk State carry exceeds frozen tolerance')
    return dict(batched_tokenwise_max_logit_error=batch_error,chunked_max_logit_error=chunk_error,
                tokens=int(tokens.shape[1]),passed=True)
