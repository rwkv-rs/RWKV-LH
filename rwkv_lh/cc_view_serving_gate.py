"""Serving gate: a nonzero State or adapter must be consumed by the actual loader.

A zero State or zero-delta adapter reproduces the base model whatever the
loader does, so it cannot show that layout, transpose, dtype or shift
initialization are right. This gate installs a registered nonzero test value
(or a trained candidate), records the PEFT training-path reference, and then
replays the same chunked tokens through the production vLLM model and loader:

- reference (PEFT environment): logits and carried State of every chunk with
  the nonzero value, the same tokens without it, the portable State profile or
  standard adapter, and for LoRA one base-precision merged checkpoint.
- serving (engine environment): StateTune through RWKV7InitialStateProfiles,
  LoRA through the ordinary artifact converter and direct loader.

Serving must match the reference within the frozen tolerances, and the effect
of the nonzero value must exceed that error by the registered ratio. For
StateTune the untransposed portable State is a negative control.
"""
import argparse
from datetime import datetime,timezone
import gc
import json
import math
from pathlib import Path
import subprocess
import sys

from . import statetune_core as core

SCHEMA='rwkv-lh.cc-view-serving-gate.v1'
METHODS=('statetune','lora')


def identity(model):
    value=dict(base=model['base'],peft_source=model['peft_source'],context_tokens=model['context_tokens'],
               precision=model['precision'],merge_target_dtype=model.get('merge_target_dtype','base'))
    if 'lora' in model:value['lora']=model['lora']
    return value


def read_registration(path,sha256):
    registration=core.read_sealed_json(path,sha256)
    core.require(registration.get('schema_version')==SCHEMA and registration.get('method') in METHODS,'explicit CC-view serving gate registration required')
    source=registration['source'];core.require(source.get('kind') in ('test','candidate'),'serving gate source must be test or candidate')
    if source['kind']=='test':
        field='state_scale' if registration['method']=='statetune' else 'lora_b_std'
        core.require(type(source.get('seed')) is int and type(source.get(field)) in (int,float) and source[field]>0,'nonzero test value needs seed and scale')
    core.require(registration['model'].get('merge_target_dtype','base') in ('base','float16','bfloat16','float32'),
                 'unsupported LoRA merge target dtype')
    core.require(type(registration.get('min_effect_ratio')) in (int,float) and registration['min_effect_ratio']>1,'effect ratio must exceed one')
    return registration


def _record(output):
    def record(value):
        value=dict(at=datetime.now(timezone.utc).isoformat(),**value)
        with (output/'EVENTS.jsonl').open('a') as stream:stream.write(json.dumps(value,allow_nan=False)+'\n');stream.flush()
        print(json.dumps(value,allow_nan=False),flush=True)
    return record


def metrics(actual,reference):
    """Compare matching floating tensors, including [H,K,V] WKV State."""
    import torch
    core.require(actual.shape==reference.shape and actual.numel()>0
                 and actual.is_floating_point() and reference.is_floating_point()
                 and actual.device==reference.device,'serving comparison tensor geometry differs')
    core.require(bool(torch.isfinite(actual).all()) and bool(torch.isfinite(reference).all()),
                 'serving comparison tensor finiteness differs')
    difference=actual.float()-reference.float()
    return dict(max_abs=float(difference.abs().max()),
                relative_l2=float(torch.linalg.vector_norm(difference)/torch.linalg.vector_norm(reference.float()).clamp_min(1e-30)))


def probe(registration):
    """The registered real-trajectory tokens and chunk boundaries, untruncated."""
    from .cc_view_training_freeze import load_split
    rows,_=load_split(registration['dataset']['path'],registration['dataset']['sha256'],registration['split'],
                      context_tokens=registration['model']['context_tokens'])
    row=next((r for r in rows if r['episode_id']==registration['episode_id']),None)
    core.require(row is not None and len(row['token_ids'])==registration['episode_tokens'],'serving probe episode identity differs')
    tokens=row['token_ids'][:-1];starts=list(registration['chunk_starts'])
    core.require(len(starts)>=2 and starts[0]==0 and all(a<b for a,b in zip(starts,starts[1:])) and starts[-1]<len(tokens),
                 'serving probe needs at least two increasing chunks to test State carry')
    core.require(all(b-a<=registration['model']['context_tokens'] for a,b in zip(starts,starts[1:]+[len(tokens)])),'serving probe chunk exceeds context')
    return [tokens[a:b] for a,b in zip(starts,starts[1:]+[len(tokens)])]


