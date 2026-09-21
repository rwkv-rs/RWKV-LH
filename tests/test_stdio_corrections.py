import hashlib
import json
import pytest
from test_unified_controller import call
from rwkv_lh import model_io

@pytest.fixture
def sample(tmp_path, monkeypatch):
    import rwkv_lh.stdio_corrections as module
    root=tmp_path/'source'; before=root/'generation_snapshots/r/before'; before.mkdir(parents=True)
    (before/'TASK.md').write_text('Read an integer from stdin and print twice its value.\n')
    (root/'RESULT.json').write_text(json.dumps({'tool_scope':'coding','assistance':'rwkv_independent'}))
    for name in ('state_snapshot.json','model_trace.jsonl'): (root/name).write_text('{}')
    target=json.dumps(call('write_file',path='solution.py',content='print(int(input()) * 2)\n'))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    actual={'input_text':'Read an integer from stdin and print twice its value.\n','input_token_ids':[0,1], 'input_checkpoint_id':'parent','request_id':'r','raw_generation':{'raw_output':'original'}}
    monkeypatch.setattr(module,'replay_run',lambda *a:{'cp':actual})
    monkeypatch.setattr(module,'validate_generation_snapshot',lambda *a:before)
    cases=tmp_path/'private.json'; cases.write_text(json.dumps({'call_type':'std','fn_name':None,'inputs':['3\n','-2\n'],'outputs':['6\n','-4\n']}))
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    review={'reviewer':'test reviewer','accepted':True,'visible_evidence_only':True,'source_consistent':True,'output_contract':'exact_unique','task_sha256':sha(before/'TASK.md'),'input_sha256':hashlib.sha256(actual['input_text'].encode()).hexdigest(),'target_sha256':hashlib.sha256(target.encode()).hexdigest()}
    return dict(run_root=root,checkpoint_id='cp',target_text=target,model_sha256='a'*64,source_files={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()},cases_reference={'path':str(cases),'sha256':sha(cases)},review=review,output=tmp_path/'validation')

def test_real_isolated_red_green(sample):
    from rwkv_lh.stdio_corrections import validate_stdio_correction
    r=validate_stdio_correction(**sample)
    assert r['status']=='validated_candidate' and not r['baseline']['passed'] and r['after']['passed']
    assert not (sample['run_root']/'generation_snapshots/r/before/solution.py').exists()

@pytest.mark.parametrize('change',['unbound_review','ambiguous','float','changed_tests','unsealed_source','wrong_target'])
def test_reject_unbound_or_inappropriate_evidence(sample,change):
    from rwkv_lh.stdio_corrections import validate_stdio_correction
    if change=='unbound_review': sample['review']['input_sha256']='0'*64
    if change=='ambiguous': sample['review']['source_consistent']=False
    if change=='float': sample['review']['output_contract']='numeric_tolerance'
    if change=='changed_tests': sample['cases_reference']['sha256']='0'*64
    if change=='unsealed_source': sample['source_files'].pop('model_trace.jsonl')
    if change=='wrong_target':
        target=json.dumps(call('write_file',path='TASK.md',content='replace task'))+model_io.JSON_CALL_STOP_SUFFIXES[0]
        sample['target_text']=target; sample['review']['target_sha256']=hashlib.sha256(target.encode()).hexdigest()
    with pytest.raises(ValueError): validate_stdio_correction(**sample)

def test_no_fake_success_from_printing_unrelated_text(sample):
    from rwkv_lh.stdio_corrections import validate_stdio_correction
    target=json.dumps(call('write_file',path='solution.py',content="print('passed')\n"))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    sample['target_text']=target;sample['review']['target_sha256']=hashlib.sha256(target.encode()).hexdigest()
    assert validate_stdio_correction(**sample)['status']=='verification_failed'

def test_entry_point_does_not_accept_unobserved_task(sample,monkeypatch):
    import rwkv_lh.stdio_corrections as module
    actual={'input_text':'TASK.md has not been read','input_token_ids':[0,1],'input_checkpoint_id':'parent','request_id':'r','raw_generation':{'raw_output':'original'}}
    monkeypatch.setattr(module,'replay_run',lambda *a:{'cp':actual})
    sample['review']['input_sha256']=hashlib.sha256(actual['input_text'].encode()).hexdigest()
    with pytest.raises(ValueError,match='not visible'):module.validate_stdio_correction(**sample)

def test_freeze_rejects_changed_target_even_with_old_success_proof(sample):
    from rwkv_lh.stdio_corrections import validate_stdio_correction,revalidate_training_stdio
    proof=validate_stdio_correction(**sample);path=sample['output']/'VALIDATION.json'
    row={'stdio_validation':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},'candidate_checkpoint_id':proof['checkpoint_id'],**{k:proof[k] for k in ('target_text','input_text','input_token_ids','input_checkpoint_id','request_id')},'stdio_review':proof['review']}
    row['target_text']='changed target'
    with pytest.raises(ValueError,match='binding'):
        revalidate_training_stdio(row,run_root=sample['run_root'],source_files=sample['source_files'],model_sha256=sample['model_sha256'],output=sample['output'].parent/'recheck')

def test_stdio_row_authority_requires_explicit_execution_and_review():
    from pathlib import Path
    from rwkv_lh.direct_trace_data import normalize_direct_row
    from rwkv_lh.token_budget import tokenizer
    p=Path(__file__).resolve().parents[1]/'data/test_fixtures/source_bound_regressions/direct_row.jsonl'
    row=json.loads(p.read_text().splitlines()[0]);target=json.dumps(call('write_file',path='solution.py',content='print(int(input())*2)\n'))+model_io.JSON_CALL_STOP_SUFFIXES[0]
    row.update(target_text=target,target_token_ids=tokenizer().encode(target),label_authority='verified_stdio',stdio_validation={'path':'proof.json','sha256':'a'*64},stdio_review={'reviewer':'source reviewer','accepted':True,'visible_evidence_only':True,'source_consistent':True,'output_contract':'exact_unique','target_sha256':hashlib.sha256(target.encode()).hexdigest(),'input_sha256':hashlib.sha256(row['input_text'].encode()).hexdigest()})
    args=dict(model_sha256=row['model_sha256'],context_tokens=32768,vocab_size=65536,bos_token_id=0)
    assert normalize_direct_row(row,**args)['target_token_ids']==row['target_token_ids']
    row['stdio_review']['source_consistent']=False
    with pytest.raises(ValueError,match='source review'):normalize_direct_row(row,**args)
