"""Separate, sealed CC-view StateTune/LoRA entry; never a Project default.

Both methods use RWKV-PEFT layers and Hugging Face PEFT. Experimental LoRA
may defer serving qualification with an explicit sealed owner authorization;
that admission does not qualify a checkpoint for serving or product adoption.
"""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import random
import time

from . import cc_view_experiment as cc
from . import statetune_core as core
from .cc_view_training_freeze import load_split
from .cc_view_serving_gate import identity,require_passed
from .statetune_state_carry import episode_chunks,state_carry_backward
from .statetune_training import publish_state

RUN_SCHEMA='rwkv-lh.cc-view-peft-training-run.v1'


def admit_training(registration):
    """Keep owner-authorized SFT training separate from serving qualification."""
    reference=registration.get('serving_gate_deferral')
    if reference is None:
        return require_passed(registration['serving_gate'],method=registration['arm'],model=registration['model'])
    authority=core.read_sealed_json(reference['path'],reference['sha256'])
    core.require(registration['arm']=='lora' and reference in registration['authorization_references']
                 and registration.get('serving_gate') is None,'serving deferral needs explicit LoRA-only authorization')
    core.require(authority.get('schema')=='rwkv-lh.cc-view-sft-serving-deferral.v1'
                 and authority.get('method')=='lora' and authority.get('product_adoption') is False
                 and authority.get('model')==identity(registration['model'])
                 and all(isinstance(authority.get(k),str) and authority[k].strip() for k in ('owner_instruction','reason')),
                 'serving deferral authorization scope differs')
    return dict(status='deferred_by_owner',serving_qualified=False,authorization=reference)


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


OPTIMIZER_FIELDS={'seed','gradient_accumulation','learning_rate','betas','eps','weight_decay','max_grad_norm',
                  'max_seconds','max_allocated_bytes','checkpoint_every_steps'}
OPTIONAL_OPTIMIZER_FIELDS={'warmup_steps','execution_chunk_tokens','checkpoint_milestones','loss_warning'}


def validate_registration(registration):
    core.require(registration['phase'] in ('pilot','formal') and registration['arm'] in ('statetune','lora'),'unknown CC-view training phase/arm')
    config=registration['optimizer'];core.require(OPTIMIZER_FIELDS<=set(config)<=OPTIMIZER_FIELDS|OPTIONAL_OPTIMIZER_FIELDS,
                                                'CC-view optimizer registration fields differ')
    core.require(registration['model']['precision']['base']=='float32','SFT optimizer currently requires FP32; unmanaged low precision is unqualified')
    for name in ('seed','gradient_accumulation','max_allocated_bytes','checkpoint_every_steps'):
        core.require(type(config[name]) is int and config[name]>(-1 if name=='seed' else 0),'invalid registered '+name)
    for name in ('learning_rate','eps','max_grad_norm','max_seconds','weight_decay'):
        if name=='max_seconds' and config[name] is None:continue
        value=config[name];core.require(type(value) in (int,float) and math.isfinite(value) and (value>=0 if name=='weight_decay' else value>0),
                                        'invalid registered '+name)
    core.require(isinstance(config['betas'],list) and len(config['betas'])==2 and all(type(v) in (int,float) and 0<=v<1 for v in config['betas']),
                 'invalid registered betas')
    core.require(type(registration['supervised_token_cap']) is int and registration['supervised_token_cap']>0,'invalid supervised token cap')
    for name in ('warmup_steps','execution_chunk_tokens'):
        if name in config:core.require(type(config[name]) is int and config[name]>=(0 if name=='warmup_steps' else 1),'invalid '+name)
    if 'execution_chunk_tokens' in config:
        core.require(config['execution_chunk_tokens']<=registration['model']['context_tokens'],'execution chunk exceeds model context')
    milestones=config.get('checkpoint_milestones',[])
    core.require(isinstance(milestones,list) and all(type(v) is int and v>=0 for v in milestones)
                 and milestones==sorted(set(milestones)),'invalid checkpoint milestones')
    warning=config.get('loss_warning')
    if warning is not None:
        core.require(set(warning)=={'window','ratio','minimum'} and type(warning['window']) is int and warning['window']>0
                     and all(type(warning[k]) in (float,int) and math.isfinite(warning[k]) and warning[k]>0 for k in ('ratio','minimum')),
                     'invalid loss warning configuration')


