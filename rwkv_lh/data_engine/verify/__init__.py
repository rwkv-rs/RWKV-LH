"""Independent real checker execution; no checker bytes or expected values reach policies."""
import hashlib
import json
from pathlib import Path
import shutil
from rwkv_lh.benchmark_verifier import run_isolated_verifier
from rwkv_lh.project_contracts import scope_path
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.workspace_snapshot import tree_identity
from rwkv_lh.evaluation_policy import assert_training_record_allowed, assert_training_source_allowed
from rwkv_lh.data_engine.tasks import checksum, dump


def write_files(root, files):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    for name,content in files.items():
        scope_path(name)
        path=root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()): raise ValueError('unsafe task file')
        path.write_bytes(content.encode('utf-8'))


def verify(task, workspace, evidence):
    evidence=Path(evidence)
    result=run_isolated_verifier(task['acceptance'],workspace,[],{},private_root=evidence.parent/'private',
        evidence_dir=evidence,timeout_seconds=90)
    record={'task_digest':task['digest'],'workspace':tree_identity(workspace),'passed':result.passed,
        'checks':[c.to_dict() for c in result.checks],'metadata':result.metadata,
        'verifier_sha256':checksum(task['acceptance']),
        'verifier_adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (evidence/'VERDICT.json').write_text(dump(record))
    return record


def admit(task, directory):
    assert_training_record_allowed(task)
    assert_training_source_allowed(directory)
    if checksum({k:v for k,v in task.items() if k!='digest'})!=task['digest']: raise ValueError('task identity differs')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    (directory/'task.json').write_text(dump(task))
    for name in ('seed','reference',*(f'mutant-{i}' for i in range(len(task['mutants'])))):
        write_files(directory/name,task['seed_files'])
    write_files(directory/'reference',task['reference_files'])
    reference=verify(task,directory/'reference',directory/'evidence/reference')
    first_reference = None
    if task.get('followups'):
        write_files(directory/'first_reference',task['seed_files'])
        write_files(directory/'first_reference',task['first_reference_files'])
        first_reference=verify({**task,'acceptance':task['first_acceptance']},
            directory/'first_reference',directory/'evidence/first_reference')
    seed=verify(task,directory/'seed',directory/'evidence/seed')
    mutants=[]
    for i,files in enumerate(task['mutants']):
        path=directory/f'mutant-{i}'
        write_files(path,task['reference_files']);write_files(path,files)
        mutants.append(verify(task,path,directory/f'evidence/mutant-{i}'))
    passed=(reference['passed'] and (first_reference is None or first_reference['passed'])
        and bool(mutants) and all(not r['passed'] for r in mutants)
        and (not task.get('seed_must_fail') or not seed['passed']))
    record={'task_digest':task['digest'],'admitted':passed,'reference_passed':reference['passed'],
        'seed_passed':seed['passed'],'mutants_failed':[not r['passed'] for r in mutants],
        'first_reference_passed':None if first_reference is None else first_reference['passed']}
    (directory/'ADMISSION.json').write_text(dump(record))
    if not passed:raise ValueError('reference/mutant admission failed: '+task['id'])
    return record


def turn_facts(execution):
    with ProjectLedger.read_snapshot(execution) as db: state=db.scan_verified_events()['state']
    labels=[]
    if state['rejections']:labels.append('protocol_rejected')
    if state['stop_reason']=='model_output_budget_exhausted':labels.append('truncated')
    if state['status']!='finished':labels.append('not_finished')
    if any(v['kind']=='tool' and not v['result'].get('success') for v in state['evidence'].values()):labels.append('tool_failure')
    return labels
