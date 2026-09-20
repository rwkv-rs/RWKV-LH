"""Offline next-command supervision at a real RWKV boundary; no model repair.

A test that exposes the bug can be a useful next action while the task remains
unfinished. Expected outcomes and reviews are external evidence, never input.
"""
import hashlib
import json
from pathlib import Path
from . import model_io
from .direct_trace_data import replay_run, executed_arguments
from .harness import ActionHarness
from .schema import GoalState, TaskAction
from .workspace_snapshot import copy_verified_workspace, tree_identity
from .statetune_core import require, verify_file, read_sealed_json


def validate_command_correction(*, run_root, checkpoint_id, target_text, model_sha256,
                                source_files, reviews, expected_exit_code, expected_output, output):
    root=Path(run_root).resolve(strict=True); output=Path(output).resolve()
    require(not output.exists() and output != root and root not in output.parents and output not in root.parents,
            'output overlaps source or exists')
    required={'RESULT.json','model_trace.jsonl','state_snapshot.json'}
    if (root/'PARENT_TRACE.jsonl').exists():required.add('PARENT_TRACE.jsonl')
    require(required <= source_files.keys(),'source artifacts missing')
    for name,digest in source_files.items():
        relative=Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts and root in (root/relative).resolve().parents,'unsafe source path')
        verify_file(root/relative,digest)
    result=json.loads((root/'RESULT.json').read_text())
    require(result.get('tool_scope')=='coding' and result.get('assistance') in ('rwkv_independent','strong_advised'),
            'RWKV coding source required')
    actual=replay_run(root,model_sha256)[checkpoint_id]
    state=json.loads((root/'state_snapshot.json').read_text())
    if (root/'generation_snapshots').is_dir():
        from .correction_snapshots import validate_generation_snapshot
        snapshot=validate_generation_snapshot(root,actual,source_files)
        source_action_id=None
    else:
        events=[json.loads(line) for line in (root/'model_trace.jsonl').read_text().splitlines()]
        requests={e['request_id'] for e in events if e['type']=='model_session_generation_returned'}
        actions=sorted((a for a in state['actions'].values() if a['request_id'] in requests),key=lambda a:a['sequence'])
        calls=sorted((root/'tool_snapshots').glob('*/call.json'))
        require(len(actions)==len(calls),'source action/snapshot count differs')
        matches=[]
        for action,path in zip(actions,calls):
            require(str(path.relative_to(root)) in source_files,'unsealed source call')
            call=json.loads(path.read_text())
            require(action['action_type']==call['action_type'] and action['arguments']==call['arguments'],'source action/snapshot binding differs')
            if action['request_id']==actual['request_id']:matches.append((action,path))
        require(len(matches)==1,'source request has no unique executed boundary')
        action,path=matches[0]
        original=model_io.parse_model_command(actual['raw_generation']['raw_output'])
        require(original.name==action['action_type'] and executed_arguments(original)==action['arguments'],'source command binding differs')
        snapshot=path.parent/'before'
        require(snapshot.is_dir(),'source boundary has no recorded before snapshot')
        for member in snapshot.rglob('*'):
            if member.is_file():require(str(member.relative_to(root)) in source_files,'unsealed source snapshot')
        source_action_id=action['action_id']
    stop=model_io.JSON_CALL_STOP_SUFFIXES[0]
    require(isinstance(target_text,str) and target_text.endswith(stop),'exact production stop required')
    raw=target_text[:-len(stop)];json.loads(raw);command=model_io.parse_model_command(raw)
    require(command.name in ('check_command','run_command'),'only command execution targets supported')
    normalized = executed_arguments(command)
    require(normalized.get('timeout', 30) <= 120, 'command exceeds correction execution budget')
    digest=lambda s:hashlib.sha256(s.encode()).hexdigest()
    from .correction_review import require_source_bound_reviews
    require_source_bound_reviews(reviews, input_sha256=digest(actual['input_text']),
                                 target_sha256=digest(target_text), execution_backed=True)
    require(type(expected_exit_code) is int and 0 <= expected_exit_code <= 255
            and isinstance(expected_output,list) and expected_output
            and all(isinstance(s,str) and s.strip() for s in expected_output),'explicit external command outcome required')
    output.mkdir(parents=True)
    record={'status':'started','training_admitted':False,'run_root':str(root),'checkpoint_id':checkpoint_id,
        'model_sha256':model_sha256,'source_files':dict(source_files),'source_action_id':source_action_id,
        'source_assistance':result['assistance'],'snapshot':str(snapshot.relative_to(root)),
        'input_text':actual['input_text'],'input_token_ids':actual['input_token_ids'],
        'input_checkpoint_id':actual['input_checkpoint_id'],'request_id':actual['request_id'],
        'original_output':actual['raw_generation']['raw_output'],'target_text':target_text,'reviews':reviews,
        'expected_exit_code':expected_exit_code,'expected_output':expected_output}
    def save(status):
        record['status']=status;(output/'VALIDATION.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');return record
    save('started')
    try:
        workspace=output/'workspace'
        record['before_tree']=copy_verified_workspace(snapshot,workspace)
        goal=GoalState.create(request=state['goal']['request'],constraints=(),workspace_root=str(workspace))
        observation=ActionHarness().execute(TaskAction(command.name,command.arguments),goal).to_dict()
        record['tool_result']=observation;record['after_tree']=tree_identity(workspace)
        valid=type(observation.get('exit_code')) is int and observation['exit_code']==expected_exit_code
        valid=valid and (observation.get('error') or {}).get('type') in (None,'CommandFailed')
        valid=valid and all(text in observation.get('output','') for text in expected_output)
        valid=valid and not observation.get('metadata',{}).get('output_truncated',False)
        return save('validated_candidate' if valid else 'verification_failed')
    except BaseException as exc:
        record['error_type']=type(exc).__name__;save('validation_error');raise


def revalidate_training_command(row, *, run_root, source_files, model_sha256, output):
    reference=row['command_validation'];proof=read_sealed_json(reference['path'],reference['sha256'])
    require(proof.get('status')=='validated_candidate' and Path(proof['run_root']).resolve()==Path(run_root).resolve()
            and proof['source_files']==dict(source_files) and proof['model_sha256']==model_sha256,'command source binding differs')
    for key,other in (('target_text','target_text'),('input_text','input_text'),('input_token_ids','input_token_ids'),
                      ('candidate_checkpoint_id','checkpoint_id'),('input_checkpoint_id','input_checkpoint_id'),
                      ('request_id','request_id'),('reviews','reviews')):
        require(row.get(key)==proof.get(other),'command row binding differs: '+key)
    result=validate_command_correction(run_root=run_root,checkpoint_id=proof['checkpoint_id'],target_text=row['target_text'],
        model_sha256=model_sha256,source_files=source_files,reviews=row['reviews'],
        expected_exit_code=proof['expected_exit_code'],expected_output=proof['expected_output'],output=output)
    require(result['status']=='validated_candidate','fresh command verification failed')
    return result
