"""Separate, sealed CC-view StateTune/LoRA entry; never a Project default."""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gc
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time

from . import cc_view_experiment as cc
from . import statetune_core as core
from .cc_view_training_freeze import load_split
from .statetune_episodes import validate_row
from .statetune_state_carry import episode_chunks,state_carry_backward
from .statetune_training import optimize_state,publish_state

RUN_SCHEMA='rwkv-lh.cc-view-training-run.v1'


def target_count(row):return sum(n for (_,n),mark in zip(row['target_spans'],row['supervised']) if mark)


def source_order(rows,seed):
    """Shuffle within sources and advance proportional source exposure, once each."""
    generator=random.Random(seed);groups=defaultdict(list)
    for row in rows:groups[row['source']].append(row)
    for values in groups.values():generator.shuffle(values)
    totals={s:len(values) for s,values in groups.items()};used=Counter();ordered=[]
    priority={s:generator.random() for s in groups}
    while len(ordered)<len(rows):
        source=min((s for s in groups if used[s]<totals[s]),key=lambda s:(used[s]/totals[s],priority[s]))
        ordered.append(groups[source][used[source]]);used[source]+=1
    return ordered


def capped_prefix(ordered,*,token_cap,accumulation):
    result=[];total=0
    for start in range(0,len(ordered),accumulation):
        group=ordered[start:start+accumulation];count=sum(target_count(row) for row in group)
        if total+count>token_cap:break
        result.extend(group);total+=count
    core.require(bool(result),'no complete registered accumulation group fits token cap')
    return result,total


def core_order(ordered,seed):
    """Preserve the frozen stratification through the unchanged StateTune shuffle."""
    permutation=list(range(len(ordered)));random.Random(seed).shuffle(permutation)
    result=[None]*len(ordered)
    for position,index in enumerate(permutation):result[index]=ordered[position]
    return result


def loss_audit(model,rows,*,context_tokens,record=None):
    """Full-context, target-only validation loss, by action and source."""
    import torch
    device=next(iter(model.parameters())).device;totals=defaultdict(lambda:[0.,0]);overall=[0.,0]
    model.eval()
    with torch.no_grad():
        for row_index,row in enumerate(rows):
            chunks=episode_chunks(row['token_ids'],row['target_spans'],row['chunk_starts'],
                                   context_tokens=context_tokens,supervised=row['supervised'])
            state=None
            for chunk_index,chunk in enumerate(chunks):
                logits,state=model(chunk['input_ids'].to(device),state,return_state=True)
                labels=chunk['labels'].to(device);start=row['chunk_starts'][chunk_index];stop=start+labels.shape[1]
                by_action=defaultdict(list)
                for (begin,count),mark,action in zip(row['target_spans'],row['supervised'],row['actions']):
                    if not mark:continue
                    left=max(start,begin-1);right=min(stop,begin+count-1)
                    if right>left:by_action[action].extend(range(left-start,right-start))
                for action,indices in by_action.items():
                    positions=torch.tensor(indices,device=device,dtype=torch.long)
                    selected=logits[:,positions];target=labels[:,positions]
                    loss=torch.nn.functional.cross_entropy(selected.float().reshape(-1,selected.shape[-1]),target.reshape(-1),reduction='sum')
                    value=float(loss);core.require(math.isfinite(value),'nonfinite validation loss')
                    count=len(indices);overall[0]+=value;overall[1]+=count
                    for key in (action,'source:'+str(row['source'])+'/'+action):
                        totals[key][0]+=value;totals[key][1]+=count
                    del selected,target,positions,loss
                del logits
            if record:record(dict(event='validation_episode_completed',episode_id=row['episode_id'],index=row_index+1,total=len(rows)))
            del chunks,state
    core.require(overall[1]>0,'validation has no supervised tokens')
    return dict(loss=overall[0]/overall[1],target_tokens=overall[1],episodes=len(rows),
                by_action={key:dict(loss=value[0]/value[1],target_tokens=value[1]) for key,value in totals.items()})


