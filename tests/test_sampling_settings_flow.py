"""Configured sampling must reach actual requests and their recorded evidence."""
from dataclasses import replace

import pytest

from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION
from rwkv_lh.model_session import ModelSession, NativeRWKVModelSession, SessionSampling
from rwkv_lh.runtime.sampling import get_request_sampling
from rwkv_lh.schema import ModelLaneKind
from test_model_session import FakeNativeStateClient, QueueClient, settings
from test_unified_controller import build, call, choose

VALUES = dict(temperature=0.3, top_p=0.85, top_k=12, presence_penalty=0.1,
              frequency_penalty=0.2, penalty_decay=0.98)


def configured(original):
    return replace(original, **{'default_' + k: v for k, v in VALUES.items()})


@pytest.mark.parametrize('native', [False, True])
@pytest.mark.parametrize('explicit', [False, True])
def test_session_sampling_settings_and_explicit_override(native, explicit):
    seen = []
    class ReplayClient(QueueClient):
        def text_completion(self, *args, **kwargs):
            seen.append(vars(get_request_sampling()))
            return super().text_completion(*args, **kwargs)
    class NativeClient(FakeNativeStateClient):
        def state_generate(self, **kwargs):
            seen.append(kwargs['sampling'])
            return super().state_generate(**kwargs)
    client = (NativeClient if native else ReplayClient)(['{"function":"final_answer","params":{"text":"Done"}}'])
    events = []
    session = (NativeRWKVModelSession if native else ModelSession)(
        client, settings=configured(settings()), audit_hook=events.append)
    root = session.bootstrap(ModelLaneKind.ACTION, 'Answer briefly.', [FINAL_ANSWER_DEFINITION])
    override = SessionSampling(temperature=0.7, frequency_penalty=0.4) if explicit else None
    candidate = session.generate(root, sampling=override)
    expected = override.to_dict() if explicit else VALUES
    assert {k: seen[0][k] for k in expected} == expected
    assert candidate.sampling.to_dict() == expected
    assert candidate.raw_record()['sampling'] == expected
    assert next(e for e in events if e['type']=='model_session_generation_started')['sampling'] == expected


@pytest.mark.parametrize('progressive', [False, True])
def test_controller_uses_configured_sampling_for_selection_and_action(tmp_path, progressive):
    outputs = [call('final_answer', text='No tests were run.')]
    if progressive:
        outputs.insert(0, choose('final_answer'))
    controller, store, workspace, client, model = build(
        tmp_path, outputs, tool_disclosure_mode='progressive' if progressive else 'full')
    model.session.settings = configured(model.session.settings)
    seen = []
    original = client.text_completion
    def complete(*args, **kwargs):
        seen.append(vars(get_request_sampling()))
        return original(*args, **kwargs)
    client.text_completion = complete
    result = controller.run('RUN')
    assert result.final_output == 'No tests were run.'
    assert len(seen) == (2 if progressive else 1)
    assert all({k: item[k] for k in VALUES} == VALUES for item in seen)
    assert len(result.state.temp_decisions) == len(seen)
    assert all({k: getattr(item, k) for k in VALUES} == VALUES for item in result.state.temp_decisions)
