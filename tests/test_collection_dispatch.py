from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sqlite3
import time

from rwkv_lh.collection_queue import CollectionQueue
from rwkv_lh.coding_agent import CodingJob
from rwkv_lh import collection_execution as execution


class TestPool(ThreadPoolExecutor):
    __test__ = False
    def __init__(self, max_workers, mp_context):
        super().__init__(max_workers=max_workers)


def admit(queue, root, name):
    item={'source_id':name,'source_sha256':hashlib.sha256(name.encode()).hexdigest(),
          'environment_sha256':'b'*64,'acceptance_sha256':'c'*64,
          'job':{'task_id':name,'output_dir':str(root/name),'tool_scope':'coding'}}
    queue.admit(item)
    return item


def job(item):
    return CodingJob(item['job']['task_id'],'engineering fixture','unused',item['job']['output_dir'],2,3)


def test_two_replicas_keep_each_task_on_one_service_and_drain_inventory(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from threading import Barrier
    monkeypatch.setattr(execution, 'ProcessPoolExecutor', TestPool)
    barrier = Barrier(2)
    calls = []
    def worker(item, task, settings, service_identity=None):
        calls.append((task.task_id, settings.base_url, service_identity))
        if len(calls) <= 2:
            barrier.wait(timeout=3)
        result = {'id': task.task_id, 'trace_complete': True, 'generation_started': 1,
                  'termination': 'interrupted', 'termination_reason': 'model_budget'}
        execution.save_receipt(item, result)
        return result
    monkeypatch.setattr(execution, 'execute', worker)
    replicas = [(SimpleNamespace(base_url='http://gpu0'), {'model': 'same'}),
                (SimpleNamespace(base_url='http://gpu2'), {'model': 'same'})]
    with CollectionQueue(tmp_path/'q') as queue:
        for name in ('one', 'two', 'three', 'four', 'five'):
            admit(queue, tmp_path, name)
        result = execution.dispatch(queue, settings=None, verify=job, concurrency=2,
            deadline=time.time()+10, replicas=replicas)
        assert result['reason'] == 'exhausted'
        assert queue.counts() == {'recorded': 5}
    assert len({c[0] for c in calls}) == 5
    assert {c[1] for c in calls[:2]} == {'http://gpu0', 'http://gpu2'}
    assert all(c[2] == {'model': 'same'} for c in calls)


def test_replica_count_cannot_silently_exceed_worker_count(tmp_path):
    import pytest
    with CollectionQueue(tmp_path/'q') as queue:
        with pytest.raises(ValueError, match='replica'):
            execution.dispatch(queue, settings=None, verify=job, concurrency=1,
                deadline=time.time()+10, replicas=[(None, {}), (None, {})])


def test_fast_receipt_is_committed_before_slow_task_finishes(tmp_path, monkeypatch):
    monkeypatch.setattr(execution,'ProcessPoolExecutor',TestPool)
    observed=[]
    database=tmp_path/'queue'
    def worker(item, task, settings, service_identity=None):
        if task.task_id=='slow':
            until=time.time()+3
            while time.time()<until:
                with sqlite3.connect(database) as db:
                    state=db.execute("SELECT status FROM tasks WHERE source_id='fast'").fetchone()[0]
                if state=='recorded':
                    observed.append(state);break
                time.sleep(.01)
        result={'id':task.task_id,'trace_complete':True,'generation_started':1,'termination':'submitted'}
        execution.save_receipt(item,result)
        return result
    monkeypatch.setattr(execution,'execute',worker)
    with CollectionQueue(database) as queue:
        admit(queue,tmp_path,'fast');admit(queue,tmp_path,'slow')
        outcome=execution.dispatch(queue,settings=None,verify=job,concurrency=2,deadline=time.time()+10)
        assert outcome['reason']=='exhausted'
        assert queue.counts()=={'recorded':2}
        assert observed==['recorded']


def test_failure_circuit_stops_pending_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(execution,'ProcessPoolExecutor',TestPool)
    def worker(item, task, settings, service_identity=None):
        result={'id':task.task_id,'trace_complete':False,'generation_started':0,'termination':'error'}
        execution.save_receipt(item,result)
        return result
    monkeypatch.setattr(execution,'execute',worker)
    with CollectionQueue(tmp_path/'q') as queue:
        for name in ('a','b','c'):admit(queue,tmp_path,name)
        result=execution.dispatch(queue,settings=None,verify=job,concurrency=1,deadline=time.time()+10,failure_limit=1)
        assert result['reason']=='infrastructure_failure_limit'
        assert queue.counts()=={'pending':2,'recorded':1}


def test_deadline_and_preflight_do_not_claim_unstarted_tasks(tmp_path, monkeypatch):
    monkeypatch.setattr(execution,'ProcessPoolExecutor',TestPool)
    with CollectionQueue(tmp_path/'q') as queue:
        admit(queue,tmp_path,'a')
        result=execution.dispatch(queue,settings=None,verify=job,concurrency=1,deadline=time.time()-1)
        assert result['reason']=='campaign_deadline' and queue.counts()=={'pending':1}
        def invalid(item):raise ValueError('frozen input changed')
        result=execution.dispatch(queue,settings=None,verify=invalid,concurrency=1,deadline=time.time()+10)
        assert result['reason']=='preflight_or_capacity_failed' and queue.counts()=={'pending':1}


def test_unresolved_task_never_gets_submitted_again(tmp_path, monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('must not start a worker')
    monkeypatch.setattr(execution,'ProcessPoolExecutor',forbidden)
    with CollectionQueue(tmp_path/'q') as queue:
        admit(queue,tmp_path,'a');queue.claim()
        result=execution.dispatch(queue,settings=None,verify=job,concurrency=1,deadline=time.time()+10)
        assert result['reason']=='unresolved_running'


def test_service_failure_circuit_survives_process_restart(tmp_path,monkeypatch):
    monkeypatch.setattr(execution,'ProcessPoolExecutor',TestPool)
    with CollectionQueue(tmp_path/'q') as queue:
        admit(queue,tmp_path,'a')
        queue.db.execute('CREATE TABLE operational (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
        queue.db.execute("INSERT INTO operational VALUES ('failure_streak','3')")
    with CollectionQueue(tmp_path/'q') as queue:
        result=execution.dispatch(queue,settings=None,verify=job,concurrency=1,deadline=time.time()+10)
        assert result['reason']=='infrastructure_failure_limit' and queue.counts()=={'pending':1}


def test_real_process_exit_after_receipt_recovers_once(tmp_path):
    import subprocess
    import sys
    database=tmp_path/'q'
    with CollectionQueue(database) as queue:admit(queue,tmp_path,'a')
    code='''import os,sys
from rwkv_lh.collection_queue import CollectionQueue
from rwkv_lh.collection_execution import save_receipt
with CollectionQueue(sys.argv[1]) as queue:
 item=queue.claim()
 save_receipt(item, {'id':item['job']['task_id'],'trace_complete':True,'generation_started':1})
 os._exit(9)
'''
    process=subprocess.run([sys.executable,'-c',code,str(database)],check=False)
    assert process.returncode==9
    with CollectionQueue(database) as queue:
        assert queue.counts()=={'running':1}
        assert execution.reconcile(queue)==0
        assert queue.counts()=={'recorded':1} and queue.claim() is None


def test_collection_worker_captures_generation_boundary(tmp_path,monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(execution,'service_fingerprint',lambda settings:{'identity':'frozen'})
    monkeypatch.setattr(execution,'evaluate_artifact',lambda item,result:{'status':'pending_manual_review'})
    events=[]
    def session(*,settings,audit_hook):
        audit_hook({'type':'model_session_generation_started','request_id':'test-request',
                    'input_checkpoint_id':'test-checkpoint','input_digest':'a'*64})
        return object()
    monkeypatch.setattr(execution,'create_model_session',session)
    def run(task,*,settings,session_factory):
        workspace=Path(task.output_dir)/'workspace';workspace.mkdir(parents=True)
        (workspace/'source.txt').write_text('actual before bytes')
        session_factory(settings=settings,audit_hook=events.append)
        return {'id':task.task_id,'trace_complete':True,'generation_started':1,'termination':'submitted'}
    monkeypatch.setattr(execution,'run_coding_job',run)
    with CollectionQueue(tmp_path/'q') as queue:
        item=admit(queue,tmp_path,'a');task=job(item)
        execution.execute(item,task,None,{'identity':'frozen'})
    assert events[0]['type']=='correction_generation_snapshot_saved'
    assert events[1]['type']=='model_session_generation_started'
    assert (tmp_path/'a/execution/generation_snapshots/test-request/before/source.txt').read_text()=='actual before bytes'


def test_storage_retirement_failure_stops_further_dispatch(tmp_path,monkeypatch):
    monkeypatch.setattr(execution,'ProcessPoolExecutor',TestPool)
    def worker(item,task,settings,service_identity=None):
        result={'id':task.task_id,'trace_complete':True,'storage_retirement':{'status':'failed'}}
        execution.save_receipt(item,result)
        return result
    monkeypatch.setattr(execution,'execute',worker)
    with CollectionQueue(tmp_path/'q') as queue:
        for name in ('first','next'):admit(queue,tmp_path,name)
        outcome=execution.dispatch(queue,settings=None,verify=job,concurrency=1,deadline=time.time()+10)
        assert outcome['reason']=='storage_retirement_failed'
        assert queue.counts()=={'recorded':1,'pending':1}
