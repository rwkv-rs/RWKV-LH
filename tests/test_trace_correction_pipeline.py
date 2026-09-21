import json
from pathlib import Path

import pytest

from rwkv_lh import trace_correction_pipeline as p
from rwkv_lh.direct_trace_data import replay_run
from test_unified_controller import call


@pytest.fixture
def prepared(tmp_path):
    root = Path(__file__).resolve().parents[1] / 'data/pipeline/sources/timestamp-offset'
    model = '559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
    rows = replay_run(root, model)
    cp = next(iter(rows))
    plan = {'source_purpose': 'production_training_source', 'source_id': 'timestamp-offset',
            'family': 'timebook', 'run_root': str(root),
            'source_files': {str(f.relative_to(root)): p.file_sha(f) for f in root.rglob('*') if f.is_file()},
            'model_sha256': model, 'checkpoint_id': cp, 'max_target_tokens': 1800,
            'context_tokens': 24576, 'allowed_functions': ['write_file', 'final_answer'],
            'protected_paths': ['test_timestamp_offset.py'], 'read_only': False,
            'public_contract_provenance': 'test uses public source contract',
            'checks': [['python3', '-m', 'unittest', 'test_timestamp_offset']]}
    out = tmp_path / 'job'
    result = p.prepare(plan, out)
    return out, result['packet_sha256'], plan


class Teacher:
    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def complete(self, system, user):
        self.calls += 1
        return self.reply, {'model': 'offline-test-double', 'request_id': 'unit', 'response_sha256': '0' * 64}


def test_real_boundary_replayed_and_protected_edit_rejected(prepared):
    out, sha, plan = prepared
    teacher = Teacher(call('write_file', path='test_timestamp_offset.py', content='pass'))
    result = p.run(out, expected_packet_sha256=sha, teacher=teacher)
    assert result['status'] == 'quarantined' and result['reason'] == 'protected_or_unsafe_edit'
    assert teacher.calls == 1 and not (out / 'execution').exists()
    assert p.run(out, expected_packet_sha256=sha, teacher=teacher) == result
    assert teacher.calls == 1


def test_packet_tamper_rejected_before_api(prepared):
    out, sha, _ = prepared
    with (out / 'PACKET.json').open('a') as handle:
        handle.write(' ')
    teacher = Teacher({})
    with pytest.raises(ValueError, match='identity'):
        p.run(out, expected_packet_sha256=sha, teacher=teacher)
    assert teacher.calls == 0


def test_eval_source_and_readonly_mutation_contract_rejected(prepared, tmp_path):
    _, _, plan = prepared
    with pytest.raises(ValueError, match='sources'):
        p.prepare(dict(plan, source_purpose='development_evaluation'), tmp_path / 'eval')
    with pytest.raises(ValueError, match='read-only'):
        p.prepare(dict(plan, read_only=True), tmp_path / 'readonly')


def test_truncated_target_is_quarantined_not_shortened(prepared):
    out, sha, _ = prepared
    teacher = Teacher(call('write_file', path='timebook.py', content='x = 1\n' * 4000))
    result = p.run(out, expected_packet_sha256=sha, teacher=teacher)
    assert result['reason'] == 'target_or_context_limit_no_truncation'
    assert teacher.calls == 1


def test_report_keeps_rejections_and_never_claims_dataset_ready(prepared):
    out, sha, _ = prepared
    teacher = Teacher(call('write_file', path='test_timestamp_offset.py', content='pass'))
    p.run(out, expected_packet_sha256=sha, teacher=teacher)
    result = p.summarize([out])
    assert result['jobs'] == 1 and result['statuses'] == {'quarantined': 1}
    assert result['dataset_ready'] is False and result['training_admitted'] == 0
    with pytest.raises(ValueError, match='duplicate'):
        p.summarize([out, out])


def test_generator_change_rejected_before_api(prepared, monkeypatch):
    directory, sha, _ = prepared
    teacher = Teacher({})
    monkeypatch.setattr(p, 'pipeline_identity', lambda: {})
    with pytest.raises(ValueError, match='pipeline code changed'):
        p.run(directory, expected_packet_sha256=sha, teacher=teacher)
    assert teacher.calls == 0
