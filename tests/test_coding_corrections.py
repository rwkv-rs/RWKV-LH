import hashlib
import json
import pytest
from rwkv_lh import model_io
from rwkv_lh.coding_corrections import validate_coding_correction, tree_sha256
from rwkv_lh.workspace_snapshot import tree_identity
from test_unified_controller import call


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def candidate(tmp_path, monkeypatch):
    import rwkv_lh.coding_corrections as module
    root = tmp_path / 'source'; before = root / 'tool_snapshots/001/before'; before.mkdir(parents=True)
    (before / 'a.py').write_text('value = 1\n')
    original = json.dumps(call('write_file', path='a.py', content='value = 1\n'))
    target = json.dumps(call('write_file', path='a.py', content='value = 2\n')) + model_io.JSON_CALL_STOP_SUFFIXES[0]
    (before.parent / 'call.json').write_text(json.dumps({'action_type': 'write_file', 'arguments': {'path': 'a.py', 'content': 'value = 1\n'}}))
    for name in ('state_snapshot.json', 'model_trace.jsonl'):
        (root / name).write_text('{}')
    (root / 'RESULT.json').write_text(json.dumps({'tool_scope': 'coding', 'assistance': 'rwkv_independent'}))
    monkeypatch.setattr(module, 'replay_run', lambda *args: {'cp': {'input_text': 'visible input', 'input_token_ids': [0, 1],
        'input_checkpoint_id': 'parent', 'request_id': 'r', 'raw_generation': {'raw_output': original}}})
    return dict(run_root=root, checkpoint_id='cp', target_text=target, model_sha256='a'*64,
        source_files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},
        snapshot='tool_snapshots/001/before', snapshot_sha256=tree_sha256(tree_identity(before)),
        checks=[['python3', '-B', '-c', 'from a import value; assert value == 2']],
        reviews=[{'reviewer': r, 'accepted': True, 'visible_evidence_only': True,
                  'target_sha256': sha(target), 'input_sha256': sha('visible input')} for r in ('one', 'two')],
        output=tmp_path / 'validation')


def test_correction_executes_real_red_green_without_modifying_source(candidate):
    result = validate_coding_correction(**candidate)
    assert result['status'] == 'validated_candidate'
    assert result['training_admitted'] is False
    assert result['before_checks'][0]['exit_code'] != 0
    assert result['after_checks'][0]['exit_code'] == 0
    assert (candidate['run_root'] / candidate['snapshot'] / 'a.py').read_text() == 'value = 1\n'
    assert result['target_text'] == candidate['target_text']


def test_noop_correction_is_not_a_valid_edit(candidate):
    target = json.dumps(call('write_file', path='a.py', content='value = 1\n')) + model_io.JSON_CALL_STOP_SUFFIXES[0]
    candidate['target_text'] = target
    for review in candidate['reviews']: review['target_sha256'] = sha(target)
    assert validate_coding_correction(**candidate)['status'] == 'no_effective_change'


def test_missing_test_program_is_not_red_evidence(candidate):
    candidate['checks'] = [['/nonexistent/rwkv-test-program']]
    assert validate_coding_correction(**candidate)['status'] == 'baseline_not_reproduced'


def test_test_claim_without_real_success_is_rejected(candidate):
    candidate['checks'] = [['python3', '-B', '-c', 'raise SystemExit(1)']]
    assert validate_coding_correction(**candidate)['status'] == 'verification_failed'


def test_candidate_without_bound_reviews_does_not_execute(candidate):
    candidate['reviews'][0]['input_sha256'] = 'b'*64
    with pytest.raises(ValueError, match='reviews'):
        validate_coding_correction(**candidate)
    assert not candidate['output'].exists()


def test_changed_source_is_rejected_before_execution(candidate):
    (candidate['run_root'] / 'model_trace.jsonl').write_text('tampered')
    with pytest.raises(ValueError, match='source'):
        validate_coding_correction(**candidate)
    assert not candidate['output'].exists()


def test_future_or_wrong_snapshot_cannot_be_substituted(candidate):
    candidate['snapshot_sha256'] = 'b'*64
    with pytest.raises(ValueError, match='snapshot'):
        validate_coding_correction(**candidate)


