import hashlib
import pytest
from rwkv_lh import model_io
from rwkv_lh.statetune_data import _protocol


def test_direct_actor_uses_existing_production_protocol_identity():
    version, sha = _protocol('direct_actor')
    assert version == model_io.MODEL_COMMAND_NORMALIZER_VERSION
    assert sha == hashlib.sha256(open(model_io.__file__, 'rb').read()).hexdigest()


def test_direct_row_rejects_unverified_or_wrong_split():
    from rwkv_lh.direct_trace_data import normalize_direct_row
    with pytest.raises(ValueError, match='recomputed'):
        normalize_direct_row({}, model_sha256='0'*64, context_tokens=8192, vocab_size=65536, bos_token_id=0)


def test_direct_freeze_rejects_cross_split_families():
    from rwkv_lh.direct_trace_data import validate_split_isolation
    with pytest.raises(ValueError, match='family'):
        validate_split_isolation([{'family':'project-a','split':'train','source_content_sha256':'a'*64},
                                  {'family':'project-a','split':'dev','source_content_sha256':'b'*64}])


def test_direct_freeze_rejects_cross_split_identical_sources():
    from rwkv_lh.direct_trace_data import validate_split_isolation
    with pytest.raises(ValueError, match='content'):
        validate_split_isolation([{'family':'project-a','split':'train','source_content_sha256':'a'*64},
                                  {'family':'project-b','split':'dev','source_content_sha256':'a'*64}])


def test_direct_freeze_accepts_independent_source_families():
    from rwkv_lh.direct_trace_data import validate_split_isolation
    validate_split_isolation([{'family':'project-a','split':'train','source_content_sha256':'a'*64},
                              {'family':'project-b','split':'dev','source_content_sha256':'b'*64}])


def test_real_direct_trace_replays_through_production_builder(tmp_path):
    from pathlib import Path
    from rwkv_lh.direct_trace_data import replay_run
    root = Path(__file__).resolve().parents[1]
    import tarfile
    archive = root / 'data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913/RAW_EVIDENCE.tar.gz'
    with tarfile.open(archive) as tar:
        members = [m for m in tar.getmembers() if m.name.startswith('runs/trial-1/') and m.isfile()
                   and ('/workspace/' in m.name or m.name.endswith(('state_snapshot.json', 'model_trace.jsonl')))]
        tar.extractall(tmp_path, members=members, filter='data')
    run = tmp_path / 'runs/trial-1'
    rows = replay_run(run, '559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65')
    assert len(rows) == 3
    assert all(row['recomputed'] for row in rows.values())


def test_training_distinguishes_serving_identity_from_container_hash():
    from rwkv_lh.statetune_training import production_model_identity
    manifest = {'source': {'sha256': 'a'*64}, 'output': {'weights_sha256': 'b'*64}}
    assert production_model_identity('direct_actor', manifest) == 'a'*64
    assert production_model_identity('selector_intent', manifest) == 'b'*64


def test_near_duplicate_sources_are_audited_across_splits(tmp_path):
    from rwkv_lh.direct_trace_data import audit_source_similarity
    left, right = tmp_path/'left.txt', tmp_path/'right.txt'
    left.write_text('Shared document content. ' * 80 + 'alpha')
    right.write_text('Shared document content. ' * 80 + 'beta')
    rows = [{'id': str(n), 'split': split, 'source_content_sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
             'content_reference': {'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}}
            for n, (p, split) in enumerate([(left, 'train'), (right, 'dev')])]
    audit = audit_source_similarity(rows, threshold=0.9)
    assert not audit['passed']
    assert len(audit['violations']) == 1


def test_executed_read_binding_accepts_documented_omission_not_wrong_parameters():
    from rwkv_lh.direct_trace_data import executed_arguments
    from rwkv_lh.model_io import parse_model_command
    command = parse_model_command('{"function":"read_file","params":{"path":"notes.txt"}}')
    args = executed_arguments(command)
    assert args == {'path': 'notes.txt', 'start_byte': 0, 'max_tokens': 4096}
    assert command.arguments == {'path': 'notes.txt'}
    invalid = parse_model_command('{"function":"read_file","params":{"path":"notes.txt","end_byte":"EOF"}}')
    with pytest.raises(Exception):
        executed_arguments(invalid)
