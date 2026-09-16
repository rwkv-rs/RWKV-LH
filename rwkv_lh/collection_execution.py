"""Bounded collection dispatch with durable per-task receipts and no teacher."""
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from dataclasses import replace
from multiprocessing import get_context
from pathlib import Path
import hashlib
import json
import os
import time
import signal

from .collection_queue import _json
from .coding_agent import run_coding_job
from .read_only_agent import run_read_only_job
from .correction_snapshots import generation_snapshot_audit
from .model_session import create_model_session
from .collection_acceptance import evaluate_artifact
from .runtime.openai_compat import OpenAICompatibleRWKVClient


def service_fingerprint(settings):
    data, _, _ = OpenAICompatibleRWKVClient(settings)._request_json('GET', '/capabilities')
    state = data.get('recurrent_state', {})
    if (data.get('model') != settings.model or not state.get('create')
            or not state.get('full_input_token_ids') or not state.get('request_recovery')
            or '+native.' not in str(data.get('server_build', ''))
            or not data.get('tokenizer_build') or data.get('error')):
        raise ValueError('ready attested Native service with exact token evidence required')
    if settings.max_model_len > data.get('max_model_len', 0):
        raise ValueError('registered context exceeds server capacity')
    return {key: data[key] for key in ('model','server_build','tokenizer_build','max_model_len')}


def _receipt_path(item):
    return Path(item['job']['output_dir']) / 'COLLECTION_RECEIPT.json'


