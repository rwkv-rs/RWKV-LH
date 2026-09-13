"""Production append must end an unused generation opener before a new turn."""
import re
import pytest
from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION, ModelCommand, canonical_json
from rwkv_lh.model_session import ModelSession, NativeRWKVModelSession
from rwkv_lh.schema import ModelEvent, ModelLaneKind
from test_model_session import FakeNativeStateClient, QueueClient, settings

BAD_BOUNDARY = re.compile(r'(?:Assistant:|\*\*Tool Call:\*\*)\s*```json\n\s*\nUser:')


def session_pair(native, outputs):
    client = FakeNativeStateClient(outputs) if native else QueueClient(outputs)
    session = (NativeRWKVModelSession if native else ModelSession)(client, settings=settings())
    return session, client


def actual_text(native, client, checkpoint):
    return client.states[checkpoint.native_state_ref] if native else checkpoint.transcript


@pytest.mark.parametrize('native', [False, True])
@pytest.mark.parametrize('native_anchor', [False, True])
def test_rollback_feedback_closes_unused_prefix_without_inventing_answer(native, native_anchor):
    session, client = session_pair(native, ['incomplete JSON'])
    root = session.bootstrap(ModelLaneKind.ACTION, 'Inspect the file.', [FINAL_ANSWER_DEFINITION], native_tool_call_json=native_anchor)
    original = actual_text(native, client, root)
    candidate = session.generate(root, max_output_tokens=100)
    restored = session.rollback(candidate, error='invalid JSON')
    event = ModelEvent('protocol_rejection', 'E1', root.lane_id, {'error': 'invalid JSON', 'action_executed': False})
    child = session.append(restored, event)
    text = actual_text(native, client, child)
    assert BAD_BOUNDARY.search(text) is None
    assert text.startswith(original + '\n```\n')
    assert 'incomplete JSON' not in text
    assert canonical_json(event.to_model_dict()) in text
    assert child.event_ids == ['E1']
    assert child.parent_checkpoint_id == restored.checkpoint_id
    assert actual_text(native, client, root) == original


@pytest.mark.parametrize('native', [False, True])
def test_committed_response_does_not_gain_an_extra_closing_fence(native):
    output = '```json\n' + ModelCommand('final_answer', {'text': 'original'}).canonical + '\n```'
    session, client = session_pair(native, [output])
    root = session.bootstrap(ModelLaneKind.ACTION, 'Inspect.', [FINAL_ANSWER_DEFINITION])
    candidate = session.generate(root, max_output_tokens=100)
    parent = session.commit(candidate, session.parse(candidate))
    before = actual_text(native, client, parent)
    event = ModelEvent('protocol_rejection', 'E1', root.lane_id, {'error': 'external rejection after commit'})
    child = session.append(parent, event)
    assert actual_text(native, client, child)[len(before):].startswith('\n\nUser:')


@pytest.mark.parametrize('native', [False, True])
def test_multiple_events_and_fork_keep_turn_boundaries_closed(native):
    session, client = session_pair(native, [])
    root = session.bootstrap(ModelLaneKind.ACTION, 'Inspect.', [FINAL_ANSWER_DEFINITION])
    first = session.append(root, ModelEvent('action_result', 'E1', root.lane_id, {'output': 'one'}))
    second = session.append(first, ModelEvent('action_result', 'E2', root.lane_id, {'output': 'two'}))
    fork = session.fork(second, ModelLaneKind.ACTION, ModelEvent('action_result', 'E3', root.lane_id, {'output': 'three'}))
    assert BAD_BOUNDARY.search(actual_text(native, client, fork)) is None
    assert fork.event_ids == ['E1', 'E2', 'E3']


@pytest.mark.parametrize('native', [False, True])
def test_rollover_summary_does_not_follow_an_unclosed_bootstrap(native):
    session, client = session_pair(native, [])
    root = session.bootstrap(ModelLaneKind.ACTION, 'Inspect.', [FINAL_ANSWER_DEFINITION])
    event = ModelEvent('protocol_rejection', 'E1', root.lane_id, {'error': 'invalid call'})
    rolled = session.rollover(root, assignment='Inspect.', visible_definitions=[FINAL_ANSWER_DEFINITION], events=[event], input_limit=10000, rollover_id='R1')
    assert BAD_BOUNDARY.search(actual_text(native, client, rolled)) is None
    assert rolled.event_ids == ['E1']


def test_native_append_budget_includes_the_new_framing_tokens():
    from dataclasses import replace
    from rwkv_lh.model_io import render_event_append
    from rwkv_lh.model_session import InputBudgetError
    from rwkv_lh.token_budget import get_token_count
    session, client = session_pair(True, [])
    root = session.bootstrap(ModelLaneKind.ACTION, 'Inspect.', [FINAL_ANSWER_DEFINITION])
    event = ModelEvent('protocol_rejection', 'E1', root.lane_id, {'error': 'invalid ' * 100})
    suffix = render_event_append(event, previous_transcript=root.transcript)
    plain_size = get_token_count(render_event_append(event))
    actual_size = get_token_count(suffix)
    assert actual_size > plain_size
    budget = actual_size - 1
    session.settings = replace(session.settings, max_model_len=budget + session.settings.context_safety_margin + session.settings.bos_token_count + 1)
    with pytest.raises(InputBudgetError):
        session.append(root, event)
    assert [name for name, _ in client.calls] == ['create']
