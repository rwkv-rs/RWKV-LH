import hashlib
import json
import pytest
from pathlib import Path
from test_unified_controller import call
from rwkv_lh import model_io


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def command_candidate(tmp_path, monkeypatch):
    import rwkv_lh.command_corrections as module
    root=tmp_path/'source';before=root/'tool_snapshots/001/before';before.mkdir(parents=True)
    (before/'a.py').write_text('value = 1\n')
    arguments={'path':'a.py','start_byte':0,'max_tokens':4096}
    original=json.dumps(call('read_file',**arguments))
    target=json.dumps(call('check_command',argv=['python3','-B','-c','from a import value; assert value == 2']))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    (before.parent/'call.json').write_text(json.dumps({'action_type':'read_file','arguments':arguments}))
    (root/'state_snapshot.json').write_text(json.dumps({'goal':{'request':'Check value'},'actions':{'A1':{'action_id':'A1','sequence':1,'request_id':'r','action_type':'read_file','arguments':arguments}}}))
    (root/'model_trace.jsonl').write_text(json.dumps({'type':'model_session_generation_returned','request_id':'r'})+'\n')
    (root/'RESULT.json').write_text(json.dumps({'tool_scope':'coding','assistance':'rwkv_independent'}))
    actual={'input_text':'visible input','input_token_ids':[0,1],'request_id':'r','input_checkpoint_id':'parent','raw_generation':{'raw_output':original}}
    monkeypatch.setattr(module,'replay_run',lambda *args:{'cp':actual})
    return dict(run_root=root,checkpoint_id='cp',target_text=target,model_sha256='a'*64,
        source_files={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},
        reviews=[{'reviewer':r,'accepted':True,'visible_evidence_only':True,'target_sha256':sha(target),'input_sha256':sha('visible input')} for r in ('one','two')],
        expected_exit_code=1,expected_output=['AssertionError'],output=tmp_path/'validation')


def test_failing_test_can_be_a_valid_next_action_without_claiming_success(command_candidate):
    from rwkv_lh.command_corrections import validate_command_correction
    result=validate_command_correction(**command_candidate)
    assert result['status']=='validated_candidate'
    assert result['tool_result']['success'] is False
    assert result['tool_result']['exit_code']==1
    assert result['training_admitted'] is False
    assert result['target_text']==command_candidate['target_text']


@pytest.mark.parametrize('problem',['missing_executable','wrong_exit','unsupported_output','wrong_review','unsealed_snapshot','wrong_request'])
def test_command_correction_rejects_unproven_progress(command_candidate,problem):
    from rwkv_lh.command_corrections import validate_command_correction
    c=command_candidate
    if problem=='missing_executable':
        c['target_text']=json.dumps(call('check_command',argv=['/not/a/program']))+model_io.JSON_CALL_STOP_SUFFIXES[0]
        for review in c['reviews']:review['target_sha256']=sha(c['target_text'])
    if problem=='wrong_exit':c['expected_exit_code']=0
    if problem=='unsupported_output':c['expected_output']=['not observed']
    if problem=='wrong_review':c['reviews'][0]['input_sha256']='b'*64
    if problem=='unsealed_snapshot':c['source_files'].pop('tool_snapshots/001/before/a.py')
    if problem=='wrong_request':
        p=c['run_root']/'state_snapshot.json';s=json.loads(p.read_text());s['actions']['A1']['request_id']='other';p.write_text(json.dumps(s));c['source_files']['state_snapshot.json']=sha(p.read_text())
    if problem in ('wrong_review','unsealed_snapshot','wrong_request'):
        with pytest.raises(ValueError):validate_command_correction(**c)
    else:
        assert validate_command_correction(**c)['status']=='verification_failed'


def test_successful_command_retains_actual_success(command_candidate):
    from rwkv_lh.command_corrections import validate_command_correction
    c=command_candidate
    c['target_text']=json.dumps(call('check_command',argv=['python3','-B','-c','print("checked")']))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    c['expected_exit_code']=0;c['expected_output']=['checked']
    for review in c['reviews']:review['target_sha256']=sha(c['target_text'])
    result=validate_command_correction(**c)
    assert result['status']=='validated_candidate' and result['tool_result']['success'] is True


def test_training_command_rejects_changed_target_and_rechecks_outcome(command_candidate,tmp_path):
    from rwkv_lh.command_corrections import validate_command_correction,revalidate_training_command
    c=command_candidate;proof=validate_command_correction(**c);p=c['output']/'VALIDATION.json'
    row={k:proof[k] for k in ('input_text','input_token_ids','input_checkpoint_id','request_id','target_text','reviews')}
    row.update(candidate_checkpoint_id='cp',command_validation={'path':str(p),'sha256':sha(p.read_text())})
    params=dict(run_root=c['run_root'],source_files=c['source_files'],model_sha256=c['model_sha256'],output=tmp_path/'fresh')
    assert revalidate_training_command(row,**params)['status']=='validated_candidate'
    row['target_text']+='changed';params['output']=tmp_path/'bad'
    with pytest.raises(ValueError,match='binding'):revalidate_training_command(row,**params)
