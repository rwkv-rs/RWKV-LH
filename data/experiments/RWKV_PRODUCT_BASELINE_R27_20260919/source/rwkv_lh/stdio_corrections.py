"""Source-bound admission for exact-output stdio edits, with fresh private tests.

One explicit semantic/source review plus isolated execution is a distinct evidence
contract, not two invented model reviews. It does not cover final answers, float
comparators, arbitrary-output tasks, or unreviewed source contradictions.
"""
import hashlib
import json
from pathlib import Path

from . import model_io
from .direct_trace_data import replay_run
from .correction_snapshots import validate_generation_snapshot
from .harness import ActionHarness
from .schema import GoalState, TaskAction
from .statetune_core import require, verify_file, read_sealed_json
from .stdio_verifier import verify_python_submission, validate_stdio_cases
from .workspace_snapshot import copy_verified_workspace, tree_identity


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def validate_stdio_correction(*, run_root, checkpoint_id, target_text, model_sha256,
                              source_files, cases_reference, review, output):
    root=Path(run_root).resolve(strict=True); output=Path(output).resolve()
    require(not output.exists() and root!=output and root not in output.parents and output not in root.parents,
            'output exists or overlaps source')
    required={'RESULT.json','model_trace.jsonl','state_snapshot.json'}
    if (root/'PARENT_TRACE.jsonl').exists(): required.add('PARENT_TRACE.jsonl')
    require(required <= source_files.keys(),'unsealed source artifacts')
    for name,digest in source_files.items():
        path=root/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and root in path.resolve().parents,
                'unsafe source member')
        verify_file(path,digest)
    result=json.loads((root/'RESULT.json').read_text())
    require(result.get('tool_scope')=='coding' and result.get('assistance') in ('rwkv_independent','strong_advised'),
            'original RWKV source required')
    actual=replay_run(root,model_sha256)[checkpoint_id]
    before=validate_generation_snapshot(root,actual,source_files)
    stop=model_io.JSON_CALL_STOP_SUFFIXES[0]
    require(isinstance(target_text,str) and target_text.endswith(stop),'exact stop required')
    raw=target_text[:-len(stop)]; json.loads(raw); command=model_io.parse_model_command(raw)
    require(command.name=='write_file' and command.arguments.get('path')=='solution.py',
            'stdio contract requires writing the actual solution.py entry point')
    ActionHarness().normalize_action(TaskAction(command.name,command.arguments))
    task=before/'TASK.md'; require(task.is_file(),'source task absent')
    task_text=task.read_bytes().decode('utf-8')
    require(task_text in actual['input_text'] or json.dumps(task_text,ensure_ascii=False)[1:-1] in actual['input_text'],
            'complete source task not visible at correction boundary')
    require(isinstance(review,dict) and isinstance(review.get('reviewer'),str) and review['reviewer'].strip()
            and review.get('accepted') is True and review.get('visible_evidence_only') is True
            and review.get('source_consistent') is True and review.get('output_contract')=='exact_unique'
            and review.get('input_sha256')==_sha(actual['input_text'])
            and review.get('target_sha256')==_sha(target_text)
            and review.get('task_sha256')==hashlib.sha256(task.read_bytes()).hexdigest(),
            'bound source/semantic review required; unsupported output contract')
    require(isinstance(cases_reference,dict) and set(cases_reference)=={'path','sha256'},'sealed private cases required')
    case_path=Path(cases_reference['path']).resolve(strict=True)
    require(root not in case_path.parents and output not in case_path.parents,'private tests overlap source or output')
    cases=read_sealed_json(case_path,cases_reference['sha256']); validate_stdio_cases(cases)
    output.mkdir(parents=True)
    record={'status':'started','training_admitted':False,'run_root':str(root),'checkpoint_id':checkpoint_id,
            'model_sha256':model_sha256,'source_files':dict(source_files),'cases_reference':dict(cases_reference),
            'review':review,'target_text':target_text,'input_text':actual['input_text'],
            'input_token_ids':actual['input_token_ids'],'input_checkpoint_id':actual['input_checkpoint_id'],
            'request_id':actual['request_id'],'original_output':actual['raw_generation']['raw_output']}
    def save(status):
        record['status']=status
        (output/'VALIDATION.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        return record
    save('started')
    try:
        copy_verified_workspace(before,output/'baseline'); copy_verified_workspace(before,output/'corrected')
        record['baseline']=verify_python_submission(output/'baseline',cases)
        if record['baseline']['passed']: return save('baseline_not_reproduced')
        goal=GoalState.create(request=json.loads((root/'RESULT.json').read_text()).get('request','Implement the visible TASK.md'),
                              workspace_root=str(output/'corrected'),constraints=[])
        record['tool_result']=ActionHarness().execute(TaskAction(command.name,command.arguments),goal).to_dict()
        if not record['tool_result']['success']: return save('candidate_tool_failed')
        initial=tree_identity(before); changed=tree_identity(output/'corrected')
        # write_file is confined to the requested entry; source/task files remain immutable.
        require((output/'corrected/TASK.md').read_bytes()==task.read_bytes(),'task changed')
        record['before_tree']=initial; record['corrected_tree']=changed
        record['after']=verify_python_submission(output/'corrected',cases)
        verify_file(case_path,cases_reference['sha256'])
        return save('validated_candidate' if record['after']['passed'] else 'verification_failed')
    except BaseException as exc:
        record['error_type']=type(exc).__name__; save('validation_error'); raise


def revalidate_training_stdio(row, *, run_root, source_files, model_sha256, output):
    ref=row['stdio_validation']; proof=read_sealed_json(ref['path'],ref['sha256'])
    require(proof.get('status')=='validated_candidate' and Path(proof['run_root']).resolve()==Path(run_root).resolve()
            and proof['source_files']==dict(source_files) and proof['model_sha256']==model_sha256,'stdio source binding differs')
    for row_key,proof_key in [('candidate_checkpoint_id','checkpoint_id'),('target_text','target_text'),
                              ('input_text','input_text'),('input_token_ids','input_token_ids'),
                              ('input_checkpoint_id','input_checkpoint_id'),('request_id','request_id'),('stdio_review','review')]:
        require(row.get(row_key)==proof.get(proof_key),'stdio row binding differs: '+row_key)
    result=validate_stdio_correction(run_root=run_root,checkpoint_id=proof['checkpoint_id'],target_text=row['target_text'],
        model_sha256=model_sha256,source_files=source_files,cases_reference=proof['cases_reference'],
        review=proof['review'],output=output)
    require(result['status']=='validated_candidate','fresh stdio verification failed')
    return result