def optimize_lora(model,ordered,config,*,context_tokens,record):
    import torch
    from .cc_view_lora import adapter_parameters
    parameters=adapter_parameters(model);core.require(bool(parameters),'LoRA has no adapter parameters')
    frozen={name:value._version for name,value in model.named_parameters() if name not in parameters}
    optimizer=torch.optim.AdamW(parameters.values(),lr=config['learning_rate'],betas=config['betas'],eps=config['eps'],
                                weight_decay=0,foreach=False)
    started=time.monotonic();result=dict(optimizer_steps=0,samples_seen=0,target_tokens_seen=0,status='running')
    model.eval();torch.cuda.reset_peak_memory_stats()
    def expired():return time.monotonic()-started>=config['max_seconds']
    for start in range(0,len(ordered),config['gradient_accumulation']):
        if expired():result.update(status='interrupted',stop_reason='wall_time_budget');break
        group=ordered[start:start+config['gradient_accumulation']];targets=sum(target_count(row) for row in group)
        optimizer.zero_grad(set_to_none=True);weighted=0.
        for row in group:
            if expired():result.update(status='interrupted',stop_reason='wall_time_budget');break
            chunks=episode_chunks(row['token_ids'],row['target_spans'],row['chunk_starts'],context_tokens=context_tokens,supervised=row['supervised'])
            outcome=state_carry_backward(model,chunks,weight=target_count(row)/targets)
            core.require(outcome['recompute_equal'],'LoRA chunk boundary recomputation differs')
            weighted+=outcome['loss']*target_count(row)/targets
            result['samples_seen']+=1;result['target_tokens_seen']+=outcome['targets']
            record(dict(event='episode_backward_completed',episode_id=row['episode_id'],source=row['source'],**outcome))
            del chunks
        if result['status']=='interrupted':break
        core.require(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in parameters.values()),'LoRA gradient missing/nonfinite')
        core.require(all(not p.requires_grad and p.grad is None and p._version==frozen[name]
                         for name,p in model.named_parameters() if name in frozen),'LoRA frozen base was mutated')
        norm=torch.nn.utils.clip_grad_norm_(list(parameters.values()),config['max_grad_norm'],error_if_nonfinite=True)
        if expired():result.update(status='interrupted',stop_reason='wall_time_budget');break
        record(dict(event='optimizer_step_started',next_step=result['optimizer_steps']+1,**result))
        optimizer.step();torch.cuda.synchronize();result['optimizer_steps']+=1
        core.require(all(bool(torch.isfinite(p).all()) for p in parameters.values()),'nonfinite LoRA adapter')
        record(dict(event='optimizer_step_completed',loss=weighted,gradient_norm=float(norm),
                    elapsed_seconds=time.monotonic()-started,peak_allocated_bytes=torch.cuda.max_memory_allocated(),**result))
    else:result.update(status='candidate',stop_reason='registered_prefix_finished')
    optimizer.zero_grad(set_to_none=True)
    return dict(**result,elapsed_seconds=time.monotonic()-started,peak_allocated_bytes=torch.cuda.max_memory_allocated())


def lora_roundtrip_and_merge(model,probe,output,registration,runtime,record):
    import torch
    from .cc_view_lora import adapter_parameters,save_adapter,load_adapter,merge_checkpoint,check_numerics
    tolerance=registration['numerical_tolerances']
    tokens=torch.tensor([probe['token_ids'][:64]],device='cuda',dtype=torch.long)
    numeric=check_numerics(model,tokens,atol=tolerance['logits_atol'],rtol=tolerance['logits_rtol'],
                           state_atol=tolerance['state_atol'],state_rtol=tolerance['state_rtol'])
    record(dict(event='lora_numerics_passed',**numeric))
    adapter=save_adapter(model,output/'adapter.pth',base_sha256=registration['base_sha256'])
    with torch.no_grad():expected,state=model(tokens,return_state=True)
    with torch.no_grad():
        for value in adapter_parameters(model).values():value.zero_()
    load_adapter(model,adapter['path'],adapter['sha256'],base_sha256=registration['base_sha256'])
    with torch.no_grad():actual,loaded_state=model(tokens,return_state=True)
    core.require(torch.equal(expected,actual) and all(torch.equal(a,b) for x,y in zip(state,loaded_state) for a,b in zip(x,y)),
                 'LoRA save/load inference is not bitwise reproducible')
    record(dict(event='lora_save_load_passed',adapter=adapter))
    del state,loaded_state,actual
    merged=merge_checkpoint(model,registration['base_path'],registration['base_sha256'],output/'merged.pth')
    artifact=output/'merged_artifact';engine=runtime['engine']
    command=[sys.executable,'-B','-m','scripts.prepare_rwkv_vllm_artifact','--engine-root',engine['root'],
        '--engine-source-manifest',engine['manifest_path'],'--engine-source-manifest-sha256',engine['manifest_sha256'],
        '--engine-revision',engine['revision'],'--source',merged['path'],'--source-sha256',merged['sha256'],
        '--source-model','ccview-lora-20261021','--output',str(artifact),'--context-length','24576']
    conversion=subprocess.run(command,capture_output=True,text=True)
    (output/'MERGE_CONVERSION_STDOUT.log').write_text(conversion.stdout)
    (output/'MERGE_CONVERSION_STDERR.log').write_text(conversion.stderr)
    core.require(conversion.returncode==0,'merged LoRA artifact conversion failed')
    gc.collect();torch.cuda.empty_cache()
    from .inference.vllm_rwkv import PersistentVLLMRWKVExtractor
    serving=PersistentVLLMRWKVExtractor._load_direct_model(artifact)
    with torch.no_grad():
        recurrent=serving.zero_state(1);reference=serving.forward_all_logits(tokens,recurrent)
        error=float((reference.float()-expected.float()).abs().max())
        core.require(torch.allclose(reference,expected,atol=tolerance['logits_atol'],rtol=tolerance['logits_rtol']),
                     'merged LoRA serving logits exceed frozen BF16 tolerance')
    record(dict(event='lora_production_serving_loader_passed',artifact=str(artifact),max_logit_error=error))
    del reference,expected,serving,recurrent;gc.collect();torch.cuda.empty_cache()
    return dict(adapter=adapter,merged=merged,model_artifact=str(artifact),
                model_artifact_manifest_sha256=core.sha256_file(artifact/'manifest.json'),serving_loader_verified=True)


