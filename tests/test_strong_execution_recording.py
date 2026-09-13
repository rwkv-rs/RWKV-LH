import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import pytest
from rwkv_lh import task_review as review
from rwkv_lh.read_only_agent import ReadOnlyJob, _run_job
from rwkv_lh.coding_agent import _RecordedHarness
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.model_session import ModelSession
from test_unified_controller import call, settings


@pytest.fixture
def execution(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    output = tmp_path / 'execution'
    raw = json.dumps(call('final_answer', text='Unchanged strong answer.'))
    response = SimpleNamespace(content=raw, finish_reason='stop', response_id='vendor-1',
                               model='strong-test', metadata={})
    client = SimpleNamespace(model_name='strong-test', text_completion=lambda *a, **k: response)
    factory = lambda **kw: ModelSession(client, **kw)
    result = _run_job(ReadOnlyJob('strong', 'Answer', str(workspace), str(output)),
        settings=replace(settings(), model='strong-test'), session_factory=factory,
        harness_factory=lambda: _RecordedHarness(output), controller_type=LongHorizonController,
        allowed_scopes=('files',), execution_authority='strong_takeover')
    envelope = {'type': 'supervisor_response_envelope_received', 'raw_response': {
        'id': 'vendor-1', 'model': 'strong-test',
        'choices': [{'message': {'content': raw}, 'finish_reason': 'stop'}],
        'usage': {'prompt_tokens': 123, 'completion_tokens': 45, 'total_tokens': 168}}}
    return output, result, envelope


def capture(output, trace=None):
    return review.capture_diagnostic_run(output, task_id='strong', arm='takeover', repeat=1,
        protocol_error_policy='feedback', execution_identity={k: review.digest(k) for k in review.IDENTITY_KEYS},
        historical=False, assistance='strong_takeover', provider_trace=trace)


def test_final_causal_source_tracks_strong_execution_authority(execution):
    output, result, _ = execution
    state = json.loads((output / 'state_snapshot.json').read_text())
    completed = [e for e in state['causal_records'].values() if e['event_type'] == 'run_completed']
    assert completed[-1]['payload']['output_source'] == 'strong_explicit_final_answer_text'
    assert result['final'] == 'Unchanged strong answer.'


def test_bound_vendor_usage_is_not_zero_when_exact_ids_are_unavailable(execution):
    output, _, envelope = execution
    path = output / 'provider.jsonl'
    path.write_text(json.dumps(envelope) + '\n')
    result = capture(output, path)
    assert result['diagnostics']['input_tokens'] == 123
    assert result['diagnostics']['output_tokens'] == 45
    assert result['diagnostics']['provider_usage_calls'] == 1
    assert result['answer'] == 'Unchanged strong answer.'
    assert any(e['path'] == 'provider.jsonl' for e in result['evidence'])


@pytest.mark.parametrize('corruption', ['missing', 'id', 'model', 'content', 'count', 'duplicate'])
def test_unknown_or_unbound_vendor_usage_is_rejected(execution, corruption):
    output, _, original = execution
    envelope = deepcopy(original)
    if corruption == 'missing':
        with pytest.raises(ValueError, match='token usage'): capture(output)
        return
    response = envelope['raw_response']
    if corruption == 'id': response['id'] = 'unrelated'
    if corruption == 'model': response['model'] = 'unrelated'
    if corruption == 'content': response['choices'][0]['message']['content'] = 'rewritten'
    if corruption == 'count': response['usage']['prompt_tokens'] = -1
    path = output / 'provider.jsonl'
    path.write_text((json.dumps(envelope) + '\n') * (2 if corruption == 'duplicate' else 1))
    with pytest.raises(ValueError): capture(output, path)


def test_completion_authority_cannot_be_inferred_from_a_source_label():
    from rwkv_lh.run_lifecycle import model_voluntary_completion
    payload = {'decision_id': 'D1', 'output_source': 'strong_explicit_final_answer_text'}
    assert not model_voluntary_completion(payload)
    assert model_voluntary_completion(payload, execution_authority='strong_takeover')
    assert not model_voluntary_completion(payload, execution_authority='unknown')
    assert not model_voluntary_completion({'decision_id': 'D1', 'output_source': 'rwkv_explicit_final_answer_text'},
                                           execution_authority='strong_takeover')


@pytest.mark.parametrize('matching_input', [True, False])
def test_provider_without_id_requires_exact_recorded_input(execution, matching_input):
    output, _, envelope = execution
    del envelope['raw_response']['id']
    envelope['call_id'] = 'local-receipt-1'
    state = json.loads((output / 'state_snapshot.json').read_text())
    events = [json.loads(line) for line in (output / 'model_trace.jsonl').read_text().splitlines()]
    for event in events:
        if event['type'] == 'model_session_generation_returned':
            event['raw_generation']['response_id'] = ''
    (output / 'model_trace.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
    start = next(e for e in events if e['type'] == 'model_session_generation_started')
    prompt = state['model_states'][start['input_checkpoint_id']]['transcript']
    wire = {'type': 'strong_execution_wire_request', 'call_id': 'local-receipt-1',
            'body': {'messages': [{'role': 'system', 'content': prompt if matching_input else 'unrelated'}]}}
    path = output / 'provider.jsonl'
    path.write_text(json.dumps(wire) + '\n' + json.dumps(envelope) + '\n')
    if matching_input:
        result = capture(output, path)
        assert result['diagnostics']['provider_input_bound_calls'] == 1
        assert result['diagnostics']['output_tokens'] == 45
    else:
        with pytest.raises(ValueError): capture(output, path)
