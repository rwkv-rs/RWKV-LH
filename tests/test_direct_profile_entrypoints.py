"""Regression: actual product dispatch must retain an explicitly selected State."""
import importlib.util
import json
from pathlib import Path
import sys
import pytest
from rwkv_lh.runtime.settings import RuntimeSettings

ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('entry',['batch','coding','read','web'])
@pytest.mark.parametrize('configured',[False,True])
def test_product_entrypoint_preserves_selected_profile(entry,configured,tmp_path,monkeypatch):
    expected=('candidate','a'*64) if configured else ('zero','0'*64)
    settings=RuntimeSettings(base_url='http://localhost:8000/v1',api_key='',model='model',state_profile_id=expected[0] if configured else '',state_profile_sha256=expected[1] if configured else '')
    captured=[]
    if entry=='web':
        from rwkv_lh import web_worker
        import rwkv_lh.runtime.settings as configuration
        monkeypatch.setattr(configuration,'get_runtime_settings',lambda:settings)
        captured.append(web_worker.direct_settings())
    else:
        name={'batch':'run_rwkv_agent','coding':'run_rwkv_coding_agent','read':'run_rwkv_read_only_agent'}[entry]
        spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        monkeypatch.setattr(module,'get_runtime_settings',lambda:settings);monkeypatch.setattr(module,'load_local_env',lambda *a,**k:None)
        def dispatch(job,*,settings,**kwargs):
            captured.append(settings)
            result={'termination':'submitted'}
            return result if entry=='coding' else [result]
        monkeypatch.setattr(module,{'batch':'run_agent_jobs','coding':'run_coding_job','read':'run_read_only_jobs'}[entry],dispatch)
        if entry=='coding':argv=[name,'--source-workspace',str(tmp_path/'source'),'--output-dir',str(tmp_path/'out'),'--request','Read the source']
        else:
            path=tmp_path/'jobs.json';path.write_text(json.dumps([{'task_id':'example','request':'Read the source','workspace':str(tmp_path/'source'),'output_dir':str(tmp_path/'out')}]))
            argv=[name,'--jobs',str(path)]
        monkeypatch.setattr(sys,'argv',argv);assert module.main()==0
    assert len(captured)==1
    actual=captured[0]
    assert (actual.state_profile_id,actual.state_profile_sha256)==expected
    assert actual.return_token_ids and actual.state_transport=='native_required'

@pytest.mark.parametrize('profile_id,profile_sha', [('candidate', ''), ('', 'a'*64), ('candidate', 'bad')])
def test_direct_settings_rejects_incomplete_identity(profile_id, profile_sha):
    from rwkv_lh.runtime.settings import direct_agent_settings
    with pytest.raises(ValueError):
        direct_agent_settings(RuntimeSettings(base_url='http://localhost:8000/v1', api_key='', model='model',
            state_profile_id=profile_id, state_profile_sha256=profile_sha))


def test_direct_settings_preserves_attested_profile_and_model():
    from rwkv_lh.runtime.settings import direct_agent_settings
    selected = RuntimeSettings(base_url='http://localhost:8000/v1', api_key='', model='selected-model',
        state_profile_id='candidate', state_profile_sha256='a'*64, state_profile_delivery='process_attested')
    actual = direct_agent_settings(selected)
    assert actual.state_profile_delivery == 'process_attested'
    assert actual.model == 'selected-model'
    assert actual.state_profile_id == selected.state_profile_id
    assert actual.state_profile_sha256 == selected.state_profile_sha256
    assert selected.return_token_ids == RuntimeSettings.__dataclass_fields__['return_token_ids'].default