def _forward(model,chunks):
    import torch
    logits=[];states=[];state=None
    with torch.no_grad():
        for chunk in chunks:
            value,state=model(torch.tensor([chunk],device='cuda',dtype=torch.long),state,return_state=True)
            logits.append(value.float().cpu());states.append(tuple(tuple(x[0].float().cpu() for x in layer) for layer in state))
            del value
    return logits,states


def _install_state(model,registration,output):
    """Write the portable BF16 profile that serving reads, then train-path reads the same values."""
    import torch
    parameters=core.state_parameters(model,layers=model.layout.layers);source=registration['source']
    if source['kind']=='test':
        generator=torch.Generator(device='cpu').manual_seed(source['seed'])
        portable={name:(torch.randn(value.shape,generator=generator)*source['state_scale']).bfloat16() for name,value in parameters.items()}
    else:
        portable=torch.load(core.verify_file(source['state']['path'],source['state']['sha256']),map_location='cpu',weights_only=True)
        core.require(isinstance(portable,dict) and set(portable)==set(parameters),'candidate State key set differs')
    core.require(all(v.dtype==torch.bfloat16 and v.shape==parameters[n].shape and bool(torch.isfinite(v).all()) and bool(torch.count_nonzero(v))
                     for n,v in portable.items()),'serving gate State must be finite, nonzero portable BF16 in every layer')
    path=output/'state.pth'
    with path.open('xb') as stream:torch.save(portable,stream)
    with torch.no_grad():
        for name,parameter in parameters.items():parameter.copy_(portable[name].float())
    return dict(path=str(path),sha256=core.sha256_file(path))


def _install_adapter(model,registration,output,record):
    """Standard PEFT adapter: save, clear, reload bitwise; never a private format."""
    import torch
    from peft import load_peft_weights,set_peft_model_state_dict
    from .cc_view_peft_backend import save_adapter,trainable_parameters
    parameters=trainable_parameters(model);source=registration['source']
    if source['kind']=='test':
        generator=torch.Generator(device='cpu').manual_seed(source['seed'])
        with torch.no_grad():
            for name,value in parameters.items():
                if 'lora_B' in name:value.copy_(torch.randn(value.shape,generator=generator)*source['lora_b_std'])
        adapter=save_adapter(model,output/'adapter')
        expected={n:p.detach().clone() for n,p in parameters.items()}
    else:
        expected=None
        directory=Path(source['adapter']['directory'])
        for name,sha in source['adapter']['files'].items():core.verify_file(directory/name,sha)
        adapter={name:dict(path=str(directory/name),sha256=sha) for name,sha in source['adapter']['files'].items()}
    with torch.no_grad():
        for value in parameters.values():value.zero_()
    loaded=load_peft_weights(str(Path(adapter['adapter_model.safetensors']['path']).parent),device='cpu')
    result=set_peft_model_state_dict(model,loaded)
    core.require(not result.unexpected_keys and not [k for k in result.missing_keys if 'lora_' in k],'standard adapter keys differ')
    core.require(any(bool(torch.count_nonzero(p)) for n,p in parameters.items() if 'lora_B' in n),'loaded adapter has a zero delta')
    core.require(expected is None or all(torch.equal(p,expected[n]) for n,p in parameters.items()),'standard adapter reload is not bitwise')
    record(dict(event='standard_adapter_loaded',files=adapter))
    return adapter


