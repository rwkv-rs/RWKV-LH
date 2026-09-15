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
        queue.finish('source:1', {'id': 't1', 'termination': 'submitted'})
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
    acceptance.write_text('{"kind":"manual_rubric","criteria":["Faithful answer"]}')
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
        second.update(source_id='source:2', source_sha256='d' * 64)
        second['job'].update(task_id='t2', workspace=str(tmp_path / 'output' / 'nested'),
                             output_dir=str(tmp_path / 'another'))
        queue.admit(second)
        with pytest.raises(ValueError, match='output contains source'):
            validate_inventory(queue)


def test_claim_validates_digest_and_preflight_before_running(tmp_path):
    with CollectionQueue(tmp_path / 'q') as queue:
        queue.admit(item())
        def reject(value):
            raise ValueError('preflight failed')
        with pytest.raises(ValueError, match='preflight failed'):
            queue.claim(verify=reject)
        assert queue.counts() == {'pending': 1}
        queue.db.execute("UPDATE tasks SET payload=replace(payload, 't1', 't2')")
        with pytest.raises(ValueError, match='digest'):
            queue.claim()
        assert queue.counts() == {'pending': 1}


def test_result_identity_and_duplicate_bytes(tmp_path):
    with CollectionQueue(tmp_path / 'q') as queue:
        queue.admit(item())
        duplicate = item()
        duplicate.update(source_id='another')
        duplicate['job'] = {'task_id': 'another'}
        with pytest.raises(ValueError, match='duplicate'):
            queue.admit(duplicate)
        queue.claim()
        with pytest.raises(ValueError, match='identity'):
            queue.finish('source:1', {'id': 'wrong'})
        assert queue.counts() == {'running': 1}


def test_malformed_source_role_is_quarantinable():
    from rwkv_lh.ultradata import audit_trajectory
    result = audit_trajectory({'messages': [{'role': []}], 'tools': []})
    assert 'unknown_message_role' in result['review_reasons']


def test_receipt_recovers_completed_task_without_reexecution(tmp_path):
    from rwkv_lh.collection_execution import save_receipt, reconcile
    row = item()
    row['job']['output_dir'] = str(tmp_path / 'output')
    with CollectionQueue(tmp_path / 'q') as queue:
        queue.admit(row)
        queue.claim()
        assert reconcile(queue) == 1
        result = {'id': 't1', 'termination': 'submitted', 'generation_started': 2}
        save_receipt(row, result)
        assert reconcile(queue) == 0
        assert queue.counts() == {'recorded': 1}
        assert reconcile(queue) == 0


def test_campaign_seal_rejects_changes_and_new_admission(tmp_path):
    with CollectionQueue(tmp_path / 'q') as queue:
        queue.admit(item())
        queue.seal({'code': 'original'})
        queue.seal({'code': 'original'})
        with pytest.raises(ValueError, match='changed'):
            queue.seal({'code': 'other'})
        with pytest.raises(ValueError, match='frozen'):
            queue.admit(item())


def test_private_reference_cannot_be_visible_to_other_job(tmp_path):
    from scripts.run_collection_queue import validate_inventory
    with CollectionQueue(tmp_path / 'q') as queue:
        a = item()
        a['job'].update(workspace=str(tmp_path/'a'), output_dir=str(tmp_path/'out-a'))
        a['acceptance_path'] = str(tmp_path/'b'/'private.json')
        b = item()
        b.update(source_id='b', source_sha256='d'*64)
        b['job'].update(task_id='b',workspace=str(tmp_path/'b'),output_dir=str(tmp_path/'out-b'))
        queue.admit(a);queue.admit(b)
        with pytest.raises(ValueError, match='private evidence'):
            validate_inventory(queue)


def test_source_scan_quarantines_bad_json_and_writes_completion(tmp_path):
    from scripts.audit_collection_sources import audit_source
    import json
    source=tmp_path/'source.jsonl';output=tmp_path/'audit.jsonl'
    source.write_text('not-json\n'+json.dumps({'messages':[{'role':[]}], 'tools':[]})+'\n')
    result=audit_source(source, 'a'*40, output)
    assert result['rows']==2 and result['invalid_rows']==1
    assert output.exists() and not (tmp_path/'audit.jsonl.partial').exists()
    with pytest.raises(FileExistsError):
        audit_source(source,'a'*40,output,resume=True)


def test_receipt_tampering_is_not_recovered(tmp_path):
    from rwkv_lh.collection_execution import save_receipt, reconcile
    import json
    row=item();row['job']['output_dir']=str(tmp_path/'out')
    with CollectionQueue(tmp_path/'q') as queue:
        queue.admit(row);queue.claim()
        save_receipt(row, {'id':'t1','termination':'submitted'})
        path=tmp_path/'out'/'COLLECTION_RECEIPT.json'
        receipt=json.loads(path.read_text());receipt['result']['id']='another'
        path.write_text(json.dumps(receipt))
        with pytest.raises(ValueError,match='digest'):
            reconcile(queue)
        assert queue.counts()=={'running':1}


def test_source_scan_resumes_only_valid_prefix(tmp_path, monkeypatch):
    import json
    import scripts.audit_collection_sources as audit
    source=tmp_path/'source';output=tmp_path/'output'
    source.write_text(''.join(json.dumps({'messages':[], 'tools':[]})+'\n' for _ in range(102)))
    original=audit.audit_trajectory
    calls=0
    def interrupted(row):
        nonlocal calls
        calls+=1
        if calls==101:raise KeyboardInterrupt()
        return original(row)
    monkeypatch.setattr(audit,'audit_trajectory',interrupted)
    with pytest.raises(KeyboardInterrupt):audit.audit_source(source,'a'*40,output)
    assert not output.exists()
    monkeypatch.setattr(audit,'audit_trajectory',original)
    result=audit.audit_source(source,'a'*40,output,resume=True)
    assert result['rows']==102 and len(output.read_text().splitlines())==102
