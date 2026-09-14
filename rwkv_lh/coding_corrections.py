"""Offline, source-bound validation of supplied atomic coding corrections.

No model invocation, target synthesis, dataset publication or training. External
checks/reviews are audit-only and are never appended to the production input.
"""
import hashlib
import json
import math
from pathlib import Path

from . import model_io
from .direct_trace_data import replay_run, executed_arguments
from .harness import ActionHarness
from .schema import GoalState, TaskAction
from .workspace_snapshot import tree_identity, copy_verified_workspace, file_inventory


def tree_sha256(tree):
    return hashlib.sha256(json.dumps(tree, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def validate_coding_correction(*, run_root, checkpoint_id, target_text, model_sha256,
                               source_files, snapshot, snapshot_sha256, checks, reviews, output,
                               check_timeout_seconds=30):
    root, output = Path(run_root).resolve(strict=True), Path(output).resolve()
    if output == root or root in output.parents or output in root.parents or output.exists():
        raise ValueError('validation output exists or overlaps source')
    required = {'state_snapshot.json', 'model_trace.jsonl', 'RESULT.json'}
    if (root / 'PARENT_TRACE.jsonl').exists():
        required.add('PARENT_TRACE.jsonl')
    if not required <= source_files.keys():
        raise ValueError('missing sealed source artifacts')
    for relative, digest in source_files.items():
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or root not in (root / path).resolve().parents:
            raise ValueError('unsafe source member')
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != digest:
            raise ValueError('source checksum differs: ' + relative)
    result = json.loads((root / 'RESULT.json').read_text())
    if result.get('tool_scope') != 'coding' or result.get('assistance') not in ('rwkv_independent', 'strong_advised'):
        raise ValueError('coding RWKV source required; takeover is not independent correction evidence')
    actual = replay_run(root, model_sha256)[checkpoint_id]
    before = (root / snapshot).resolve(strict=True)
    if before.parent.parent == root / 'generation_snapshots':
        from .correction_snapshots import validate_generation_snapshot
        before = validate_generation_snapshot(root, actual, source_files, snapshot=snapshot)
    else:
        original = model_io.parse_model_command(actual['raw_generation']['raw_output'])
        if original.name not in ('write_file', 'replace_text'):
            raise ValueError('only recorded atomic file-edit boundaries supported')
        if root not in before.parents or before.name != 'before' or before.parent.parent != root / 'tool_snapshots':
            raise ValueError('snapshot must be a recorded before boundary')
        calls = sorted((root / 'tool_snapshots').glob('*/call.json'))
        matching = []
        for path in calls:
            if str(path.relative_to(root)) not in source_files:
                raise ValueError('unsealed source call identity')
            call = json.loads(path.read_text())
            if call.get('action_type') == original.name and ActionHarness().normalize_action(TaskAction(original.name, call['arguments'])).arguments == executed_arguments(original):
                matching.append(path.parent / 'before')
        if matching != [before]:
            raise ValueError('ambiguous or unrelated source snapshot')
    if tree_sha256(tree_identity(before)) != snapshot_sha256:
        raise ValueError('snapshot identity differs')
    stop = model_io.JSON_CALL_STOP_SUFFIXES[0]
    if not isinstance(target_text, str) or not target_text.endswith(stop):
        raise ValueError('candidate requires exact production stop')
    raw = target_text[:-len(stop)]
    json.loads(raw)
    target = model_io.parse_model_command(raw)
    if target.name not in ('write_file', 'replace_text'):
        raise ValueError('only atomic file-edit correction candidates supported')
    # Validation only: the original target bytes and arguments are never repaired.
    harness = ActionHarness()
    action = TaskAction(target.name, target.arguments)
    harness.normalize_action(action)
    if (len({r.get('reviewer') for r in reviews}) < 2 or not all(
            isinstance(r.get('reviewer'), str) and r['reviewer'].strip()
            and r.get('accepted') is True and r.get('visible_evidence_only') is True
            and r.get('target_sha256') == _sha(target_text)
            and r.get('input_sha256') == _sha(actual['input_text']) for r in reviews)):
        raise ValueError('two source-bound reviews required')
    if not checks or not all(isinstance(argv, list) and argv and all(isinstance(v, str) for v in argv) for argv in checks):
        raise ValueError('explicit external verification commands required')
    if type(check_timeout_seconds) not in (int, float) or not math.isfinite(check_timeout_seconds) or not 0 < check_timeout_seconds <= 120:
        raise ValueError('check timeout must be in (0, 120] seconds')
    output.mkdir(parents=True)
    record = {'status': 'started', 'training_admitted': False, 'source_assistance': result['assistance'],
              'run_root': str(root), 'checkpoint_id': checkpoint_id, 'model_sha256': model_sha256,
              'input_checkpoint_id': actual['input_checkpoint_id'], 'request_id': actual['request_id'],
              'input_text': actual['input_text'], 'input_token_ids': actual['input_token_ids'],
              'original_output': actual['raw_generation']['raw_output'], 'target_text': target_text,
              'source_files': dict(source_files), 'snapshot': snapshot, 'snapshot_sha256': snapshot_sha256,
              'reviews': reviews, 'checks': checks, 'check_timeout_seconds': check_timeout_seconds,
              'before_checks': [], 'after_checks': []}
    def save(status):
        record['status'] = status
        (output / 'VALIDATION.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
        return record
    def goal(workspace):
        return GoalState.create(request='External correction validation', constraints=(), workspace_root=str(workspace))
    def run_checks(workspace, key):
        for argv in checks:
            value = harness.execute(TaskAction('run_command', {'argv': argv, 'expected_exit_code': 0,
                'timeout': check_timeout_seconds, 'env': {'CUDA_DEVICE_ORDER': 'PCI_BUS_ID', 'CUDA_VISIBLE_DEVICES': '0'}}), goal(workspace)).to_dict()
            record[key].append(value)
            save('checking')
        return record[key]
    save('started')
    try:
        baseline, corrected = output / 'baseline', output / 'corrected'
        for destination in (baseline, corrected):
            if tree_sha256(copy_verified_workspace(before, destination)) != snapshot_sha256:
                raise ValueError('source snapshot changed before copy')
        results = run_checks(baseline, 'before_checks')
        if not (all(type(r.get('exit_code')) is int for r in results) and any(r['exit_code'] != 0 for r in results)):
            return save('baseline_not_reproduced')
        initial = tree_identity(corrected)
        record['tool_result'] = harness.execute(action, goal(corrected)).to_dict()
        if not record['tool_result']['success']:
            return save('candidate_tool_failed')
        final = tree_identity(corrected)
        record['corrected_tree'] = final
        if file_inventory(initial) == file_inventory(final):
            return save('no_effective_change')
        # Tests get a separate copy: their writes cannot manufacture the patch.
        checked = output / 'checked'
        copy_verified_workspace(corrected, checked)
        results = run_checks(checked, 'after_checks')
        if not all(type(r.get('exit_code')) is int and r['exit_code'] == 0 and r.get('success') is True for r in results):
            return save('verification_failed')
        return save('validated_candidate')
    except BaseException as exc:
        record['error_type'] = type(exc).__name__
        save('validation_error')
        raise


def revalidate_training_correction(row, *, run_root, source_files, model_sha256, output):
    """Freeze-time proof binding plus fresh isolated execution, never label repair."""
    from .statetune_core import read_sealed_json, require
    reference = row['correction_validation']
    proof = read_sealed_json(reference['path'], reference['sha256'])
    require(proof.get('status') == 'validated_candidate', 'correction proof not validated')
    require(Path(proof['run_root']).resolve() == Path(run_root).resolve()
            and proof['source_files'] == dict(source_files)
            and proof['model_sha256'] == model_sha256, 'correction source binding differs')
    root = Path(run_root).resolve(strict=True)
    snapshot = (root / proof['snapshot']).resolve(strict=True)
    require(root in snapshot.parents, 'correction snapshot binding differs')
    for member in snapshot.rglob('*'):
        if member.is_file():
            require(str(member.relative_to(root)) in source_files,
                    'unsealed correction snapshot member')
    for row_key, proof_key in (
        ('target_text', 'target_text'), ('input_text', 'input_text'),
        ('input_token_ids', 'input_token_ids'), ('candidate_checkpoint_id', 'checkpoint_id'),
        ('input_checkpoint_id', 'input_checkpoint_id'), ('request_id', 'request_id'),
        ('reviews', 'reviews'),
    ):
        require(row.get(row_key) == proof.get(proof_key), 'correction row binding differs: ' + row_key)
    result = validate_coding_correction(
        run_root=run_root, checkpoint_id=proof['checkpoint_id'], target_text=row['target_text'],
        model_sha256=model_sha256, source_files=source_files, snapshot=proof['snapshot'],
        snapshot_sha256=proof['snapshot_sha256'], checks=proof['checks'], reviews=row['reviews'],
        output=output, check_timeout_seconds=proof['check_timeout_seconds'])
    require(result['status'] == 'validated_candidate', 'fresh correction verification failed')
    return result