def checkpoint_identity(registration,ordered):
    """A resumed run must continue the same method, data, order, source and precision."""
    order=hashlib.sha256('\n'.join(row['episode_id'] for row in ordered).encode()).hexdigest()
    return dict(arm=registration['arm'],phase=registration['phase'],dataset=registration['dataset']['sha256'],
        project_source=registration['project_source']['sha256'],model=identity(registration['model']),
        optimizer=registration['optimizer'],order_sha256=order)


def optimize(model,ordered,config,*,context_tokens,record,last,resume=None,deadline=None):
    """One token-weighted AdamW loop over PEFT trainables, for both methods.

    Each complete episode is backpropagated through its carried State. An
    atomic last.pt holds trainables, optimizer, RNG and data progress; budgets
    stop only before the next optimizer step. max_seconds counts training time
    across resumes; deadline is an absolute wall-clock bound for this process.
    """
    import torch
    from . import cc_view_peft_backend as backend
    from .cc_view_checkpoint import save_last,load_last,retain_milestone
    parameters=backend.trainable_parameters(model)
    frozen={name:value._version for name,value in model.named_parameters() if name not in parameters}
    optimizer=torch.optim.AdamW(parameters.values(),lr=config['learning_rate'],betas=config['betas'],eps=config['eps'],
                                weight_decay=config['weight_decay'],foreach=False)
    progress=dict(optimizer_steps=0,next_episode=0,samples_seen=0,target_tokens_seen=0,elapsed_seconds=0.)
    if resume is not None:
        progress.update(load_last(resume['path'],model,optimizer,identity=last['identity']))
        record(dict(event='resumed',checkpoint=resume,**progress))
    core.require(0<=progress['next_episode']<=len(ordered) and
                 (progress['next_episode']==len(ordered) or progress['next_episode']%config['gradient_accumulation']==0),
                 'checkpoint is not at a step boundary')
    saved=None if resume is None else dict(path=str(resume['path']),sha256=core.sha256_file(resume['path']),progress=dict(progress))
    started=time.monotonic()-progress['elapsed_seconds'];stepping=False
    result=dict(status='running',stop_reason=None);device=next(iter(parameters.values())).device
    model.eval()
    if device.type=='cuda':torch.cuda.reset_peak_memory_stats(device)
    def peak():return torch.cuda.max_memory_allocated(device) if device.type=='cuda' else 0
    def elapsed():return time.monotonic()-started
    def reason():
        if config['max_seconds'] is not None and elapsed()>=config['max_seconds']:return 'wall_time_budget'
        if deadline is not None and time.time()>=deadline:return 'hard_deadline'
        if peak()>config['max_allocated_bytes']:return 'gpu_memory_budget'
        return None
    def checkpoint():
        nonlocal saved
        progress['elapsed_seconds']=elapsed()
        saved=save_last(last['path'],model,optimizer,identity=last['identity'],progress=progress)
        record(dict(event='last_checkpoint_saved',**saved))
        if progress['optimizer_steps'] in config.get('checkpoint_milestones',[]):
            record(dict(event='checkpoint_milestone_saved',**retain_milestone(saved)))
    try:
        if saved is None and 0 in config.get('checkpoint_milestones',[]):checkpoint()
        for start in range(progress['next_episode'],len(ordered),config['gradient_accumulation']):
            if reason():break
            group=ordered[start:start+config['gradient_accumulation']];targets=sum(target_count(row) for row in group)
            optimizer.zero_grad(set_to_none=True);weighted=0.
            for row in group:
                if reason():break
                record(dict(event='episode_backward_started',episode_id=row['episode_id'],source=row['source'],
                            next_step=progress['optimizer_steps']+1,input_tokens=len(row['token_ids'])-1))
                starts=row['chunk_starts']
                if 'execution_chunk_tokens' in config:
                    starts=list(range(0,len(row['token_ids'])-1,config['execution_chunk_tokens']))
                chunks=episode_chunks(row['token_ids'],row['target_spans'],starts,context_tokens=context_tokens,supervised=row['supervised'])
                def chunk_record(value):record(dict(value,episode_id=row['episode_id'],source=row['source']))
                try:outcome=state_carry_backward(model,chunks,weight=target_count(row)/targets,record=chunk_record)
                except BaseException as error:
                    record(dict(event='episode_backward_failed',episode_id=row['episode_id'],source=row['source'],error=repr(error)))
                    raise
                core.require(outcome['recompute_equal'],'chunk boundary recomputation differs')
                core.require(math.isfinite(outcome['loss']),'nonfinite target loss')
                weighted+=outcome['loss']*target_count(row)/targets
                record(dict(event='episode_backward_completed',episode_id=row['episode_id'],source=row['source'],**outcome))
                del chunks
            else:
                bad=[n for n,p in parameters.items() if p.grad is None or not bool(torch.isfinite(p.grad).all())]
                if bad:record(dict(event='gradient_failed',parameters=bad))
                core.require(not bad,'trainable gradient missing/nonfinite')
                core.require(any(bool(p.grad.ne(0).any()) for p in parameters.values()),'all trainable gradients are zero')
                core.require(all(not p.requires_grad and p.grad is None and p._version==frozen[name]
                                 for name,p in model.named_parameters() if name in frozen),'frozen base was mutated')
                norm=torch.nn.utils.clip_grad_norm_(list(parameters.values()),config['max_grad_norm'],error_if_nonfinite=True)
                if reason():break
                warmup=config.get('warmup_steps',0)
                rate=config['learning_rate']*min(1.,(progress['optimizer_steps']+1)/max(1,warmup))
                for parameter_group in optimizer.param_groups:parameter_group['lr']=rate
                record(dict(event='optimizer_step_started',next_step=progress['optimizer_steps']+1,learning_rate=rate,**progress))
                stepping=True;optimizer.step()
                if device.type=='cuda':torch.cuda.synchronize(device)
                core.require(all(bool(torch.isfinite(p).all()) for p in parameters.values()),'nonfinite trainable parameter')
                progress.update(optimizer_steps=progress['optimizer_steps']+1,next_episode=start+len(group),
                                samples_seen=progress['samples_seen']+len(group),target_tokens_seen=progress['target_tokens_seen']+targets)
                stepping=False
                warning=config.get('loss_warning')
                if warning is not None:
                    health=progress.setdefault('loss_health',dict(baseline=[],recent=[]))
                    if len(health['baseline'])<warning['window']:health['baseline'].append(weighted)
                    health['recent']=(health['recent']+[weighted])[-warning['window']:]
                    if len(health['baseline'])==warning['window'] and len(health['recent'])==warning['window']:
                        baseline=sum(health['baseline'])/warning['window'];recent=sum(health['recent'])/warning['window']
                        if recent>max(warning['minimum'],baseline*warning['ratio']):
                            record(dict(event='training_loss_warning',baseline=baseline,recent=recent,optimizer_steps=progress['optimizer_steps'],
                                        action='notify_only; finite loss is not an Agent score or automatic stop'))
                record(dict(event='optimizer_step_completed',loss=weighted,gradient_norm=float(norm),learning_rate=rate,
                            peak_allocated_bytes=peak(),**dict(progress,elapsed_seconds=elapsed())))
                if progress['optimizer_steps']%config['checkpoint_every_steps']==0 or progress['optimizer_steps'] in config.get('checkpoint_milestones',[]):checkpoint()
                continue
            break
        if progress['next_episode']>=len(ordered):result.update(status='candidate',stop_reason='registered_prefix_finished')
        else:result.update(status='interrupted',stop_reason=reason() or 'budget')
    except BaseException as error:
        result.update(status='failed',stop_reason=type(error).__name__);raise
    finally:
        optimizer.zero_grad(set_to_none=True)
        # Partial accumulation is discarded; last.pt always ends at a step boundary.
        # A failure inside optimizer.step leaves an uncertain update and is never saved.
        if not stepping and (saved is None or saved['progress']['optimizer_steps']!=progress['optimizer_steps']):
            try:checkpoint()
            except Exception as error:
                if result['status']!='failed':raise
                record(dict(event='last_checkpoint_failed',error=repr(error)))
        result.update(progress,elapsed_seconds=elapsed(),peak_allocated_bytes=peak(),last=saved)
        record(dict(event='optimization_stopped',**result))
    return result