def save_receipt(item, result):
    if result.get('id') != item['job']['task_id']:
        raise ValueError('receipt task identity mismatch')
    path = _receipt_path(item)
    path.parent.mkdir(parents=True, exist_ok=True)
    value = {'source_id': item['source_id'],
             'payload_sha256': hashlib.sha256(_json(item).encode()).hexdigest(),
             'result_sha256': hashlib.sha256(_json(result).encode()).hexdigest(),
             'result': result}
    temporary = path.with_suffix('.pending')
    with temporary.open('x') as stream:
        stream.write(_json(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def reconcile(queue):
    """Recover completed receipts only; absent/partial receipts stay unresolved."""
    for item in list(queue.items('running')):
        path = _receipt_path(item)
        if not path.exists():
            continue
        receipt = json.loads(path.read_text())
        if (receipt['source_id'] != item['source_id']
                or receipt['payload_sha256'] != hashlib.sha256(_json(item).encode()).hexdigest()
                or receipt['result_sha256'] != hashlib.sha256(_json(receipt['result']).encode()).hexdigest()):
            raise ValueError('receipt identity or digest mismatch')
        queue.finish(item['source_id'], receipt['result'])
    return queue.counts().get('running', 0)


def execute(item, job, settings, service_identity=None):
    output = Path(job.output_dir)
    coding = item['job']['tool_scope'] == 'coding'
    workspace = output / 'workspace' if coding else Path(job.workspace)
    evidence = output / 'execution' if coding else output
    def session_factory(*, settings, audit_hook):
        return create_model_session(settings=settings, audit_hook=generation_snapshot_audit(
            workspace=workspace, output=evidence, audit_hook=audit_hook))
    try:
        if service_identity is None or service_fingerprint(settings) != service_identity:
            raise ValueError('service identity differs from campaign freeze')
        result = (run_coding_job if coding else run_read_only_job)(
            job, settings=settings, session_factory=session_factory)
    except Exception as exc:
        result = {'id': job.task_id, 'termination': 'error',
                  'termination_reason': 'collection_worker_failed', 'trace_complete': False,
                  'generation_started': None, 'acceptance': 'unreviewable',
                  'error': {'type': type(exc).__name__, 'message': str(exc)}}
    result['collection_service'] = {'base_url': getattr(settings, 'base_url', None),
                                    'identity': service_identity}
    result["external_acceptance"] = {"status": "pending_verification"}
    save_receipt(item, result)
    def expired(signum, frame):
        raise TimeoutError("external verification exceeded 30 seconds")
    previous = signal.signal(signal.SIGALRM, expired)
    old_timer = signal.setitimer(signal.ITIMER_REAL, 30)
    try:
        result["external_acceptance"] = evaluate_artifact(item, result)
    except Exception as exc:
        result["external_acceptance"] = {"status": "unreviewable", "error": str(exc)}
    finally:
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        signal.signal(signal.SIGALRM, previous)
    save_receipt(item, result)
    return result


def dispatch(queue, *, settings, verify, concurrency, deadline, failure_limit=3,
             capacity_check=lambda: None, service_identity=None, replicas=None):
    """Drain in-flight work at cutoff; no newly queued work after an infra fault."""
    services = list(replicas) if replicas is not None else [(settings, service_identity)]
    if not services or concurrency < len(services):
        raise ValueError('each replica requires at least one worker slot')
    # A slot owns one endpoint for the entire task. State is never migrated
    # between services, and a model failure still advances to the next task.
    free_slots = list(range(concurrency))
    if reconcile(queue):
        return {'reason': 'unresolved_running', 'counts': queue.counts()}
    queue.db.execute('CREATE TABLE IF NOT EXISTS operational (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
    saved = queue.db.execute("SELECT value FROM operational WHERE name='failure_streak'").fetchone()
    failures = int(saved[0]) if saved else 0
    if failures >= failure_limit:
        return {'reason': 'infrastructure_failure_limit', 'counts': queue.counts()}
    reason = 'exhausted'
    failure_detail = None
    with ProcessPoolExecutor(max_workers=concurrency, mp_context=get_context('spawn')) as pool:
        active = {}
        stop = False
        while active or not stop:
            while not stop and len(active) < concurrency:
                if time.time() >= deadline:
                    reason, stop = 'campaign_deadline', True
                    break
                try:
                    capacity_check()
                    prepared = []
                    def preflight(value):
                        prepared.append(verify(value))
                    item = queue.claim(verify=preflight)
                except Exception as exc:
                    failure_detail = {'stage':'preflight', 'type':type(exc).__name__, 'message':str(exc)}
                    reason, stop = 'preflight_or_capacity_failed', True
                    break
                if item is None:
                    stop = True
                    break
                try:
                    # Frozen bytes were checked before claim, outside model input construction.
                    job = prepared[0]
                    remaining = max(0.001, deadline - time.time())
                    job = replace(job, max_seconds=min(job.max_seconds, remaining))
                    slot = free_slots.pop(0)
                    task_settings, task_identity = services[slot % len(services)]
                    active[pool.submit(execute, item, job, task_settings, task_identity)] = (item, slot)
                except Exception as exc:
                    failure_detail = {'stage':'dispatch', 'source_id':item['source_id'], 'type':type(exc).__name__, 'message':str(exc)}
                    reason, stop = 'dispatch_outcome_unknown', True
                    break
            if not active:
                break
            done, _ = wait(active, return_when=FIRST_COMPLETED)
            for future in done:
                item, slot = active.pop(future)
                free_slots.append(slot)
                try:
                    result = future.result()
                    queue.finish(item['source_id'], result)
                    failures = failures + 1 if result.get('trace_complete') is not True else 0
                    queue.db.execute("INSERT OR REPLACE INTO operational VALUES ('failure_streak', ?)", (str(failures),))
                except Exception as exc:
                    failure_detail = {'stage':'worker_or_receipt', 'source_id':item['source_id'], 'type':type(exc).__name__, 'message':str(exc)}
                    reason, stop = 'worker_or_receipt_outcome_unknown', True
                    continue
                if failures >= failure_limit:
                    reason, stop = 'infrastructure_failure_limit', True
            print(_json({'counts': queue.counts(), 'stop_reason': reason if stop else None}), flush=True)
    if queue.counts().get('running', 0):
        reason = 'unresolved_running'
    queue.db.execute("INSERT OR REPLACE INTO operational VALUES ('last_stop', ?)",
                     (_json({'reason': reason, 'time': time.time(), 'error':failure_detail}),))
    return {'reason': reason, 'counts': queue.counts(), 'error':failure_detail}