def test_takeover_is_not_rwkv_correction_source(candidate):
    path = candidate['run_root'] / 'RESULT.json'
    path.write_text(json.dumps({'tool_scope': 'coding', 'assistance': 'strong_takeover'}))
    candidate['source_files']['RESULT.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='takeover'):
        validate_coding_correction(**candidate)


def test_real_failed_write_is_replayed_and_rejected_as_noop(tmp_path):
    import tarfile
    from pathlib import Path
    from rwkv_lh.direct_trace_data import replay_run
    archive = Path(__file__).resolve().parents[1] / 'data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/EVIDENCE.tar.gz'
    prefix = 'runs/atomic-2/execution/'
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.isfile() and m.name.startswith(prefix)
                   and (m.name[len(prefix):] in ('RESULT.json', 'model_trace.jsonl', 'state_snapshot.json')
                        or '/tool_snapshots/' in m.name)]
        tar.extractall(tmp_path, members=members, filter='data')
    root = tmp_path / prefix
    model_sha = '559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
    rows = replay_run(root, model_sha)
    cp, row = next((cp, row) for cp, row in rows.items()
                   if model_io.parse_model_command(row['raw_generation']['raw_output']).name == 'write_file')
    original = row['raw_generation']['raw_output']
    target = original if original.endswith(model_io.JSON_CALL_STOP_SUFFIXES[0]) else original + model_io.JSON_CALL_STOP_SUFFIXES[0]
    reviews = [{'reviewer': r, 'accepted': True, 'visible_evidence_only': True,
                'target_sha256': sha(target), 'input_sha256': sha(row['input_text'])}
               for r in ('unit-test-review-a', 'unit-test-review-b')]
    result = validate_coding_correction(run_root=root, checkpoint_id=cp, target_text=target,
        model_sha256=model_sha,
        source_files={str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()},
        snapshot='tool_snapshots/002/before', snapshot_sha256=tree_sha256(tree_identity(root / 'tool_snapshots/002/before')),
        checks=[['python3', '-B', '-m', 'unittest', 'test_query_limit']], reviews=reviews, output=tmp_path / 'audit')
    assert result['status'] == 'no_effective_change'
    assert result['training_admitted'] is False


def test_training_admission_rechecks_sealed_correction(candidate, tmp_path):
    from rwkv_lh.coding_corrections import revalidate_training_correction
    proof = validate_coding_correction(**candidate)
    reference = {'path': str(candidate['output'] / 'VALIDATION.json'),
                 'sha256': sha((candidate['output'] / 'VALIDATION.json').read_text())}
    row = {'target_text': candidate['target_text'], 'input_text': 'visible input',
           'input_token_ids': [0, 1], 'candidate_checkpoint_id': 'cp',
           'input_checkpoint_id': 'parent', 'request_id': 'r', 'reviews': candidate['reviews'],
           'correction_validation': reference}
    result = revalidate_training_correction(row, run_root=candidate['run_root'],
        source_files=candidate['source_files'], model_sha256=candidate['model_sha256'], output=tmp_path / 'fresh')
    assert result['status'] == 'validated_candidate'
    assert result['target_text'] == proof['target_text']
    assert result['before_checks'][0]['exit_code'] != 0
    assert result['after_checks'][0]['exit_code'] == 0


@pytest.mark.parametrize('field,value', [('target_text','wrong'), ('input_text','future observation'),
    ('input_token_ids',[0, 3]), ('candidate_checkpoint_id','future'), ('request_id','other')])
def test_training_admission_rejects_proof_for_other_boundary(candidate, tmp_path, field, value):
    from rwkv_lh.coding_corrections import revalidate_training_correction
    validate_coding_correction(**candidate)
    path = candidate['output'] / 'VALIDATION.json'
    row = {'target_text': candidate['target_text'], 'input_text': 'visible input',
           'input_token_ids': [0, 1], 'candidate_checkpoint_id': 'cp',
           'input_checkpoint_id': 'parent', 'request_id': 'r', 'reviews': candidate['reviews'],
           'correction_validation': {'path':str(path),'sha256':sha(path.read_text())}}
    row[field] = value
    with pytest.raises(ValueError, match='binding'):
        revalidate_training_correction(row, run_root=candidate['run_root'],
            source_files=candidate['source_files'], model_sha256=candidate['model_sha256'], output=tmp_path/'fresh')
    assert not (tmp_path/'fresh').exists()


@pytest.mark.parametrize('mode', ['checksum', 'stale_success', 'unsealed_source'])
def test_training_admission_does_not_trust_a_success_flag(candidate, tmp_path, mode):
    from rwkv_lh.coding_corrections import revalidate_training_correction
    validate_coding_correction(**candidate)
    path = candidate['output']/'VALIDATION.json'
    proof=json.loads(path.read_text())
    if mode=='stale_success':
        proof['checks']=[['python3','-B','-c','raise SystemExit(1)']]
        path.write_text(json.dumps(proof))
    row={'target_text':candidate['target_text'],'input_text':'visible input','input_token_ids':[0,1],
         'candidate_checkpoint_id':'cp','input_checkpoint_id':'parent','request_id':'r','reviews':candidate['reviews'],
         'correction_validation':{'path':str(path),'sha256':sha(path.read_text())}}
    if mode=='checksum':path.write_text(path.read_text()+' ')
    if mode=='unsealed_source':(candidate['run_root']/'model_trace.jsonl').write_text('changed')
    with pytest.raises(ValueError):
        revalidate_training_correction(row,run_root=candidate['run_root'],source_files=candidate['source_files'],
            model_sha256=candidate['model_sha256'],output=tmp_path/'fresh')
    if mode=='stale_success':
        assert json.loads((tmp_path/'fresh/VALIDATION.json').read_text())['status']=='verification_failed'


