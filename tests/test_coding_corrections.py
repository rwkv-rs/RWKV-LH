import hashlib
import json
import pytest
from rwkv_lh import model_io
from rwkv_lh.coding_corrections import validate_coding_correction, tree_sha256
from rwkv_lh.workspace_snapshot import tree_identity
from test_unified_controller import call


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    import rwkv_lh.coding_corrections as module
    root = tmp_path / 'source'; before = root / 'tool_snapshots/001/before'; before.mkdir(parents=True)
    (before / 'a.py').write_text('value = 1\n')
    original = json.dumps(call('write_file', path='a.py', content='value = 1\n'))
    target = json.dumps(call('write_file', path='a.py', content='value = 2\n')) + model_io.JSON_CALL_STOP_SUFFIXES[0]
    (before.parent / 'call.json').write_text(json.dumps({'action_type': 'write_file', 'arguments': {'path': 'a.py', 'content': 'value = 1\n'}}))
    for name in ('state_snapshot.json', 'model_trace.jsonl'):
        (root / name).write_text('{}')
    (root / 'RESULT.json').write_text(json.dumps({'tool_scope': 'coding', 'assistance': 'rwkv_independent'}))
    monkeypatch.setattr(module, 'replay_run', lambda *args: {'cp': {'input_text': 'visible input', 'input_token_ids': [0, 1],
        'input_checkpoint_id': 'parent', 'request_id': 'r', 'raw_generation': {'raw_output': original}}})
    return dict(run_root=root, checkpoint_id='cp', target_text=target, model_sha256='a'*64,
        source_files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},
        snapshot='tool_snapshots/001/before', snapshot_sha256=tree_sha256(tree_identity(before)),
        checks=[['python3', '-B', '-c', 'from a import value; assert value == 2']],
        reviews=[{'reviewer': r, 'accepted': True, 'visible_evidence_only': True,
                  'target_sha256': sha(target), 'input_sha256': sha('visible input')} for r in ('one', 'two')],
        output=tmp_path / 'validation')


def test_correction_executes_real_red_green_without_modifying_source(candidate):
    result = validate_coding_correction(**candidate)
    assert result['status'] == 'validated_candidate'
    assert result['training_admitted'] is False
    assert result['before_checks'][0]['exit_code'] != 0
    assert result['after_checks'][0]['exit_code'] == 0
    assert (candidate['run_root'] / candidate['snapshot'] / 'a.py').read_text() == 'value = 1\n'
    assert result['target_text'] == candidate['target_text']


def test_noop_correction_is_not_a_valid_edit(candidate):
    target = json.dumps(call('write_file', path='a.py', content='value = 1\n')) + model_io.JSON_CALL_STOP_SUFFIXES[0]
    candidate['target_text'] = target
    for review in candidate['reviews']: review['target_sha256'] = sha(target)
    assert validate_coding_correction(**candidate)['status'] == 'no_effective_change'


def test_missing_test_program_is_not_red_evidence(candidate):
    candidate['checks'] = [['/nonexistent/rwkv-test-program']]
    assert validate_coding_correction(**candidate)['status'] == 'baseline_not_reproduced'


def test_test_claim_without_real_success_is_rejected(candidate):
    candidate['checks'] = [['python3', '-B', '-c', 'raise SystemExit(1)']]
    assert validate_coding_correction(**candidate)['status'] == 'verification_failed'


def test_candidate_without_bound_reviews_does_not_execute(candidate):
    candidate['reviews'][0]['input_sha256'] = 'b'*64
    with pytest.raises(ValueError, match='reviews'):
        validate_coding_correction(**candidate)
    assert not candidate['output'].exists()


def test_changed_source_is_rejected_before_execution(candidate):
    (candidate['run_root'] / 'model_trace.jsonl').write_text('tampered')
    with pytest.raises(ValueError, match='source'):
        validate_coding_correction(**candidate)
    assert not candidate['output'].exists()


def test_future_or_wrong_snapshot_cannot_be_substituted(candidate):
    candidate['snapshot_sha256'] = 'b'*64
    with pytest.raises(ValueError, match='snapshot'):
        validate_coding_correction(**candidate)


def test_takeover_is_not_rwkv_correction_source(candidate):
    path = candidate['run_root'] / 'RESULT.json'
    path.write_text(json.dumps({'tool_scope': 'coding', 'assistance': 'strong_takeover'}))
    candidate['source_files']['RESULT.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='takeover'):
        validate_coding_correction(**candidate)


def test_real_failed_write_is_replayed_and_rejected_as_noop(tmp_path):
    import tarfile
    from pathlib import Path
    from rwkv_lh.direct_trace_data import replay_run
    archive = Path(__file__).resolve().parents[1] / 'data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/EVIDENCE.tar.gz'
    prefix = 'runs/atomic-2/execution/'
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.isfile() and m.name.startswith(prefix)
                   and (m.name[len(prefix):] in ('RESULT.json', 'model_trace.jsonl', 'state_snapshot.json')
                        or '/tool_snapshots/' in m.name)]
        tar.extractall(tmp_path, members=members, filter='data')
    root = tmp_path / prefix
    model_sha = '559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
    rows = replay_run(root, model_sha)
    cp, row = next((cp, row) for cp, row in rows.items()
                   if model_io.parse_model_command(row['raw_generation']['raw_output']).name == 'write_file')
    original = row['raw_generation']['raw_output']
    target = original if original.endswith(model_io.JSON_CALL_STOP_SUFFIXES[0]) else original + model_io.JSON_CALL_STOP_SUFFIXES[0]
    reviews = [{'reviewer': r, 'accepted': True, 'visible_evidence_only': True,
                'target_sha256': sha(target), 'input_sha256': sha(row['input_text'])}
               for r in ('unit-test-review-a', 'unit-test-review-b')]
    result = validate_coding_correction(run_root=root, checkpoint_id=cp, target_text=target,
        model_sha256=model_sha,
        source_files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},
        snapshot='tool_snapshots/002/before', snapshot_sha256=tree_sha256(tree_identity(root / 'tool_snapshots/002/before')),
        checks=[['python3', '-B', '-m', 'unittest', 'test_query_limit']], reviews=reviews, output=tmp_path / 'audit')
    assert result['status'] == 'no_effective_change'
    assert result['training_admitted'] is False
