import json
import pytest
from test_trace_correction_pipeline import prepared
from rwkv_lh import trace_correction_pipeline as p
from rwkv_lh.observation_corrections import validate_observation_correction
from rwkv_lh.model_io import JSON_CALL_STOP_SUFFIXES
from rwkv_lh.offline_teacher_api import digest


def test_read_is_executed_and_no_workspace_mutation(prepared, tmp_path):
    directory, sha, plan = prepared
    packet = json.loads((directory / 'PACKET.json').read_text())
    target = json.dumps({'function': 'read_file', 'params': {'path': 'timebook.py'}}) + JSON_CALL_STOP_SUFFIXES[0]
    review = {'accepted': True, 'issues': [], 'assessment': 'Inspect source requested by user.', 'claims': []}
    reviews = [{'reviewer': 'test', 'accepted': True, 'visible_evidence_only': True,
                'independent': False, 'review_mode': 'single_author_execution',
                'assessment': review['assessment'], 'input_sha256': digest(packet['actual']['input_text']),
                'target_sha256': digest(target)}]
    result = validate_observation_correction(run_root=plan['run_root'], checkpoint_id=plan['checkpoint_id'],
        target_text=target, model_sha256=plan['model_sha256'], source_files=plan['source_files'],
        reviews=reviews, judgment=review, output=tmp_path / 'proof')
    assert result['status'] == 'validated_candidate'
    assert result['tool_result']['success'] is True
    assert result['before_tree'] == result['after_tree']
    assert 'def parse_timestamp' in result['tool_result']['output']


def test_batch_duplicate_boundary_fails_before_api(prepared):
    directory, sha, _ = prepared
    class Teacher:
        def complete(self, *args):
            pytest.fail('duplicate batch must not call API')
    job = {'directory': str(directory), 'packet_sha256': sha}
    with pytest.raises(ValueError, match='duplicate'):
        p.run_batch({'jobs': [job, job]}, teacher=Teacher())


def test_final_cannot_use_a_review_to_invent_execution(prepared, tmp_path):
    directory, sha, plan = prepared
    packet = json.loads((directory / 'PACKET.json').read_text())
    # The first generation has no tool execution, even though it has a task.
    text = 'test_timestamp_offset.py'
    target = json.dumps({'function': 'final_answer', 'params': {'text': text}}) + JSON_CALL_STOP_SUFFIXES[0]
    review = {'accepted': True, 'issues': [], 'assessment': 'Fixture-only accepted review.',
              'claims': [{'quote': text, 'status': 'supported', 'evidence_quote': text,
                          'reason': 'The task names this file.'}]}
    reviews = [{'reviewer': 'test', 'accepted': True, 'visible_evidence_only': True,
                'independent': False, 'review_mode': 'single_author_execution',
                'assessment': review['assessment'], 'input_sha256': digest(packet['actual']['input_text']),
                'target_sha256': digest(target)}]
    result = validate_observation_correction(run_root=plan['run_root'], checkpoint_id=plan['checkpoint_id'],
        target_text=target, model_sha256=plan['model_sha256'], source_files=plan['source_files'],
        reviews=reviews, judgment=review, output=tmp_path / 'final-proof')
    assert result['status'] == 'verification_failed'
    assert result['visible_execution_events'] == {}


def test_final_records_actual_visible_tool_events(prepared, tmp_path):
    from rwkv_lh.direct_trace_data import replay_run
    from pathlib import Path
    _, _, plan = prepared
    rows = replay_run(Path(plan['run_root']), plan['model_sha256'])
    checkpoint, actual = list(rows.items())[-1]
    text = '已读取 timebook.py 中 parse_timestamp 的实现。'
    target = json.dumps({'function': 'final_answer', 'params': {'text': text}}) + JSON_CALL_STOP_SUFFIXES[0]
    review = {'accepted': True, 'issues': [], 'assessment': 'Fixture tests provenance, not task completion.',
              'claims': [{'quote': text, 'status': 'supported', 'evidence_quote': 'def parse_timestamp(value):',
                          'reason': 'Actual read result includes the source definition.'}]}
    reviews = [{'reviewer': 'test', 'accepted': True, 'visible_evidence_only': True,
                'independent': False, 'review_mode': 'single_author_execution',
                'assessment': review['assessment'], 'input_sha256': digest(actual['input_text']),
                'target_sha256': digest(target)}]
    result = validate_observation_correction(run_root=plan['run_root'], checkpoint_id=checkpoint,
        target_text=target, model_sha256=plan['model_sha256'], source_files=plan['source_files'],
        reviews=reviews, judgment=review, output=tmp_path / 'final-observed')
    assert result['status'] == 'validated_candidate'
    assert result['visible_execution_events']
    assert result['training_admitted'] is False