def export(model,registration,output):
    """Final StateTune profile or standard PEFT adapter; merging is a separate serving step."""
    from . import cc_view_peft_backend as backend
    if registration['arm']=='statetune':
        artifact=registration['serving_artifact']
        (output/'candidate').mkdir()
        return publish_state(model,output/'candidate',profile_id=registration['profile_id'],
                             model_artifact=str(Path(artifact['path']).resolve()),engine_revision=artifact['engine_revision'])
    return dict(adapter=backend.save_adapter(model,output/'adapter'))


def run(reference,expected_sha,output,*,resume=None):
    registration=core.read_sealed_json(reference,expected_sha)
    core.require(registration['schema_version']==RUN_SCHEMA and registration['input_protocol']==cc.PROTOCOL,
                 'explicit CC-view PEFT registration required')
    validate_registration(registration)
    core.require(resume is None or registration['phase']=='formal','only formal training resumes; a pilot reruns whole')
    for ref in registration['authorization_references']:core.verify_file(ref['path'],ref['sha256'])
    out=Path(output);out.mkdir(parents=True,exist_ok=False);events=out/'TRAIN_LOG.jsonl'
    started=time.monotonic();report=dict(status='starting',arm=registration['arm'],phase=registration['phase'],backend='rwkv-peft+hf-peft',
        input_protocol=cc.PROTOCOL,registration_sha256=expected_sha,optimizer_steps=0,resumed_from=resume)
    model=None;next_loss_token=500000
    def record(value):
        nonlocal next_loss_token
        item=dict(at=datetime.now(timezone.utc).isoformat(),**value)
        with events.open('a') as stream:stream.write(json.dumps(item,ensure_ascii=False,allow_nan=False)+'\n');stream.flush()
        print(json.dumps(item,ensure_ascii=False),flush=True)
        if value.get('event')=='optimizer_step_completed':
            report['optimizer_steps']=value['optimizer_steps']
            if value['target_tokens_seen']>=next_loss_token:
                with events.open('a') as stream:stream.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(),event='half_million_token_loss',
                    target_tokens_seen=value['target_tokens_seen'],optimizer_steps=value['optimizer_steps'],loss=value['loss']))+'\n')
                while next_loss_token<=value['target_tokens_seen']:next_loss_token+=500000
    try:
        source=core.read_sealed_json(registration['project_source']['path'],registration['project_source']['sha256'])
        root=Path(__file__).resolve().parents[1]
        for row in source['files']:core.verify_file(root/row['path'],row['sha256'])
        gate=admit_training(registration)
        import torch
        from . import cc_view_peft_backend as backend
        core.require(torch.cuda.device_count()==1 and core.device_uuid_matches(str(torch.cuda.get_device_properties(0).uuid),registration['gpu_uuid']),
                     'CC-view training GPU UUID differs')
        context=registration['model']['context_tokens']
        train,manifest=load_split(registration['dataset']['path'],registration['dataset']['sha256'],'train',context_tokens=context)
        core.require(manifest['model_sha256']==registration['model']['base']['sha256'],'CC-view training data base identity differs')
        if registration['phase']=='pilot':
            validation,_=load_split(registration['dataset']['path'],registration['dataset']['sha256'],'validation',context_tokens=context)
            by_id={row['episode_id']:row for row in train};selected=[by_id[key] for key in registration['pilot_ids']]
            core.require(len(selected)==30 and len(set(registration['pilot_ids']))==30,'pilot requires exactly thirty frozen unique trajectories')
        else:selected=source_order(train,registration['optimizer']['seed'])
        config=dict(registration['optimizer'])
        ordered,exposure=capped_prefix(selected,token_cap=registration['supervised_token_cap'],accumulation=config['gradient_accumulation'])
        deadline=None if registration.get('hard_deadline') is None else datetime.fromisoformat(registration['hard_deadline']).timestamp()-30
        core.require(deadline is None or time.time()<deadline,'CC-view hard deadline has passed')
        torch.manual_seed(config['seed']);random.seed(config['seed'])
        model=backend.build(registration['model'],method=registration['arm'])
        core.require(all(bool(torch.count_nonzero(value)==0) for name,value in model.named_parameters() if name.endswith('.time_state')),
                     'CC-view training must initialize State from zero')
        trainable=backend.trainable_parameters(model)
        record(dict(event='identity_admitted',gpu_uuid=registration['gpu_uuid'],dataset_sha256=registration['dataset']['sha256'],
                    model_sha256=registration['model']['base']['sha256'],precision=model.precision,serving_gate=registration['serving_gate'],
                    training_admission=gate,
                    trainable_tensors=len(trainable),trainable_scalars=sum(p.numel() for p in trainable.values()),
                    train_episodes=len(train),selected_episodes=len(ordered),selected_supervised_tokens=exposure,initial_state='zero',
                    source_counts=dict(Counter(row['source'] for row in ordered))))
        probe=None
        if registration['phase']=='pilot':
            validation_ids=set(registration['validation_probe_ids']);probe=[row for row in validation if row['episode_id'] in validation_ids]
            core.require(len(probe)==len(validation_ids) and {row['source'] for row in probe}==set(range(1,7)),
                         'pilot validation probe must cover every source')
            report.update(before_train=loss_audit(model,ordered,context_tokens=context,record=record),
                          before_validation=loss_audit(model,probe,context_tokens=context,record=record))
            record(dict(event='pilot_before',train=report['before_train'],validation=report['before_validation']))
        last=dict(path=out/'last.pt',identity=checkpoint_identity(registration,ordered))
        result=optimize(model,ordered,config,context_tokens=context,record=record,last=last,resume=resume,deadline=deadline)
        report.update(optimization=result,optimizer_steps=result['optimizer_steps'],selected_episodes=len(ordered),
                      selected_supervised_tokens=exposure,dataset_episodes=len(train),
                      full_dataset_epochs_completed=int(result['samples_seen']==len(train)))
        if result['status']!='candidate':
            report.update(status='interrupted',elapsed_seconds=time.monotonic()-started)
            return report
        report['export']=export(model,registration,out)
        if registration['phase']=='pilot':
            after_train=loss_audit(model,ordered,context_tokens=context,record=record)
            after_validation=loss_audit(model,probe,context_tokens=context,record=record)
            gate=after_train['loss']<report['before_train']['loss'] and after_validation['loss']<report['before_validation']['loss']
            report.update(after_train=after_train,after_validation=after_validation,loss_gate=gate)
            core.require(gate,'pilot train and validation loss must both decrease')
        report.update(status='pilot_passed' if registration['phase']=='pilot' else 'trained_checkpoint_available',
                      elapsed_seconds=time.monotonic()-started)
    except BaseException as error:
        report.update(status='failed',error=dict(type=type(error).__name__,message=str(error)),elapsed_seconds=time.monotonic()-started)
        record(dict(event='run_failed',**report))
        raise
    finally:
        with (out/'RESULT.json').open('x') as stream:json.dump(report,stream,ensure_ascii=False,indent=2);stream.write('\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration',type=Path,required=True);parser.add_argument('--registration-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',type=Path);parser.add_argument('--resume-sha256');args=parser.parse_args()
    core.require((args.resume is None)==(args.resume_sha256 is None),'resume needs last.pt and its SHA-256')
    resume=None if args.resume is None else dict(path=str(core.verify_file(args.resume,args.resume_sha256)),sha256=args.resume_sha256)
    result=run(args.registration,args.registration_sha256,args.output,resume=resume)
    return 0 if result['status'] in ('pilot_passed','trained_checkpoint_available') else 1


if __name__=='__main__':raise SystemExit(main())
