"""Opaque artifact integration checks; never production scenarios or training data."""
import importlib
import json
from pathlib import Path

import pytest
from test_statetune_data import row, write, _mock_extract
from rwkv_lh import statetune_data as data
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace
from rwkv_lh.role_trace_artifacts import REQUIRED_COVERAGE, build_artifacts, split_project_family, write_artifacts


def rows():
    families = {}
    for i in range(200):
        family = f"opaque-mechanism-family-{i}"
        families.setdefault(split_project_family(family), family)
    result = []
    for i, split in enumerate(['train', 'train', 'dev', 'confirmation']):
        r = row()
        r.update(sample_id=f'opaque-{i}', project_family=families[split], split=split,
                 input_text=('A' if split=='train' else 'B' if split=='dev' else 'C') * 100,
                 coverage={flag: True for flag in REQUIRED_COVERAGE})
        r['coverage']['execute'] = i == 1
        result.append(r)
    return result


def fixture(tmp_path, monkeypatch):
    source = write(tmp_path/'source.json', {'unit_test_only': True})
    samples = rows()
    provenance = {'source_registration_sha256': source['sha256'], 'requested_roles': ['selector_intent']}
    bundle = build_artifacts(samples, provenance=provenance)
    candidate = bundle.manifest
    assert candidate['status'] == 'valid'
    policy = write(tmp_path/'policy.json', {'unit_test_only': True})
    selected = write(tmp_path/'selection.json', {'schema_version': data.SELECTION_SCHEMA,
        'role': 'selector_intent', 'kept_sample_ids': ['opaque-0','opaque-2','opaque-3'],
        'counts': {'train':1,'dev':1,'confirmation':1}, 'policy_evidence_refs':[policy]})
    reg = {'schema_version':data.FREEZE_SCHEMA,'role':'selector_intent','authorization':policy,
        'candidate_manifest':write(tmp_path/'candidate.json',candidate),'source_registration':source,
        'row_selection':selected,'minimum_counts':{'train':1,'dev':1,'confirmation':1},
        'regression_fingerprint':candidate['regression_fingerprint']}
    _mock_extract(monkeypatch,tmp_path,candidate,samples,{})
    return reg,samples,bundle


def test_filter_cannot_hide_loss_of_only_execute_row(tmp_path,monkeypatch):
    reg,_,_=fixture(tmp_path,monkeypatch)
    with pytest.raises(ValueError,match='selected.*quality|selection.*coverage'):
        data.freeze_dataset(reg,registration_reference=write(tmp_path/'freeze.json',reg),
            output=tmp_path/'data/datasets/must-not-publish')
    assert not (tmp_path/'data/datasets/must-not-publish').exists()


def test_selected_source_path_reaudits_before_valid_candidate_publication(tmp_path,monkeypatch):
    # The integration entrypoint must exist independently of the freezer so a
    # raw pool that fails similarity can produce a fully re-audited selection.
    selected = importlib.import_module('rwkv_lh.role_trace_selection')
    assert callable(selected.extract_selected_registration)


def test_filter_cannot_keep_raw_regression_after_removing_eval_member(tmp_path,monkeypatch):
    from copy import deepcopy
    reg,samples,bundle=fixture(tmp_path,monkeypatch)
    extra=deepcopy(samples[2]);extra['sample_id']='opaque-extra-dev';samples.append(extra)
    raw=build_artifacts(samples,provenance=bundle.manifest['provenance'])
    reg['candidate_manifest']=write(tmp_path/'candidate-extra.json',raw.manifest)
    reg['regression_fingerprint']=raw.manifest['regression_fingerprint']
    selection=json.loads(Path(reg['row_selection']['path']).read_text())
    selection.update(kept_sample_ids=['opaque-0','opaque-1','opaque-2','opaque-3'],
                     counts={'train':2,'dev':1,'confirmation':1})
    reg['row_selection']=write(tmp_path/'selection-extra.json',selection)
    _mock_extract(monkeypatch,tmp_path,raw.manifest,samples,{})
    with pytest.raises(ValueError,match='selected.*regression'):
        data.freeze_dataset(reg,registration_reference=write(tmp_path/'freeze-extra.json',reg),
            output=tmp_path/'data/datasets/must-not-publish')


