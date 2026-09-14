import pytest
from rwkv_lh.usage_accounting import summarize_usage


def provider(events, *, attempt=1, usage=None):
    events.extend([
        {'type': 'supervisor_request_started', 'run_id': 'r', 'call_id': 'c', 'model': 'strong'},
        {'type': 'supervisor_http_attempt_started', 'run_id': 'r', 'call_id': 'c', 'attempt': attempt},
        {'type': 'supervisor_response_envelope_received', 'run_id': 'r', 'call_id': 'c', 'attempt': attempt,
         'model': 'strong', 'usage': usage, 'latency_ms': 12}])


def test_missing_usage_is_unknown_not_zero():
    events = []; provider(events)
    result = summarize_usage({'strong': events})
    assert result['provider_attempts'] == 1
    assert result['provider_input_tokens'] is None
    assert result['total_cost'] is None
    assert result['missing_usage_attempts'] == 1


def test_failed_retry_is_counted_and_prevents_complete_cost():
    events = [{'type': 'supervisor_http_attempt_started', 'run_id': 'r', 'call_id': 'c', 'attempt': 1}]
    provider(events, attempt=2, usage={'prompt_tokens': 100, 'completion_tokens': 20})
    result = summarize_usage({'strong': events}, rates={'strong': {'input_per_million': 1, 'output_per_million': 2}}, currency='USD')
    assert result['provider_attempts'] == 2
    assert result['known_cost_subtotal'] == pytest.approx(0.00014)
    assert result['total_cost'] is None


def test_repeated_trace_copies_do_not_double_bill():
    events = []; provider(events, usage={'input_tokens': 100, 'output_tokens': 20})
    result = summarize_usage({'first': events, 'copy': events}, rates={'strong': {'input_per_million': 1, 'output_per_million': 2}}, currency='USD')
    assert result['provider_attempts'] == 1
    assert result['total_cost'] == pytest.approx(0.00014)
    assert result['provider_input_tokens'] == 100


def test_native_context_tokens_are_not_provider_cost():
    events = [{'type': 'model_session_generation_started', 'request_id': 'native'},
              {'type': 'model_session_generation_returned', 'request_id': 'native', 'state_transport': 'native_rwkv',
               'raw_generation': {'prompt_token_ids': [0, 1, 2], 'raw_token_ids': [3, 4]}}]
    result = summarize_usage({'rwkv': events})
    assert result['logical_input_tokens_known'] == 3
    assert result['logical_output_tokens_known'] == 2
    assert result['total_cost'] is None
    assert result['remote_gpu_peak_bytes'] is None


def test_empty_output_ids_with_nonempty_answer_are_unknown():
    result = summarize_usage({'rwkv': [
        {'type': 'model_session_generation_returned', 'request_id': 'r', 'state_transport': 'native_rwkv',
         'raw_generation': {'prompt_token_ids': None, 'raw_token_ids': [], 'raw_output': 'answer'}}]})
    assert result['logical_output_tokens'] is None
    assert result['unpaired_generations'] == 1


def test_conflicting_duplicate_usage_rejected():
    left = []; provider(left, usage={'input_tokens': 1, 'output_tokens': 2})
    right = []; provider(right, usage={'input_tokens': 10, 'output_tokens': 2})
    with pytest.raises(ValueError, match='conflicting'):
        summarize_usage({'first': left, 'second': right})


@pytest.mark.parametrize('value', [-1, True, 1.5])
def test_invalid_provider_token_counts_do_not_become_cost(value):
    events = []; provider(events, usage={'input_tokens': value, 'output_tokens': 2})
    assert summarize_usage({'strong': events})['provider_input_tokens'] is None


def test_provider_started_without_attempt_is_unknown():
    result = summarize_usage({'strong': [{'type': 'supervisor_request_started', 'run_id': 'r', 'call_id': 'c', 'model': 'strong'}]})
    assert result['unresolved_provider_requests'] == 1
    assert result['total_cost'] is None


def test_unrelated_provider_call_cannot_cover_unpriced_generation():
    events = []; provider(events, usage={'input_tokens': 1, 'output_tokens': 2})
    generation = [{'type': 'model_session_generation_started', 'request_id': 'other'},
                  {'type': 'model_session_generation_returned', 'request_id': 'other', 'state_transport': 'text',
                   'raw_generation': {'prompt_token_ids': [1], 'raw_token_ids': [2]}}]
    result = summarize_usage({'provider': events, 'generation': generation},
                             rates={'strong': {'input_per_million': 1, 'output_per_million': 1}}, currency='USD')
    assert result['total_cost'] is None


def test_run_accounting_preserves_task_attribution_and_hashes(tmp_path):
    import json
    from rwkv_lh.usage_accounting import audit_run_usage
    events = []; provider(events, usage={'input_tokens': 1, 'output_tokens': 2})
    (tmp_path / 'strong_trace.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    (tmp_path / 'DELIVERY.json').write_text(json.dumps({'termination': 'submitted', 'assistance': 'strong_takeover',
        'acceptance': 'not_evaluated', 'workflow': {'end_to_end_seconds': 10}, 'elapsed_seconds': 2}))
    result = audit_run_usage(tmp_path)
    assert result['end_to_end_seconds'] == 10
    assert result['recorded_inner_elapsed_seconds'] == 2
    assert result['task_acceptance_recorded'] == 'not_evaluated'
    assert result['task_assistance'] == 'strong_takeover'
    assert len(result['trace_sha256']['strong_trace.jsonl']) == 64
