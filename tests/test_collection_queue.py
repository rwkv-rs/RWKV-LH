import pytest
from rwkv_lh.collection_queue import CollectionQueue


def item():
    return {'source_id': 'source:1', 'source_sha256': 'a' * 64,
            'job': {'task_id': 't1'}, 'environment_sha256': 'b' * 64,
            'acceptance_sha256': 'c' * 64}


def test_resume_never_silently_reexecutes_uncertain_work(tmp_path):
    path = tmp_path / 'queue.sqlite3'
    with CollectionQueue(path) as queue:
        queue.admit(item())
        claimed = queue.claim()
        assert claimed['source_id'] == 'source:1'
    with CollectionQueue(path) as queue:
        assert queue.claim() is None
        assert queue.counts() == {'running': 1}
        queue.finish('source:1', {'termination': 'submitted'})
        assert queue.counts() == {'recorded': 1}
        assert queue.claim() is None


def test_duplicate_source_and_changed_freeze_are_rejected(tmp_path):
    with CollectionQueue(tmp_path / 'q') as queue:
        queue.admit(item())
        changed = item()
        changed['job'] = {'task_id': 'another'}
        with pytest.raises(ValueError):
            queue.admit(changed)
        with pytest.raises(ValueError):
            queue.admit(item())
        with pytest.raises(ValueError):
            queue.finish('source:1', {})


def test_bad_identity_and_transactional_claim(tmp_path):
    path = tmp_path / 'q'
    with CollectionQueue(path) as first, CollectionQueue(path) as second:
        bad = item()
        bad['source_sha256'] = 'unknown'
        with pytest.raises(ValueError):
            first.admit(bad)
        first.admit(item())
        assert first.claim() is not None
        assert second.claim() is None


def test_direct_collection_rejects_assistance_and_requires_budgets():
    from scripts.run_collection_queue import make_job
    row = dict(task_id='t', request='read', workspace='/tmp/source',
               output_dir='/tmp/output', tool_scope='files', max_calls=2, max_seconds=30)
    assert make_job(row).tool_scope == 'files'
    with pytest.raises(ValueError):
        make_job({**row, 'on_stall': 'takeover'})
    row.pop('max_calls')
    with pytest.raises(ValueError):
        make_job(row)


def test_changed_source_is_rejected_before_execution(tmp_path):
    from scripts.run_collection_queue import verify_item
    import hashlib
    import json
    from rwkv_lh.workspace_snapshot import tree_identity
    source = tmp_path / 'original.json'
    source.write_text('{}')
    acceptance = tmp_path / 'private.json'
    acceptance.write_text('{}')
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    (workspace / 'TASK.md').write_text('Read this document.')
    row = item()
    row.update(source_path=str(source), acceptance_path=str(acceptance),
               source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
               acceptance_sha256=hashlib.sha256(acceptance.read_bytes()).hexdigest(),
               environment_sha256=hashlib.sha256(json.dumps(tree_identity(workspace, allow_links=False),
                   sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
               job=dict(task_id='t1', request='Read TASK.md', workspace=str(workspace),
                        output_dir=str(tmp_path / 'output'), tool_scope='files', max_calls=2, max_seconds=30))
    verify_item(row)
    source.write_text('{"changed":true}')
    with pytest.raises(ValueError, match='source_path changed'):
        verify_item(row)


def test_cross_batch_output_cannot_contain_another_source(tmp_path):
    from scripts.run_collection_queue import validate_inventory
    with CollectionQueue(tmp_path / 'q') as queue:
        first = item()
        first['job'].update(workspace=str(tmp_path / 'input'), output_dir=str(tmp_path / 'output'))
        queue.admit(first)
        second = item()
        second.update(source_id='source:2')
        second['job'].update(task_id='t2', workspace=str(tmp_path / 'output' / 'nested'),
                             output_dir=str(tmp_path / 'another'))
        queue.admit(second)
        with pytest.raises(ValueError, match='output contains source'):
            validate_inventory(queue)