def selected_fixture(tmp_path, monkeypatch):
    from copy import deepcopy
    from rwkv_lh import role_trace_selection as api
    monkeypatch.setattr(trace,'ROOT',tmp_path)
    source=write(tmp_path/'raw-source.json',{'unit_test_only':True})
    samples=rows()
    duplicate=deepcopy(samples[0]);duplicate.update(sample_id='unselected-similar',input_text=samples[2]['input_text'])
    samples.append(duplicate)
    provenance={'source_registration_sha256':source['sha256'],'requested_roles':['selector_intent'],
        'source_runs':[{'source_run_id':'opaque-source','run_id':'opaque-run','role_data_collection':None}],
        'coverage_scope_sha256':'f'*64,'equivalence_waiver_sha256':None}
    raw=build_artifacts(samples,provenance=provenance)
    assert raw.manifest['status']=='invalid' and not raw.manifest['quality_gates']['cross_split_similarity']
    raw_root=tmp_path/'raw-artifact';manifest=write_artifacts(raw_root,raw)
    raw_ref={'path':str(raw_root/'manifest.json'),'sha256':data.core.sha256_file(raw_root/'manifest.json')}
    calls=[]
    def replay(source_path,output,**kwargs):
        assert source_path==Path(source['path'])
        calls.append(kwargs)
        return write_artifacts(output,raw)
    monkeypatch.setattr(trace,'extract_registration',replay)
    policy=write(tmp_path/'policy.json',{'unit_test_only':True})
    selection=write(tmp_path/'selected.json',{'schema_version':data.SELECTION_SCHEMA,'role':'selector_intent',
        'kept_sample_ids':['opaque-0','opaque-1','opaque-2','opaque-3'],
        'counts':{'train':2,'dev':1,'confirmation':1},'policy_evidence_refs':[policy]})
    document={'schema_version':api.SOURCE_SCHEMA,'role':'selector_intent',
        'source_groups':[{'source_registration':source,'candidate_manifest':raw_ref}], 'row_selection':selection}
    source_ref=write(tmp_path/'selected-source.json',document)
    return api,document,source_ref,policy,raw_root,calls


def selected_freeze(tmp_path,source_ref,document,policy,candidate_ref,candidate,**extra):
    registration={'schema_version':data.FREEZE_SCHEMA,'role':'selector_intent','authorization':policy,
        'candidate_manifest':candidate_ref,'source_registration':source_ref,'row_selection':document['row_selection'],
        'minimum_counts':{'train':2,'dev':1,'confirmation':1},
        'regression_fingerprint':candidate['regression_fingerprint'],**extra}
    return data.freeze_dataset(registration,registration_reference=write(tmp_path/'freeze-effective.json',registration),
                               output=tmp_path/'data/datasets/effective')


def test_invalid_raw_similarity_pool_replays_to_valid_selection_and_freeze(tmp_path,monkeypatch):
    api,document,source_ref,policy,raw_root,calls=selected_fixture(tmp_path,monkeypatch)
    output=tmp_path/'data/experiments/effective'
    candidate=api.extract_selected_registration(Path(source_ref['path']),output,roles=['selector_intent'])
    assert candidate['status']=='valid' and candidate['coverage_audit']['selector_intent']['execute']==1
    ref={'path':str(output/'manifest.json'),'sha256':data.core.sha256_file(output/'manifest.json')}
    frozen=selected_freeze(tmp_path,source_ref,document,policy,ref,candidate)
    assert frozen['counts']=={'train':2,'dev':1,'confirmation':1}
    regression=json.loads((tmp_path/'data/datasets/effective/regression.json').read_text())
    assert [r['sample_id'] for r in regression['samples_by_split']['dev']]==['opaque-2']
    assert [r['sample_id'] for r in regression['samples_by_split']['confirmation']]==['opaque-3']
    assert len(calls)==2 and not candidate['regression_reused']
    assert json.loads((raw_root/'manifest.json').read_text())['status']=='invalid'


def test_selection_dropping_only_execute_is_invalid_and_cannot_freeze(tmp_path,monkeypatch):
    api,document,source_ref,policy,_,_=selected_fixture(tmp_path,monkeypatch)
    selection=json.loads(Path(document['row_selection']['path']).read_text())
    selection['kept_sample_ids'].remove('opaque-1');selection['counts']['train']=1
    document['row_selection']=write(tmp_path/'missing-execute-selection.json',selection)
    source_ref=write(tmp_path/'missing-execute-source.json',document)
    output=tmp_path/'data/experiments/missing-execute'
    candidate=api.extract_selected_registration(Path(source_ref['path']),output,roles=['selector_intent'])
    assert candidate['status']=='invalid' and candidate['coverage_audit']['selector_intent']['execute']==0
    with pytest.raises(ValueError,match='quality audit is not valid'):
        selected_freeze(tmp_path,source_ref,document,policy,
            {'path':str(output/'manifest.json'),'sha256':data.core.sha256_file(output/'manifest.json')},candidate)


def test_selection_cannot_hide_tampered_unselected_raw_member(tmp_path,monkeypatch):
    api,document,source_ref,_,raw_root,_=selected_fixture(tmp_path,monkeypatch)
    p=raw_root/'candidates.jsonl';p.write_bytes(p.read_bytes().replace(b'unselected-similar',b'unselected-corrupt'))
    with pytest.raises(ValueError,match='SHA-256'):
        api.extract_selected_registration(Path(source_ref['path']),tmp_path/'data/experiments/no-output',roles=['selector_intent'])


def test_selected_source_waiver_must_match_raw_admission_bidirectionally(tmp_path,monkeypatch):
    api,document,source_ref,_,_,calls=selected_fixture(tmp_path,monkeypatch)
    document['source_groups'][0]['equivalence_waiver']=write(tmp_path/'unexpected-waiver.json',{'unit_test_only':True})
    source_ref=write(tmp_path/'unexpected-waiver-source.json',document)
    with pytest.raises(ValueError,match='admission waiver differs'):
        api.extract_selected_registration(Path(source_ref['path']),tmp_path/'data/experiments/no-output',roles=['selector_intent'])
    assert calls==[]


