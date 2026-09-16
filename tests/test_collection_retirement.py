import json
from types import SimpleNamespace
import pytest
from rwkv_lh import collection_retirement as retirement


def test_refuse_unsealed_or_changed_evidence_before_any_release(tmp_path,monkeypatch):
    monkeypatch.setattr(retirement,"service_fingerprint",lambda settings:{})
    root=tmp_path/'run';root.mkdir()
    (root/'state_snapshot.json').write_text('{}')
    evidence=tmp_path/'sealed';evidence.mkdir()
    (evidence/'MANIFEST.json').write_text(json.dumps({'run_root':str(root),'source_files':{'state_snapshot.json':'wrong'},'boundaries_sha256':'wrong'}))
    with pytest.raises(ValueError,match='evidence'):
        retirement.release_sealed_run(root,evidence,SimpleNamespace(settings=None),expected_service={})


def test_live_run_cannot_be_retired(tmp_path):
    root=tmp_path/'run';root.mkdir()
    (root/'state_snapshot.json').write_text(json.dumps({'status':'running','model_states':{}}))
    with pytest.raises(ValueError,match='active'):
        retirement.seal_run(root,tmp_path/'sealed','a'*64)


def sealed_fixture(tmp_path):
    root=tmp_path/'run';root.mkdir()
    evidence=tmp_path/'sealed';evidence.mkdir()
    service={'model':'test','server_build':'build','tokenizer_build':'token','max_model_len':100}
    identity={'state_ref':'WKV-'+'a'*32,'state_digest':'b'*64,'cache_binding_digest':'c'*64}
    state={'run_id':'one','status':'interrupted','model_states':{'one':{'status':'committed','native_state_export':{**service,**identity}}}}
    (root/'state_snapshot.json').write_text(json.dumps(state))
    (root/'RESULT.json').write_text(json.dumps({'id':'one','status':'interrupted','termination':'budget','trace_complete':True}))
    (evidence/'boundaries.jsonl').write_text('')
    (evidence/'MANIFEST.json').write_text(json.dumps({'run_root':str(root),'source_files':retirement.tree(root),'boundaries_sha256':retirement.digest(evidence/'boundaries.jsonl')}))
    return root,evidence,service,identity


def test_release_is_explicit_idempotent_and_original_evidence_unchanged(tmp_path,monkeypatch):
    root,evidence,service,identity=sealed_fixture(tmp_path)
    before=retirement.tree(root);calls=[]
    monkeypatch.setattr(retirement,'service_fingerprint',lambda settings:service)
    def release(**kwargs):
        assert (evidence/'RETIREMENT_PLAN.json').exists()
        calls.append(kwargs)
        return {'released_state_refs':[identity['state_ref']]}
    client=SimpleNamespace(settings=None,state_release=release)
    first=retirement.release_sealed_run(root,evidence,client,expected_service=service)
    assert retirement.release_sealed_run(root,evidence,client,expected_service=service)==first
    assert calls[0]=={'states':[identity],'release_import_aliases':True}
    assert retirement.tree(root)==before


def test_different_server_refused_before_mutation(tmp_path,monkeypatch):
    root,evidence,service,identity=sealed_fixture(tmp_path)
    monkeypatch.setattr(retirement,'service_fingerprint',lambda settings:{**service,'server_build':'new'})
    with pytest.raises(ValueError,match='service identity'):
        retirement.release_sealed_run(root,evidence,SimpleNamespace(settings=None),expected_service=service)
    assert not (evidence/'RETIREMENT_PLAN.json').exists()


def test_uncertain_release_retains_plan_and_does_not_claim_success(tmp_path,monkeypatch):
    root,evidence,service,identity=sealed_fixture(tmp_path)
    monkeypatch.setattr(retirement,'service_fingerprint',lambda settings:service)
    def release(**kwargs):raise TimeoutError('unknown')
    with pytest.raises(TimeoutError):
        retirement.release_sealed_run(root,evidence,SimpleNamespace(settings=None,state_release=release),expected_service=service)
    assert (evidence/'RETIREMENT_PLAN.json').exists()
    assert not (evidence/'RETIREMENT_RESULT.json').exists()
    assert (root/'state_snapshot.json').exists()


def test_budget_stop_is_terminal_execution_even_with_resumable_state(tmp_path):
    root=tmp_path/'run';root.mkdir()
    (root/'state_snapshot.json').write_text(json.dumps({'run_id':'one','status':'running','model_states':{}}))
    (root/'RESULT.json').write_text(json.dumps({'id':'one','status':'interrupted','termination':'budget','trace_complete':True}))
    assert retirement.require_terminal(root)['run_id']=='one'


def test_bulk_retirement_uses_one_server_operation(tmp_path,monkeypatch):
    a=tmp_path/'a';a.mkdir();b=tmp_path/'b';b.mkdir()
    root,ev,service,identity=sealed_fixture(a)
    root2,ev2,_,_=sealed_fixture(b)
    calls=[]
    monkeypatch.setattr(retirement,'service_fingerprint',lambda settings:service)
    def release(**kwargs):
        calls.append(kwargs)
        return {'released_state_refs':[identity['state_ref']]}
    retirement.release_sealed_runs([(root,ev),(root2,ev2)],SimpleNamespace(settings=None,state_release=release),expected_service=service)
    assert len(calls)==1 and calls[0]['states']==[identity]
    assert (ev/'RETIREMENT_RESULT.json').exists() and (ev2/'RETIREMENT_RESULT.json').exists()


def test_campaign_lock_prevents_retirement_during_dispatch(tmp_path,monkeypatch):
    import fcntl
    from scripts import retire_collection_states
    with (tmp_path/'campaign.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        monkeypatch.setattr('sys.argv',['retire','--campaign',str(tmp_path),'--evidence',str(tmp_path/'evidence'),'--env-file',str(tmp_path/'env'),'--expected-tasks','1'])
        with pytest.raises(BlockingIOError):retire_collection_states.main()
