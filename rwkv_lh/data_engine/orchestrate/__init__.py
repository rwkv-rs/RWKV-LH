"""Durable task campaigns on the production loop, with one shared teacher pool."""
import asyncio
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import multiprocessing
from pathlib import Path
import secrets
import sqlite3
import threading
import time
import traceback

from rwkv_lh.data_engine.qwen import TeacherPool
from rwkv_lh.data_engine.tasks import load_task, dump, checksum
from rwkv_lh.evaluation_policy import assert_training_source_allowed, assert_training_record_allowed


class Queue:
    def __init__(self, path):
        self.path = Path(path)
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, state TEXT NOT NULL, attempt INTEGER NOT NULL DEFAULT 0, provider TEXT, result TEXT)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=60)
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def populate(self, count):
        with self.db() as db:
            db.executemany("INSERT OR IGNORE INTO jobs(id,state) VALUES(?,'queued')", ((i,) for i in range(count)))

    def claim(self, provider):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute("SELECT id,attempt,state FROM jobs WHERE state IN ('queued','resume') ORDER BY attempt,id LIMIT 1").fetchone()
            if not row:
                return None
            attempt = row[1] + (row[2] == 'queued')
            db.execute("UPDATE jobs SET state='active',attempt=?,provider=? WHERE id=?", (attempt,provider,row[0]))
            return row[0], attempt

    def finish(self, index, result, max_attempts):
        with self.db() as db:
            attempt = db.execute('SELECT attempt FROM jobs WHERE id=?', (index,)).fetchone()[0]
            state = ('done' if result.get('export') else 'uncertain' if result.get('uncertain')
                     else 'failed' if attempt >= max_attempts else 'queued')
            db.execute('UPDATE jobs SET state=?,result=? WHERE id=?', (state,json.dumps(result),index))

    def reconcile(self, root, tasks, max_attempts):
        """Resume only confirmed boundaries. Unknown effects stay recorded, never replayed."""
        from rwkv_lh.project_ledger import ProjectLedger
        with self.db() as db:
            active = db.execute("SELECT id,attempt FROM jobs WHERE state='active'").fetchall()
        for index, attempt in active:
            run = Path(root) / 'runs' / f'{tasks[index]["id"]}-a{attempt:02d}'
            if (run / 'ENGINE_RESULT.json').exists():
                self.finish(index,json.loads((run/'ENGINE_RESULT.json').read_text()),max_attempts)
                continue
            state = 'resume'
            if (run/'execution/project.sqlite3').exists():
                with ProjectLedger.read_snapshot(run/'execution') as ledger:
                    if ledger.scan_verified_events()['state']['pending']:
                        state = 'uncertain'
            elif run.exists():
                state = 'uncertain'
            with self.db() as db:
                db.execute('UPDATE jobs SET state=? WHERE id=?', (state,index))

    def counts(self):
        with self.db() as db:
            return dict(db.execute('SELECT state,count(*) FROM jobs GROUP BY state').fetchall())


def run_episode(root, task, attempt, broker, provider):
    """A process main thread owns the production deadline and isolated tools."""
    from rwkv_lh.data_engine.verify import admit,verify
    from rwkv_lh.data_engine.build import export_episode
    from rwkv_lh.data_engine.records import record_episode
    from rwkv_lh.data_engine.rollout import BrokerPolicy
    from rwkv_lh.project_agent import run_project_job, resume_project, continue_project
    from rwkv_lh.project_ledger import ProjectLedger
    from rwkv_lh.agent_jobs import CodingJob
    from rwkv_lh.runtime.settings import RuntimeSettings
    root = Path(root)
    directory = root/'tasks'/task['id']
    episode = f'{task["id"]}-a{attempt:02d}'
    run = root/'runs'/episode
    row = {'task':task['id'],'attempt':attempt,'provider':provider['id'],'model':provider['model']}
    try:
        if (directory/'ADMISSION.json').exists():
            record = json.loads((directory/'ADMISSION.json').read_text())
            if record['task_digest'] != task['digest'] or not record['admitted']:
                raise ValueError('task admission identity changed or rejected')
        else:
            admit(task,directory)
        port = BrokerPolicy(broker,provider,episode=episode,max_output_tokens=16384)
        settings = RuntimeSettings(base_url='http://127.0.0.1:1/v1',model='offline-round0',api_key='')
        if (run/'execution/project.sqlite3').exists():
            result = resume_project(run,settings=settings,agent_port=port)
        else:
            result = run_project_job(CodingJob(task['id'],task['request'],str(directory/'seed'),str(run),
                task['max_calls'],task['max_seconds'],record_generation_snapshots=True,
                protected_paths=tuple(task['protected_paths'])),settings=settings,agent_port=port)
        with ProjectLedger.read_snapshot(run/'execution') as ledger:
            state = ledger.scan_verified_events()['state']
        if task.get('followups') and len(state['requests']) == 1 and state['status'] == 'finished':
            first = verify({**task,'acceptance':task['first_acceptance']}, run/'workspace',root/'verification'/(episode+'-first'))
            if first['passed']:
                result = continue_project(run,task['followups'][0],settings=settings,agent_port=port)
        verdict = verify(task,run/'workspace',root/'verification'/episode)
        with ProjectLedger.read_snapshot(run/'execution') as ledger:
            state = ledger.scan_verified_events()['state']
        strict = (verdict['passed'] and result.get('status') == 'finished'
                  and result['termination_reason'] == 'model_finished' and not state['pending']
                  and not state['inbox'] and len(state['requests']) == 1+len(task.get('followups',[])))
        row.update(Strict=bool(strict),completed=verdict['passed'],mutation=result.get('mutation_count',0),
            termination_reason=result['termination_reason'],model_calls=state['calls'],
            user_requests=len(state['requests']),changed_files=result['changed_files'])
        row['record'] = record_episode(task, run, verdict=verdict)
        if strict:
            row['export'] = export_episode(task,run,verdict,root/'production',root/'exports',teacher=provider)
        (run/'ENGINE_RESULT.json').write_text(dump(row))
    except BaseException as exc:
        row.update(error=type(exc).__name__,detail=str(exc),traceback=traceback.format_exc())
        if (run/'execution/project.sqlite3').exists():
            with ProjectLedger.read_snapshot(run/'execution') as ledger:
                row['uncertain'] = bool(ledger.state()['pending'])
            try:
                row['record'] = record_episode(task, run)
            except (ValueError, OSError) as archive_error:
                row['archive_error'] = str(archive_error)
        run.mkdir(parents=True,exist_ok=True)
        (run/'ENGINE_RESULT.json').write_text(dump(row))
    return row