def test_prior_regression_reuses_exact_members_and_fingerprint(tmp_path,monkeypatch):
    api,document,source_ref,policy,_,_=selected_fixture(tmp_path,monkeypatch)
    first=tmp_path/'data/experiments/first'
    initial=api.extract_selected_registration(Path(source_ref['path']),first,roles=['selector_intent'])
    prior_path=first/'regression_candidate.json';prior=json.loads(prior_path.read_text())
    output=tmp_path/'data/experiments/reused'
    candidate=api.extract_selected_registration(Path(source_ref['path']),output,roles=['selector_intent'],
        prior_regression=prior,expected_regression_fingerprint=initial['regression_fingerprint'])
    assert candidate['regression_reused'] and (output/'regression_candidate.json').read_bytes()==prior_path.read_bytes()
    selected_freeze(tmp_path,source_ref,document,policy,
        {'path':str(output/'manifest.json'),'sha256':data.core.sha256_file(output/'manifest.json')},candidate,
        prior_regression={'path':str(prior_path),'sha256':data.core.sha256_file(prior_path)})
    with pytest.raises(ValueError,match='fingerprint'):
        api.extract_selected_registration(Path(source_ref['path']),tmp_path/'data/experiments/wrong-prior',roles=['selector_intent'],
            prior_regression=prior,expected_regression_fingerprint='e'*64)


def test_selected_source_cannot_bypass_scoped_waiver_review(tmp_path,monkeypatch):
    api,document,_,_,raw_root,_=selected_fixture(tmp_path,monkeypatch)
    waiver=write(tmp_path/'accepted-waiver.json',{'schema_version':trace.EQUIVALENCE_WAIVER_SCHEMA,
        'decision':'accept','reviewers':['MOCK-ONE','MOCK-TWO'],'entries':[{
            'path':'rwkv_lh/statetune_data.py','frozen_sha256':'c'*64,'current_sha256':'d'*64,
            'rationale':'Opaque scope-validation fixture only.','evidence_refs':['MOCK-only']}]})
    original=json.loads((raw_root/'manifest.json').read_text())
    incoming=[json.loads(line) for line in (raw_root/'candidates.jsonl').read_text().splitlines()]
    provenance=original['provenance'];provenance['equivalence_waiver_sha256']=waiver['sha256']
    bundle=build_artifacts(incoming,provenance=provenance)
    sealed_raw=tmp_path/'raw-with-waiver';write_artifacts(sealed_raw,bundle)
    group={**document['source_groups'][0],'equivalence_waiver':waiver,
        'candidate_manifest':{'path':str(sealed_raw/'manifest.json'),'sha256':data.core.sha256_file(sealed_raw/'manifest.json')}}
    monkeypatch.setattr(trace,'extract_registration',lambda source,output,**kwargs:write_artifacts(output,bundle))
    with pytest.raises(ValueError,match='scope.*review'):
        api._replay_group(group,tmp_path/'raw-replay','selector_intent')


@pytest.mark.parametrize('field,bad_value',[(None,None),('registration_sha256','0'*64),
    ('waiver_sha256','0'*64),('wrapper_sha256','0'*64),('role','executor_args'),('source_count',2)])
def test_waiver_scope_is_exactly_bound_to_source_role_and_wrapper(tmp_path,field,bad_value):
    from rwkv_lh import role_trace_selection as api
    source={'source_runs':[{'source_run_id':'opaque','run_id':'opaque'}]}
    source_ref=write(tmp_path/'source.json',source)
    waiver=write(tmp_path/'waiver.json',{'schema_version':trace.EQUIVALENCE_WAIVER_SCHEMA,
        'decision':'accept','reviewers':['MOCK-ONE','MOCK-TWO'],'entries':[{
            'path':'rwkv_lh/statetune_data.py','frozen_sha256':'c'*64,'current_sha256':'d'*64,
            'rationale':'Opaque scope-validation fixture only.','evidence_refs':['MOCK-only']}]})
    reviews=[]
    for who in ['MOCK-ONE','MOCK-TWO']:
        review={'reviewer':who,'decision':'accept','registration_sha256':source_ref['sha256'],
            'waiver_sha256':waiver['sha256'],'wrapper_sha256':data.core.sha256_file(api.__file__),
            'role':'selector_intent','source_count':1}
        if field is not None and who=='MOCK-TWO':review[field]=bad_value
        reviews.append(write(tmp_path/(who+'.json'),review))
    group={'source_registration':source_ref,'equivalence_waiver':waiver,'waiver_reviews':reviews}
    if field is None:
        assert api._scoped_waiver(group,source,'selector_intent')=={'rwkv_lh/statetune_data.py':('c'*64,'d'*64)}
    else:
        with pytest.raises(ValueError,match='scope review'):
            api._scoped_waiver(group,source,'selector_intent')
