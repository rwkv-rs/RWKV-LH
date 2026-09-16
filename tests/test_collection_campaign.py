import hashlib
import json
import pytest


def batch(tmp_path, name, source='source-one', family='family-one'):
    inventory = tmp_path / (name+'.jsonl')
    inventory.write_text(json.dumps({'source_id': source, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
        'job': {'task_id': source, 'workspace': str(tmp_path/source/'initial'),
                'output_dir': str(tmp_path/source/'run')}})+'\n')
    manifest = tmp_path/(name+'.json')
    manifest.write_text(json.dumps({'batch_id': name, 'inventory': str(inventory),
        'inventory_sha256': hashlib.sha256(inventory.read_bytes()).hexdigest(),
        'families': {source: family}}))
    return manifest


def test_campaign_advances_batches_and_survives_restart(tmp_path):
    from rwkv_lh.collection_campaign import Campaign
    first = batch(tmp_path, 'one')
    second = batch(tmp_path, 'two', 'source-two', 'family-two')
    with Campaign(tmp_path/'campaign.sqlite3', {'frozen': 'identity'}) as campaign:
        campaign.admit(first)
        campaign.admit(second)
        assert campaign.next_batch()['batch_id'] == 'one'
        campaign.finish('one', {'reason': 'exhausted', 'counts': {'recorded': 1}})
    with Campaign(tmp_path/'campaign.sqlite3', {'frozen': 'identity'}) as campaign:
        assert campaign.next_batch()['batch_id'] == 'two'
        campaign.finish('two', {'reason': 'exhausted', 'counts': {'recorded': 1}})
        assert campaign.next_batch() is None
        assert campaign.counts() == {'recorded': 2}


def test_campaign_deduplicates_families_across_batches_before_execution(tmp_path):
    from rwkv_lh.collection_campaign import Campaign
    with Campaign(tmp_path/'c', {}) as campaign:
        campaign.admit(batch(tmp_path, 'one'))
        with pytest.raises(ValueError, match='duplicate'):
            campaign.admit(batch(tmp_path, 'two', 'different-source', 'family-one'))
        assert campaign.counts() == {'pending': 1}


def test_campaign_changed_manifest_and_unresolved_work_do_not_advance(tmp_path):
    from rwkv_lh.collection_campaign import Campaign
    with Campaign(tmp_path/'c', {}) as campaign:
        manifest = batch(tmp_path, 'one')
        campaign.admit(manifest)
        with pytest.raises(ValueError, match='incomplete'):
            campaign.finish('one', {'reason':'unresolved_running','counts':{'running':1}})
        assert campaign.next_batch()['batch_id'] == 'one'
        manifest.write_text('{}')
        with pytest.raises(ValueError, match='changed'):
            campaign.next_batch()


def test_campaign_cli_runs_next_batch_without_manual_restart(tmp_path, monkeypatch):
    import sqlite3
    from types import SimpleNamespace
    import scripts.run_collection_campaign as runner
    root = tmp_path/'campaign';(root/'ready').mkdir(parents=True)
    for name, source in [('one','a'),('two','b')]:
        manifest = batch(tmp_path, name, source, 'family-'+source)
        (root/'ready'/manifest.name).write_bytes(manifest.read_bytes())
    replicas = tmp_path/'replicas.json';replicas.write_text('[]')
    monkeypatch.setattr(runner, 'verify_item', lambda *args, **kwargs: None)
    run_order = []
    def process(cmd, **kwargs):
        queue = cmd[cmd.index('--queue')+1]
        with sqlite3.connect(queue) as db:
            if '--inventory' in cmd:
                db.execute('CREATE TABLE tasks(status TEXT,result TEXT)')
                db.execute("INSERT INTO tasks VALUES ('pending',NULL)")
            else:
                assert '--run' in cmd
                run_order.append(queue)
                db.execute("UPDATE tasks SET status='recorded', result=?", (json.dumps({'trace_complete':True}),))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess, 'run', process)
    monkeypatch.setattr(runner.sys, 'argv', ['campaign','--root',str(root),
        '--replicas',str(replicas),'--env-file',str(tmp_path/'missing-env'),
        '--target-tasks','2'])
    assert runner.main() == 0
    assert len(run_order) == 2 and run_order[0] != run_order[1]
    status = json.loads((root/'STATUS.json').read_text())
    assert status['phase'] == 'collection_recorded' and status['recorded_tasks'] == 2
    assert status['teacher_calls'] == 0