def load_manifest(path):
    path = Path(path).resolve(strict=True)
    assert_training_source_allowed(path)
    manifest = json.loads(path.read_text())
    assert_training_record_allowed(manifest)
    tasks = []
    for item in manifest['tasks']:
        source = (path.parent/item['path']).resolve(strict=True)
        assert_training_source_allowed(source)
        if hashlib.sha256(source.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('task file differs from frozen manifest')
        task = load_task(source)
        assert_training_record_allowed(task)
        tasks.append(task)
    if len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('duplicate task identity')
    return tasks


async def campaign(root, providers, *, tasks_manifest, count=None, workers=32, max_attempts=3):
    tasks = load_manifest(tasks_manifest)
    if count is not None:
        tasks = tasks[:count]
    if not tasks:
        raise ValueError('nonempty frozen task manifest required')
    root = Path(root);root.mkdir(parents=True,exist_ok=True)
    assert_training_source_allowed(root)
    public = [{k:v for k,v in p.items() if k in ('id','model','base_url','max_concurrency',
        'reasoning_effort','reasoning_budget_tokens','temperature','top_p','top_k')} for p in providers]
    registration = {'tasks':{t['id']:t['digest'] for t in tasks},'workers':workers,'max_attempts':max_attempts,
        'providers':public,'tasks_manifest_sha256':hashlib.sha256(Path(tasks_manifest).read_bytes()).hexdigest(),
        'owner_instruction':'Prepare 2000 diverse project-level verified SFT trajectories in the existing harness; no task budget; local API ceiling 32.',
        'training_started':False,'new_optimizer_updates':0}
    path = root/'REGISTRATION.json'
    if path.exists() and json.loads(path.read_text()) != registration:
        raise ValueError('campaign registration changed; use a new campaign')
    path.write_text(dump(registration))
    pools = {p['id']:TeacherPool(p,root/'teachers'/(p['id']+'.sqlite3')) for p in providers}
    queue = Queue(root/'queue.sqlite3');queue.populate(len(tasks));queue.reconcile(root,tasks,max_attempts)
    loop = asyncio.get_running_loop()
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_POST(self):
            if self.headers.get('Authorization') != 'Bearer '+token:
                self.send_error(403);return
            status = 200
            try:
                size = int(self.headers['Content-Length'])
                if not 0<size<20*1024*1024:raise ValueError('invalid request size')
                body = json.loads(self.rfile.read(size))
                future = asyncio.run_coroutine_threadsafe(pools[body['provider']].complete(body['messages'],key=body['key'],
                    max_output_tokens=body['max_output_tokens'],tools=body.get('tools')),loop)
                value = future.result()
            except Exception as exc:
                value = {'error':type(exc).__name__+': '+str(exc)};status=503
            raw = json.dumps(value).encode()
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers()
            try:self.wfile.write(raw)
            except (BrokenPipeError,ConnectionResetError):pass
    server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    broker = {'url':f'http://127.0.0.1:{server.server_port}/complete','token':token}
    started = time.time()
    async def monitor():
        while True:
            report = {'time':time.time(),'elapsed_seconds':time.time()-started,'jobs':queue.counts(),'teachers':[p.status() for p in pools.values()]}
            (root/'STATUS.json').write_text(dump(report))
            print(json.dumps({'event':'status','jobs':report['jobs'],'elapsed_seconds':round(report['elapsed_seconds'])}),flush=True)
            await asyncio.sleep(30)
    monitoring = asyncio.create_task(monitor())
    try:
        with ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as executor:
            async def worker(provider):
                while (claimed:=queue.claim(provider['id'])) is not None:
                    index,attempt = claimed
                    row = await loop.run_in_executor(executor,run_episode,str(root),tasks[index],attempt,broker,provider)
                    queue.finish(index,row,max_attempts)
                    with (root/'RESULTS.jsonl').open('a') as stream:stream.write(json.dumps(row,ensure_ascii=False)+'\n')
                    print(json.dumps({'event':'episode',**{k:row.get(k) for k in ('task','attempt','provider','Strict','completed','termination_reason','error')}}),flush=True)
            await asyncio.gather(*(worker(public[i%len(public)]) for i in range(workers)))
    finally:
        monitoring.cancel()
        server.shutdown();server.server_close();thread.join(timeout=5)
    result = {'jobs':queue.counts(),'teachers':[p.status() for p in pools.values()],'elapsed_seconds':time.time()-started}
    (root/'FINAL_STATUS.json').write_text(dump(result))
    return result
