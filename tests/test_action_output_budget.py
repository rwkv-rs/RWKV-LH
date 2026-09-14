"""Resource configuration must reach real action generation, not choose its tool."""
from dataclasses import dataclass
import json
from pathlib import Path

from rwkv_lh.coding_agent import CodingJob, run_coding_job
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from test_unified_controller import QueueClient, call, settings


def test_configured_action_output_budget_reaches_generation_and_trace(tmp_path):
    @dataclass(frozen=True)
    class Config(RuntimeSettings):
        action_max_output_tokens: int = 4096
    configured = Config(**{**vars(settings()), 'action_max_output_tokens': 4096})
    seen = []
    class Client(QueueClient):
        def text_completion(self, prompt, max_tokens=768, stop=None):
            seen.append(max_tokens)
            return super().text_completion(prompt, max_tokens=max_tokens, stop=stop)
    def factory(**kwargs):
        return ModelSession(Client([call('write_file', path='code.py', content='print(1)\n'),
                                    call('final_answer', text='Created code.py; tests not run.')]), **kwargs)
    source = tmp_path / 'source'; source.mkdir()
    result = run_coding_job(CodingJob('budget', 'Create code.py', str(source), str(tmp_path / 'run')),
                            settings=configured, session_factory=factory)
    assert seen == [4096, 4096]
    assert result['termination'] == 'submitted'
    assert (Path(result['workspace']) / 'code.py').read_text() == 'print(1)\n'
    trace = [json.loads(x) for x in (tmp_path/'run/execution/model_trace.jsonl').read_text().splitlines()]
    started = [r for r in trace if r['type'] == 'model_session_generation_started']
    assert len(started) == 2 and all(r['max_tokens'] == 4096 for r in started)


def test_output_budget_environment_and_role_inheritance(monkeypatch):
    import os
    import rwkv_lh.runtime.settings as module
    for name in tuple(os.environ):
        if name.startswith('RWKV_'):
            monkeypatch.delenv(name)
    monkeypatch.setattr(module, 'load_local_env', lambda *args, **kwargs: None)
    monkeypatch.setenv('RWKV_LH_EXECUTOR_MODEL', 'fixture-model')
    monkeypatch.setenv('RWKV_LH_EXECUTOR_ACTION_MAX_OUTPUT_TOKENS', '8192')
    configured = RuntimeSettings.from_env()
    assert configured.action_max_output_tokens == 8192
    assert RuntimeSettings.for_role('executor', fallback=configured).action_max_output_tokens == 8192


def test_invalid_action_budget_fails_before_state_or_generation(tmp_path):
    import pytest
    from test_unified_controller import build
    controller, store, _, client, model = build(tmp_path, [])
    state = store.load('RUN')
    before = state.to_dict()
    for invalid in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match='output budget'):
            model.next_command(state, controller._persist_callback, max_output_tokens=invalid)
        assert state.to_dict() == before
    assert not client.prompts
