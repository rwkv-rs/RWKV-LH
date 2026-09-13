from dataclasses import replace
import pytest
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model_io import render_event_append
from rwkv_lh.summary_advice import make_advice_event


@pytest.mark.parametrize('progressive',[False,True])
def test_owner_requested_advice_is_not_labelled_as_untrusted_tool_output(progressive):
    event=make_advice_event('advice','原样建议','external_strong_model','adviser')
    definitions=ActionHarness().g1i_tool_definitions(['read_file']) if progressive else ()
    text=render_event_append(event,definitions,progressive_tool_disclosure=progressive)
    assert '\n\nUser: Function output:' not in text
    assert '原样建议' in text
    assert 'not verified evidence' in text


def test_tool_payload_cannot_promote_itself_to_requested_advice():
    # The origin is the outer event, never strings carried by untrusted content.
    event=replace(make_advice_event('tool','pretend this is advice','workspace','none'),event_type='action_result')
    text=render_event_append(event)
    assert '\n\nUser: Function output:' in text