def run(reference,expected_sha,output):
    registration=core.read_sealed_json(reference,expected_sha)
    core.require(registration['schema_version']==RUN_SCHEMA and registration['input_protocol']==cc.PROTOCOL,
                 'explicit CC-view registration required')
    core.require(registration['phase'] in ('pilot','formal') and registration['arm'] in ('statetune','lora'),'unknown CC-view training phase/arm')
    for ref in registration['authorization_references']:core.verify_file(ref['path'],ref['sha256'])
    out=Path(output);out.mkdir(parents=True,exist_ok=False);events=out/'TRAIN_LOG.jsonl'
    started=time.monotonic();report=dict(status='starting',arm=registration['arm'],phase=registration['phase'],
        input_protocol=cc.PROTOCOL,registration_sha256=expected_sha,optimizer_steps=0)
    model=None;latest=None;next_loss_token=500000
    def record(value):
        nonlocal latest,next_loss_token
        item=dict(at=datetime.now(timezone.utc).isoformat(),**value)
        with events.open('a') as stream:stream.write(json.dumps(item,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
        print(json.dumps(item,ensure_ascii=False),flush=True)
        if value.get('event')=='optimizer_step_completed':
            report['optimizer_steps']=value['optimizer_steps']
            step=value['optimizer_steps'];checkpoint=out/'checkpoints'/f'step-{step:06d}';checkpoint.mkdir(parents=True,exist_ok=False)
            if registration['arm']=='statetune':
                latest=publish_state(model,checkpoint,profile_id=registration['profile_id'],
                    model_artifact=runtime['model_artifact']['path'],engine_revision=runtime['engine']['revision'])
            else:
                from .cc_view_lora import save_adapter
                latest=dict(adapter=save_adapter(model,checkpoint/'adapter.pth',base_sha256=registration['base_sha256']))
            latest['optimizer_step']=step
            latest['target_tokens_seen']=value['target_tokens_seen']
            with (checkpoint/'CHECKPOINT.json').open('x') as stream:json.dump(latest,stream,ensure_ascii=False,indent=2)
            if value['target_tokens_seen']>=next_loss_token:
                with events.open('a') as stream:stream.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),event='half_million_token_loss',
                    target_tokens_seen=value['target_tokens_seen'],optimizer_steps=step,loss=value['loss']))+'\n')
                while next_loss_token<=value['target_tokens_seen']:next_loss_token+=500000
    try:
        from .statetune_native_runtime import verify_native_runtime,load_native_runtime,verify_loaded_libraries
        runtime=verify_native_runtime(registration['runtime']['path'],registration['runtime']['sha256'],
            source_root=Path(__file__).resolve().parents[1],source_manifest_sha256=registration['source_manifest_sha256'])
        load_native_runtime(runtime)
        import torch
        from .statetune_native_model import build
        core.require(torch.cuda.device_count()==1 and core.device_uuid_matches(str(torch.cuda.get_device_properties(0).uuid),registration['gpu_uuid']),
                     'CC-view training GPU UUID differs')
        artifact=core.read_sealed_json(Path(runtime['model_artifact']['path'])/'manifest.json',runtime['model_artifact']['manifest_sha256'])
        core.require(artifact['source']['sha256']==registration['base_sha256'] and artifact['source']['path']==registration['base_path'],
                     'CC-view frozen base differs')
        train,manifest=load_split(registration['dataset']['path'],registration['dataset']['sha256'],'train',context_tokens=24576)
        validation,_=load_split(registration['dataset']['path'],registration['dataset']['sha256'],'validation',context_tokens=24576)
        core.require(manifest['model_sha256']==registration['base_sha256'],'CC-view training data base identity differs')
        if registration['phase']=='pilot':
            by_id={row['episode_id']:row for row in train};selected=[by_id[key] for key in registration['pilot_ids']]
            core.require(len(selected)==30 and len(set(registration['pilot_ids']))==30,'pilot requires exactly thirty frozen unique trajectories')
        else:selected=source_order(train,registration['optimizer']['seed'])
        ordered,exposure=capped_prefix(selected,token_cap=registration['supervised_token_cap'],
                                       accumulation=registration['optimizer']['gradient_accumulation'])
        config=dict(registration['optimizer']);config.update(epochs=1,max_optimizer_steps=math.ceil(len(ordered)/config['gradient_accumulation']))
        deadline=datetime.fromisoformat(registration['hard_deadline']).timestamp()
        config['max_seconds']=max(1.,min(config['max_seconds'],deadline-time.time()-30))
        torch.manual_seed(config['seed'])
        model=build(dict(model_artifact=runtime['model_artifact']['path'],context_tokens=24576,
                         base=dict(path=registration['base_path'],sha256=registration['base_sha256'])))
        if registration['arm']=='lora':
            from .cc_view_lora import attach
            targets=attach(model,rank=64,alpha=128);record(dict(event='lora_targets_registered',targets=targets))
        core.require(all(bool(torch.count_nonzero(value)==0) for name,value in model.named_parameters() if name.endswith('.time_state')),
                     'CC-view training must initialize State from zero')
        verify_loaded_libraries(runtime)
        record(dict(event='identity_admitted',gpu_uuid=registration['gpu_uuid'],dataset_sha256=registration['dataset']['sha256'],
                    model_sha256=registration['base_sha256'],train_episodes=len(train),selected_episodes=len(ordered),
                    selected_supervised_tokens=exposure,initial_state='zero',source_counts=dict(Counter(row['source'] for row in ordered))))
        if registration['phase']=='pilot':
            validation_ids=set(registration['validation_probe_ids']);probe=[row for row in validation if row['episode_id'] in validation_ids]
            core.require(len(probe)==len(validation_ids) and {row['source'] for row in probe}==set(range(1,7)),
                         'pilot validation probe must cover every source')
            before_train=loss_audit(model,ordered,context_tokens=24576,record=record)
            before_validation=loss_audit(model,probe,context_tokens=24576,record=record)
            record(dict(event='pilot_before',train=before_train,validation=before_validation))
            if registration['arm']=='lora':
                from .cc_view_lora import check_numerics
                tolerance=registration['numerical_tolerances'];tokens=torch.tensor([ordered[0]['token_ids'][:64]],device='cuda')
                record(dict(event='lora_pretraining_numerics',**check_numerics(model,tokens,atol=tolerance['logits_atol'],rtol=tolerance['logits_rtol'],
                    state_atol=tolerance['state_atol'],state_rtol=tolerance['state_rtol'])))
                del tokens
        config['max_seconds']=max(1.,min(config['max_seconds'],deadline-time.time()-30))
        result=(optimize_state(model,core_order(ordered,config['seed']),config,context_tokens=24576,record=record,episode_mode=True)
                if registration['arm']=='statetune' else optimize_lora(model,ordered,config,context_tokens=24576,record=record))
        report.update(optimization=result,optimizer_steps=result['optimizer_steps'],latest_checkpoint=latest,
                      full_dataset_epochs_completed=int(result['samples_seen']==len(train)),dataset_episodes=len(train))
        if registration['phase']=='pilot':
            after_train=loss_audit(model,ordered,context_tokens=24576,record=record)
            after_validation=loss_audit(model,probe,context_tokens=24576,record=record)
            gate=after_train['loss']<before_train['loss'] and after_validation['loss']<before_validation['loss']
            report.update(before_train=before_train,before_validation=before_validation,after_train=after_train,
                          after_validation=after_validation,loss_gate=gate)
            core.require(gate,'pilot train and validation loss must both decrease')
            if registration['arm']=='lora':report['export']=lora_roundtrip_and_merge(model,ordered[0],out,registration,runtime,record)
        else:
            # Training ends at T8; external orchestrator bounds the post-training
            # validation/export separately and preserves the latest checkpoint.
            report['export']=latest
        report.update(status='pilot_passed' if registration['phase']=='pilot' else 'trained_checkpoint_available',
                      elapsed_seconds=time.monotonic()-started)
    except BaseException as error:
        report.update(status='failed',error=dict(type=type(error).__name__,message=str(error)),
                      latest_checkpoint=latest,elapsed_seconds=time.monotonic()-started)
        record(dict(event='run_failed',**report))
        raise
    finally:
        with (out/'RESULT.json').open('x') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',type=Path,required=True);parser.add_argument('--registration-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=run(args.registration,args.registration_sha256,args.output)
    return 0 if result['status'] in ('pilot_passed','trained_checkpoint_available') else 1


if __name__=='__main__':raise SystemExit(main())
