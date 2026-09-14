import hashlib,json
from pathlib import Path
import pytest
from test_unified_controller import call
from rwkv_lh import model_io
from rwkv_lh.workspace_snapshot import tree_identity
from rwkv_lh.coding_corrections import tree_sha256


def test_snapshot_is_saved_before_the_real_generation_event(tmp_path):
    from rwkv_lh.correction_snapshots import generation_snapshot_audit
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'a.py').write_text('value = 1\n')
    output=tmp_path/'evidence';events=[]
    audit=generation_snapshot_audit(workspace=workspace,output=output,audit_hook=events.append)
    event={'type':'model_session_generation_started','request_id':'r','input_checkpoint_id':'parent','input_digest':'d'*64}
    audit(event)
    assert [e['type'] for e in events]==['correction_generation_snapshot_saved','model_session_generation_started']
    assert (output/'generation_snapshots/r/before/a.py').read_text()=='value = 1\n'
    assert events[-1]==event
    with pytest.raises(FileExistsError):audit(event)
    assert len(events)==2


def test_unrelated_audit_events_do_not_snapshot(tmp_path):
    from rwkv_lh.correction_snapshots import generation_snapshot_audit
    events=[];audit=generation_snapshot_audit(workspace=tmp_path,output=tmp_path/'output',audit_hook=events.append)
    audit({'type':'native_request_prepared','request_id':'r'})
    assert events==[{'type':'native_request_prepared','request_id':'r'}]
    assert not (tmp_path/'output').exists()


@pytest.fixture
def generation_candidate(tmp_path,monkeypatch):
    import rwkv_lh.coding_corrections as module
    root=tmp_path/'source';before=root/'generation_snapshots/r/before';before.mkdir(parents=True)
    (before/'a.py').write_text('value = 1\n')
    original=json.dumps(call('run_command',shell=True))
    target=json.dumps(call('write_file',path='a.py',content='value = 2\n'))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    identity={'schema_version':'rwkv-lh.correction-generation-snapshot.v1','request_id':'r','input_checkpoint_id':'parent','input_digest':'d'*64,'tree_sha256':tree_sha256(tree_identity(before))}
    (before.parent/'SNAPSHOT.json').write_text(json.dumps(identity))
    events=[{'type':'correction_generation_snapshot_saved',**identity},{'type':'model_session_generation_started','request_id':'r','input_checkpoint_id':'parent','input_digest':'d'*64},{'type':'model_session_generation_returned','request_id':'r'}]
    (root/'model_trace.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    (root/'state_snapshot.json').write_text('{}');(root/'RESULT.json').write_text(json.dumps({'tool_scope':'coding','assistance':'rwkv_independent'}))
    actual={'input_text':'visible input','input_token_ids':[0,1],'request_id':'r','input_checkpoint_id':'parent','raw_generation':{'raw_output':original}}
    monkeypatch.setattr(module,'replay_run',lambda *args:{'cp':actual})
    sha=lambda s:hashlib.sha256(s.encode()).hexdigest()
    return dict(run_root=root,checkpoint_id='cp',target_text=target,model_sha256='a'*64,
       source_files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},snapshot='generation_snapshots/r/before',snapshot_sha256=identity['tree_sha256'],
       checks=[['python3','-B','-c','from a import value; assert value == 2']],reviews=[{'reviewer':r,'accepted':True,'visible_evidence_only':True,'input_sha256':sha('visible input'),'target_sha256':sha(target)} for r in ('one','two')],output=tmp_path/'validation')


def test_real_generation_boundary_allows_correction_of_illegal_original(generation_candidate):
    from rwkv_lh.coding_corrections import validate_coding_correction
    result=validate_coding_correction(**generation_candidate)
    assert result['status']=='validated_candidate'
    assert result['before_checks'][0]['exit_code']==1
    assert result['after_checks'][0]['exit_code']==0
    assert result['original_output']==json.dumps(call('run_command',shell=True))


@pytest.mark.parametrize('fault',['future','parent','request','unsealed','contents'])
def test_generation_snapshot_rejects_wrong_boundary(generation_candidate,fault):
    from rwkv_lh.coding_corrections import validate_coding_correction
    c=generation_candidate;root=c['run_root'];path=root/'model_trace.jsonl';events=[json.loads(l) for l in path.read_text().splitlines()]
    if fault=='future':events[0],events[1]=events[1],events[0]
    if fault=='parent':events[1]['input_checkpoint_id']='future-parent'
    if fault=='request':events[1]['request_id']='other'
    if fault in ('future','parent','request'):
        path.write_text(''.join(json.dumps(e)+'\n' for e in events));c['source_files']['model_trace.jsonl']=hashlib.sha256(path.read_bytes()).hexdigest()
    if fault=='unsealed':c['source_files'].pop('generation_snapshots/r/SNAPSHOT.json')
    if fault=='contents':
        p=root/c['snapshot']/'a.py';p.write_text('future = 2\n');c['source_files'][str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    with pytest.raises(ValueError):validate_coding_correction(**c)
    assert not c['output'].exists()


def test_command_correction_can_use_a_generation_with_no_executed_action(generation_candidate,monkeypatch):
    from rwkv_lh.command_corrections import validate_command_correction
    import rwkv_lh.command_corrections as commands
    import rwkv_lh.coding_corrections as coding
    c=generation_candidate
    monkeypatch.setattr(commands,'replay_run',coding.replay_run)
    path=c['run_root']/'state_snapshot.json';path.write_text(json.dumps({'goal':{'request':'Check the value'}}))
    c['source_files']['state_snapshot.json']=hashlib.sha256(path.read_bytes()).hexdigest()
    target=json.dumps(call('check_command',argv=['python3','-B','-c','from a import value; assert value == 2']))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    reviews=[{**review,'target_sha256':hashlib.sha256(target.encode()).hexdigest()} for review in c['reviews']]
    result=validate_command_correction(**{key:c[key] for key in ('run_root','checkpoint_id','model_sha256','source_files','output')},target_text=target,reviews=reviews,expected_exit_code=1,expected_output=['AssertionError'])
    assert result['status']=='validated_candidate' and result['tool_result']['exit_code']==1
    assert result['source_action_id'] is None