def reference(registration_path,registration_sha256,output):
    """PEFT side: nonzero and zero references on identical chunked tokens."""
    import torch
    registration=read_registration(registration_path,registration_sha256);method=registration['method']
    output=Path(output);output.mkdir(parents=True,exist_ok=False);record=_record(output)
    from . import cc_view_peft_backend as backend
    core.require(torch.cuda.device_count()==1 and core.device_uuid_matches(str(torch.cuda.get_device_properties(0).uuid),registration['gpu_uuid']),
                 'serving gate GPU differs')
    chunks=probe(registration);torch.manual_seed(registration['source'].get('seed',0))
    model=backend.build(registration['model'],method=method)
    record(dict(event='peft_loaded',method=method,precision=model.precision,chunks=[len(c) for c in chunks],optimizer_steps=0))
    if method=='statetune':
        artifact=dict(state=_install_state(model,registration,output))
    else:
        artifact=dict(adapter=_install_adapter(model,registration,output,record))
    logits,states=_forward(model,chunks)
    if method=='statetune':
        parameters=core.state_parameters(model,layers=model.layout.layers);saved={n:p.detach().clone() for n,p in parameters.items()}
        with torch.no_grad():
            for p in parameters.values():p.zero_()
        zero,_=_forward(model,chunks)
        with torch.no_grad():
            for n,p in parameters.items():p.copy_(saved[n])
    else:
        with model.disable_adapter():zero,_=_forward(model,chunks)
    effect=[metrics(a,b) for a,b in zip(logits,zero)]
    core.require(all(math.isfinite(m['max_abs']) and m['max_abs']>0 for m in effect),'nonzero value does not change PEFT logits')
    payload=dict(schema=SCHEMA,method=method,registration_sha256=registration_sha256,chunks=chunks,logits=logits,zero_logits=zero,states=states)
    path=output/'REFERENCE.pt'
    with path.open('xb') as stream:torch.save(payload,stream)
    if method=='lora':
        del logits,zero,states,payload;gc.collect()
        artifact['merged']=backend.merge_checkpoint(model,output/'merged.pth',base_path=registration['model']['base']['path'],
                                                    base_sha256=registration['model']['base']['sha256'],
                                                    target_dtype=registration['model'].get('merge_target_dtype','base'))
        record(dict(event='lora_merged_in_registered_precision',merged=artifact['merged']))
    result=dict(status='reference_ready',method=method,registration_sha256=registration_sha256,precision=model.precision,model=identity(registration['model']),
        reference=dict(path=str(path),sha256=core.sha256_file(path)),artifact=artifact,peft_effect=effect,optimizer_steps=0)
    with (output/'REFERENCE.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    record(dict(event='reference_ready',reference=result['reference'],optimizer_steps=0))
    return result


def _profiles(registration,state,output,model):
    import torch
    from .inference.vllm_rwkv_state_profiles_v1 import RWKV7InitialStateProfiles,RWKV7_STATE_PROFILE_MANIFEST_SCHEMA
    engine=registration['engine'];artifact=str(Path(registration['serving_artifact']['path']).resolve())
    path=output/'STATE_PROFILES.json'
    path.write_text(json.dumps(dict(schema_version=RWKV7_STATE_PROFILE_MANIFEST_SCHEMA,model_artifact=artifact,model_revision=engine['revision'],
        default_profile='zero',profiles=[dict(id='serving-gate',format='rwkv-peft-time-state.v1',path=state['path'],sha256=state['sha256'])]),indent=2)+'\n')
    profiles=RWKV7InitialStateProfiles.load(str(path),core.sha256_file(path),model_artifact=artifact,model_revision=engine['revision'],
        total_num_layers=int(model.total_num_layers),total_num_heads=int(model.num_attention_heads),layer_offset=0,
        num_layers=int(model.total_num_layers),tp_size=1,tp_rank=0,num_heads=int(model.num_attention_heads),
        head_size=int(model.head_size),device=torch.device('cuda:0'),dtype=model.wkv_state_dtype)
    return profiles.resolve('serving-gate').wkv_state


def _convert(registration,merged,output):
    engine=registration['engine'];artifact=output/'merged_artifact'
    command=[sys.executable,'-B','-m','scripts.prepare_rwkv_vllm_artifact','--engine-root',engine['root'],
        '--engine-source-manifest',engine['manifest_path'],'--engine-source-manifest-sha256',engine['manifest_sha256'],
        '--engine-revision',engine['revision'],'--source',merged['path'],'--source-sha256',merged['sha256'],
        '--source-model','ccview-lora-serving-gate','--output',str(artifact),'--context-length',str(registration['model']['context_tokens'])]
    conversion=subprocess.run(command,capture_output=True,text=True)
    (output/'CONVERSION_STDOUT.log').write_text(conversion.stdout);(output/'CONVERSION_STDERR.log').write_text(conversion.stderr)
    core.require(conversion.returncode==0,'merged LoRA serving artifact conversion failed')
    return artifact


def serving(registration_path,registration_sha256,reference_path,reference_sha256,output):
    """Engine side: replay the chunks through the production loader and model."""
    import torch
    registration=read_registration(registration_path,registration_sha256);method=registration['method']
    output=Path(output);output.mkdir(parents=True,exist_ok=False);record=_record(output)
    summary=core.read_sealed_json(reference_path,reference_sha256)
    core.require(summary['status']=='reference_ready' and summary['method']==method and summary['registration_sha256']==registration_sha256,
                 'serving gate reference belongs to another registration')
    reference=torch.load(core.verify_file(summary['reference']['path'],summary['reference']['sha256']),map_location='cpu',weights_only=True)
    core.require(torch.cuda.device_count()==1 and core.device_uuid_matches(str(torch.cuda.get_device_properties(0).uuid),registration['gpu_uuid']),
                 'serving gate GPU differs')
    import vllm
    engine=registration['engine'];core.require(Path(vllm.__file__).resolve().is_relative_to(Path(engine['root']).resolve()),'vllm resolved outside the pinned engine')
    from .inference.vllm_rwkv import PersistentVLLMRWKVExtractor
    if method=='statetune':
        artifact=Path(registration['serving_artifact']['path'])
        manifest=core.read_sealed_json(artifact/'manifest.json',registration['serving_artifact']['manifest_sha256'])
        core.require(manifest['source']['sha256']==registration['model']['base']['sha256'],'serving artifact is not the frozen base')
    else:
        artifact=_convert(registration,summary['artifact']['merged'],output)
    model=PersistentVLLMRWKVExtractor._load_direct_model(artifact)
    core.require(str(model.wkv_state_dtype)=='torch.float32','serving State arithmetic differs')
    initial=_profiles(registration,summary['artifact']['state'],output,model) if method=='statetune' else None
    tolerance=registration['tolerances']

    def run(wkv,count=None):
        recurrent=model.zero_state(1);logits=[];states=[]
        if wkv is not None:recurrent[1].copy_(wkv.unsqueeze(1))
        with torch.inference_mode():
            for chunk in reference['chunks'][:count]:
                logits.append(model.forward_all_logits(torch.tensor([chunk],device='cuda',dtype=torch.long),recurrent).float().cpu())
                states.append([(recurrent[1][i,0].float().cpu(),recurrent[0][i,0,0].float().cpu(),recurrent[0][i,1,0].float().cpu())
                               for i in range(int(model.total_num_layers))])
        return logits,states

    logits,states=run(initial)
    rows=[];passed=True;ratio=registration['min_effect_ratio']
    for index,(actual,expected,zero) in enumerate(zip(logits,reference['logits'],reference['zero_logits'])):
        error=metrics(actual,expected);effect=metrics(expected,zero);moved=metrics(actual,zero)
        close=bool(torch.allclose(actual,expected,atol=tolerance['logits_atol'],rtol=tolerance['logits_rtol']))
        state_close=all(torch.allclose(a,b,atol=tolerance['state_atol'],rtol=tolerance['state_rtol'])
                        for layer,peft in zip(states[index],reference['states'][index]) for a,b in zip(layer,peft))
        state_error=max(metrics(a,b)['max_abs'] for layer,peft in zip(states[index],reference['states'][index]) for a,b in zip(layer,peft))
        consumed=effect['max_abs']>=ratio*error['max_abs'] and moved['max_abs']>=ratio*error['max_abs']
        rows.append(dict(chunk=index,tokens=len(reference['chunks'][index]),logits=error,peft_effect=effect,serving_effect=moved,
                         logits_close=close,state_close=state_close,max_state_error=state_error,consumed=consumed))
        passed&=close and state_close and consumed
        record(dict(event='serving_chunk_compared',**rows[-1]))
    control=None
    if method=='statetune':
        # Skipping the loader's single [H,V,K]->[H,K,V] conversion must be detectable.
        wrong,_=run(initial.transpose(-2,-1).contiguous(),count=1)
        control=metrics(wrong[0],reference['logits'][0]);control['detected']=control['max_abs']>=ratio*rows[0]['logits']['max_abs']
        passed&=control['detected'];record(dict(event='transposed_state_control',**control))
    result=dict(status='passed' if passed else 'failed',method=method,registration_sha256=registration_sha256,
        reference=dict(path=str(reference_path),sha256=reference_sha256),serving_artifact=str(artifact),
        artifact=summary['artifact'],precision=summary['precision'],model=summary['model'],chunks=rows,transposed_state_control=control,
        model_generations=0,optimizer_steps=0)
    with (output/'RESULT.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    record(dict(event='serving_gate_finished',status=result['status'],optimizer_steps=0))
    core.require(passed,'serving gate failed')
    return result


def require_passed(reference,*,method,model):
    """Training admission: the same method/base/precision/source passed serving."""
    result=core.read_sealed_json(reference['path'],reference['sha256'])
    core.require(result.get('status')=='passed' and result.get('method')==method,'serving gate has not passed for this method')
    core.require(result['model']==identity(model),'serving gate base, PEFT source, context or precision differs from training')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('phase',choices=('reference','serving'))
    parser.add_argument('--registration',required=True);parser.add_argument('--registration-sha256',required=True)
    parser.add_argument('--reference');parser.add_argument('--reference-sha256');parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.phase=='reference':reference(args.registration,args.registration_sha256,args.output)
    else:
        core.require(bool(args.reference and args.reference_sha256),'serving phase needs the sealed reference')
        serving(args.registration,args.registration_sha256,args.reference,args.reference_sha256,args.output)
    return 0


if __name__=='__main__':raise SystemExit(main())