def test_direct_freeze_reverifies_coding_and_preserves_proof(candidate, tmp_path, monkeypatch):
    import types
    import rwkv_lh.direct_trace_data as direct
    from rwkv_lh.statetune_data import FREEZE_SCHEMA
    proof=validate_coding_correction(**candidate)
    def seal(name,value):
        p=tmp_path/name;p.write_text(json.dumps(value))
        return {'path':str(p),'sha256':sha(p.read_text())}
    reference={'path':str(candidate['output']/'VALIDATION.json'),
               'sha256':sha((candidate['output']/'VALIDATION.json').read_text())}
    source={'source_id':'source','split':'train','family':'training-project','source_content_sha256':'a'*64,
            'run_root':str(candidate['run_root']), 'manifest':seal('source.json',{
                'source_type':'native_production_trace','model_sha256':candidate['model_sha256'],
                'collector_source_manifest_sha256':'b'*64,'server_identity_sha256':'c'*64,
                'files':candidate['source_files']})}
    row={'sample_id':'edit','source_id':'source','family':source['family'],
         'source_manifest_sha256':source['manifest']['sha256'],'source_content_sha256':'a'*64,
         'target_text':candidate['target_text'],'input_text':'visible input','input_token_ids':[0,1],
         'candidate_checkpoint_id':'cp','input_checkpoint_id':'parent','request_id':'r','reviews':candidate['reviews'],
         'label_authority':'verified_coding','correction_validation':reference}
    # This integration test isolates freeze dispatch. Token/protocol normalization
    # has its own tests; fresh tools, checks, proof binding and publication are real.
    monkeypatch.setattr(direct,'normalize_direct_row',lambda row,**kw:None)
    monkeypatch.setattr(direct,'replay_run',lambda *a:{'cp':row})
    monkeypatch.setattr(direct.RunState,'from_dict',lambda value:types.SimpleNamespace())
    monkeypatch.setattr(direct,'audit_source_similarity',lambda *a,**kw:{'passed':True})
    regression=seal('regression.json',{'cases':[
        {'split':'dev','family':'dev-project','source_content_sha256':'d'*64},
        {'split':'confirmation','family':'confirmation-project','source_content_sha256':'e'*64}]})
    registration={'schema_version':FREEZE_SCHEMA,'role':direct.ROLE,
        'authorization':seal('authorization.json',{'authorized':True}),
        'reviewed_rows':seal('rows.json',{'rows':[row]}),'regression_registration':regression,
        'regression_fingerprint':regression['sha256'],'sources':[source],'similarity_threshold':0.9,
        'similarity_audit':seal('similarity.json',{'passed':True}),'model_sha256':candidate['model_sha256'],
        'context_tokens':8192,'vocab_size':65536,'bos_token_id':0,
        'minimum_coverage':{'source_files':1,'families':1,'read_boundaries':0,'summary_boundaries':0,'coding_boundaries':1},
        'minimum_counts':{'train':1,'dev':1,'confirmation':1}}
    output=tmp_path/'published'
    manifest=direct.freeze_direct_dataset(registration,registration_reference=seal('registration.json',registration),output=output)
    assert manifest['coding_validation']['count']==1
    archived=json.loads((output/'coding_validation.json').read_text())['rows'][0]['validation']
    assert archived['status']=='validated_candidate'
    assert archived['before_checks'][0]['exit_code'] != 0
    assert archived['after_checks'][0]['exit_code'] == 0
    assert json.loads((output/'train.jsonl').read_text())['target_text']==candidate['target_text']
    import rwkv_lh.statetune_data as data
    monkeypatch.setattr(data,'normalize_row',lambda row,**kw:{'sample_id':row['sample_id']})
    published_reference={'path':str(output/'manifest.json'),'sha256':sha((output/'manifest.json').read_text())}
    args=dict(role=direct.ROLE,expected_regression=regression['sha256'],model_sha256=candidate['model_sha256'],
              context_tokens=8192,vocab_size=65536,bos_token_id=0)
    assert len(data.admit_dataset(published_reference,**args)[1])==1
    (output/'coding_validation.json').write_text('{}')
    with pytest.raises(ValueError,match='SHA'):
        data.admit_dataset(published_reference,**args)


def test_training_admission_requires_sealed_snapshot_members(candidate, tmp_path):
    from rwkv_lh.coding_corrections import revalidate_training_correction
    candidate['source_files'].pop('tool_snapshots/001/before/a.py')
    validate_coding_correction(**candidate)
    path=candidate['output']/'VALIDATION.json'
    row={'target_text':candidate['target_text'],'input_text':'visible input','input_token_ids':[0,1],
         'candidate_checkpoint_id':'cp','input_checkpoint_id':'parent','request_id':'r','reviews':candidate['reviews'],
         'correction_validation':{'path':str(path),'sha256':sha(path.read_text())}}
    with pytest.raises(ValueError,match='unsealed correction snapshot'):
        revalidate_training_correction(row,run_root=candidate['run_root'],source_files=candidate['source_files'],
            model_sha256=candidate['model_sha256'],output=tmp_path/'fresh')
