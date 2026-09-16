from types import SimpleNamespace
from rwkv_lh.teacher_input import build_teacher_input


def test_teacher_input_keeps_real_output_and_excludes_audit_metadata():
    action = SimpleNamespace(to_dict=lambda: {
        'action_id': 'A1', 'action_type': 'run_command', 'arguments': {'argv': ['python3', 'main.py']},
        'status': 'failed', 'result': {'output': 'number 18/21\n', 'exit_code': 1,
        'success': False, 'metadata': {'output_truncated': False, 'raw_sha256': 'AUDIT_ONLY'}},
        'error': None})
    state = SimpleNamespace(actions={'A1': action}, model_events={})
    system, payload = build_teacher_input(goal='Fix the program', definitions=[{'name': 'run_command'}],
        failure_candidate='untrusted prior response', workspace_paths=['main.py'], state=state)
    assert payload['execution_history'][0]['result']['output'] == 'number 18/21\n'
    assert 'AUDIT_ONLY' not in str(payload)
    assert 'Fix the program' == payload['goal']
    assert 'final_answer' in system and 'stdin' in system


def test_teacher_input_preserves_truncation_and_protocol_rejection():
    event = SimpleNamespace(event_type='protocol_rejection', payload={'error': 'unknown parameter'})
    state = SimpleNamespace(actions={}, model_events={'E1': event})
    _, payload = build_teacher_input(goal='Implement', definitions=[{'name': 'read_file'}],
        failure_candidate='bad', workspace_paths=[], state=state)
    assert payload['protocol_feedback'] == [{'error': 'unknown parameter'}]
