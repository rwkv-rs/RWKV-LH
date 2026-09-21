import pytest
from rwkv_lh.runtime import settings as runtime


def test_explicit_model_is_applied_before_validation(monkeypatch):
    monkeypatch.setattr(runtime, 'load_local_env', lambda *a, **k: None)
    monkeypatch.setenv('RWKV_LH_EXECUTOR_MODEL', '')
    monkeypatch.setenv('RWKV_MODEL', '')
    configured = runtime.RuntimeSettings.from_env(overrides={'model': 'explicit-model'})
    assert configured.model == 'explicit-model'
    with pytest.raises(ValueError, match='MODEL'):
        runtime.RuntimeSettings.from_env()


def test_invalid_override_still_validated(monkeypatch):
    monkeypatch.setattr(runtime, 'load_local_env', lambda *a, **k: None)
    with pytest.raises(ValueError, match='HTTP'):
        runtime.RuntimeSettings.from_env(overrides={'model': 'model', 'base_url': 'invalid'})


def test_unified_single_entry_accepts_explicit_model(tmp_path, monkeypatch):
    import scripts.run_rwkv_agent as cli
    monkeypatch.setattr(runtime, 'load_local_env', lambda *a, **k: None)
    monkeypatch.setattr(cli, 'load_local_env', lambda *a, **k: None)
    monkeypatch.setenv('RWKV_LH_EXECUTOR_MODEL', '')
    monkeypatch.setenv('RWKV_MODEL', '')
    seen = []
    def execute(jobs, **kwargs):
        seen.append((jobs, kwargs['settings']))
        return [{'termination': 'submitted'}]
    monkeypatch.setattr(cli, 'run_agent_jobs', execute)
    assert cli.main(['--source-workspace', str(tmp_path), '--request', 'Inspect code',
                     '--output-dir', str(tmp_path / 'out'), '--model', 'explicit-model']) == 0
    assert seen[0][1].model == 'explicit-model'
    assert len(seen[0][0]) == 1


def test_empty_batch_does_not_report_success(tmp_path):
    from scripts.run_rwkv_agent import main
    jobs = tmp_path / 'jobs.json'
    jobs.write_text('[]')
    with pytest.raises(SystemExit) as error:
        main(['--jobs', str(jobs)])
    assert error.value.code == 2
