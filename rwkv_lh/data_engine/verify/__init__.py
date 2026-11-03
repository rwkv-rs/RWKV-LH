"""Independent real checker execution; no checker bytes or expected values reach policies."""
import hashlib
import json
from pathlib import Path
import shutil
from rwkv_lh.benchmark_verifier import run_isolated_verifier
from rwkv_lh.project_contracts import scope_path
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.workspace_snapshot import tree_identity, copy_verified_workspace
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
        evidence_dir=evidence,timeout_seconds=task.get('verification_timeout_seconds',90))
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
    if 'workspace_snapshots' in task:
        return _admit_snapshots(task, directory)
    for name in ('seed','reference',*(f'mutant-{i}' for i in range(len(task['mutants'])))):
        write_files(directory/name,task['seed_files'])
    write_files(directory/'reference',task['reference_files'])
    repetitions=task.get('reference_repetitions',1)
    if type(repetitions) is not int or repetitions<1:
        raise ValueError('positive reference repetition count required')
    references=[verify(task,directory/'reference',directory/f'evidence/reference-{i}')
                for i in range(repetitions)]
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
    passed=(all(reference['passed'] for reference in references) and (first_reference is None or first_reference['passed'])
        and bool(mutants) and all(not r['passed'] for r in mutants)
        and (not task.get('seed_must_fail') or not seed['passed']))
    record={'task_digest':task['digest'],'admitted':passed,'reference_passed':all(r['passed'] for r in references),
        'reference_repetitions':[r['passed'] for r in references],
        'seed_passed':seed['passed'],'mutants_failed':[not r['passed'] for r in mutants],
        'first_reference_passed':None if first_reference is None else first_reference['passed']}
    (directory/'ADMISSION.json').write_text(dump(record))
    if not passed:raise ValueError('reference/mutant admission failed: '+task['id'])
    return record


def _admit_snapshots(task, directory):
    """Use the same sandbox/verifier for full repositories, including binary files.

    Base reproduction is a separate positive check: an arbitrary failing test
    process is insufficient. Every oracle run gets a fresh verifier namespace.
    The original failing tree is a valid defect mutant for an upstream bug task.
    """
    snapshots = task['workspace_snapshots']
    if task.get('followups'):
        raise ValueError('snapshot followups require separately frozen reference admission')
    repetitions = task.get('reference_repetitions')
    if type(repetitions) is not int or repetitions < 3 or not snapshots['mutants']:
        raise ValueError('three reference runs and defect mutants required')
    if not task.get('base_acceptance'):
        raise ValueError('explicit base reproduction check required')
    sources = [('seed', snapshots['seed']), ('reference', snapshots['reference'])]
    sources += [(f'mutant-{i}', v) for i, v in enumerate(snapshots['mutants'])]
    # Check every source before copying any. Marked development sources remain
    # excluded even if somebody wraps them in a new task manifest.
    for _, snapshot in sources:
        assert_training_source_allowed(snapshot['path'])
        if checksum(tree_identity(snapshot['path'], exclude_git=True)) != snapshot['tree_sha256']:
            raise ValueError('frozen workspace snapshot identity differs')
    for name, snapshot in sources:
        copied = copy_verified_workspace(snapshot['path'], directory/name,
            audit_path=directory/'copies'/(name+'.json'))
        if checksum(copied) != snapshot['tree_sha256']:
            raise ValueError('frozen workspace snapshot identity changed during copy')
    reference = [verify(task, directory/'reference', directory/f'evidence/reference-{i}')
                 for i in range(repetitions)]
    seed = verify(task, directory/'seed', directory/'evidence/seed')
    base = verify({**task, 'acceptance': task['base_acceptance']}, directory/'seed',
                  directory/'evidence/base-reproduction')
    mutants = [verify(task, directory/f'mutant-{i}', directory/f'evidence/mutant-{i}')
               for i in range(len(snapshots['mutants']))]
    passed = (all(v['passed'] for v in reference) and base['passed']
              and not seed['passed'] and all(not v['passed'] for v in mutants))
    record = {'task_digest': task['digest'], 'admitted': passed,
              'reference_passed': all(v['passed'] for v in reference),
              'reference_repetitions': [v['passed'] for v in reference],
              'base_reproduced': base['passed'], 'seed_passed': seed['passed'],
              'mutants_failed': [not v['passed'] for v in mutants]}
    (directory/'ADMISSION.json').write_text(dump(record))
    if not passed:
        raise ValueError('reference/mutant admission failed: '+task['id'])
    return record


def turn_facts(execution):
    with ProjectLedger.read_snapshot(execution) as db: state=db.scan_verified_events()['state']
    labels=[]
    if state['rejections']:labels.append('protocol_rejected')
    if state['stop_reason']=='model_output_budget_exhausted':labels.append('truncated')
    if state['status']!='finished':labels.append('not_finished')
    if any(v['kind']=='tool' and not v['result'].get('success') for v in state['evidence'].values()):labels.append('tool_failure')
    return labels
