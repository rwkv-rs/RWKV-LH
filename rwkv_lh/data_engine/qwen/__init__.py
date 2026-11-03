"""Asynchronous teacher scheduling with durable reservations and conservative recovery."""
import asyncio
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import uuid
import requests


class TeacherUnavailable(RuntimeError):
    pass


class TeacherPool:
    """One event-loop owned pool. HTTP and the production loop run in worker threads.

    A sending row surviving a crash is uncertain, never automatically replayed.
    A completed response is cached by content and request key, so resume neither
    loses its response nor submits it twice. Unknown spend keeps its reservation.
    """
    def __init__(self, provider, database, *, max_requests=None, max_tokens=None):
        self.provider = dict(provider)
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.max_requests, self.max_tokens = max_requests, max_tokens
        self.ceiling = provider['max_concurrency']
        if type(self.ceiling) is not int or self.ceiling < 1:
            raise ValueError('positive teacher concurrency required')
        # All campaigns using this endpoint/key share transport slots. A worker
        # keeps its flock until HTTP actually returns, including after coroutine
        # cancellation; process death releases the lease automatically.
        quota_id = hashlib.sha256(json.dumps([provider['base_url'].rstrip('/'),
            str(Path(provider['key_file']).resolve())]).encode()).hexdigest()
        self.quota_root = Path(provider.get('quota_directory', Path.home()/'.cache/rwkv-lh/teacher-quota')) / quota_id
        self.quota_root.mkdir(parents=True, exist_ok=True)
        self.limit, self.active, self.successes = self.ceiling, 0, 0
        self.waiters, self.sequence = [], 0
        self.condition = asyncio.Condition()
        self.rates = []
        self.key_locks = {}
        with self.db() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, input_sha TEXT NOT NULL, state TEXT NOT NULL, reserved INTEGER NOT NULL, response TEXT, usage TEXT, attempts INTEGER NOT NULL DEFAULT 0, error TEXT, created REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, request_key TEXT, state TEXT, status INTEGER, usage TEXT, started REAL, ended REAL)')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.database, timeout=60)
        db.execute('PRAGMA journal_mode=WAL')
        try:
            with db:
                yield db
        finally:
            db.close()

    async def _enter(self, priority, reservation):
        async with self.condition:
            self.sequence += 1
            ticket = (priority, self.sequence)
            self.waiters.append(ticket)
            try:
                while True:
                    now = time.time()
                    self.rates = [(t,n) for t,n in self.rates if t > now - 60]
                    rpm, tpm = self.provider.get('rpm'), self.provider.get('tpm')
                    ready = ((not rpm or len(self.rates)<rpm) and (not tpm or sum(n for _,n in self.rates)+reservation<=tpm))
                    if self.active < self.limit and ticket == min(self.waiters) and ready:
                        self.active += 1
                        self.rates.append((now, reservation))
                        return
                    try: await asyncio.wait_for(self.condition.wait(), 1)
                    except asyncio.TimeoutError: pass
            finally:
                self.waiters.remove(ticket)

    async def _leave(self, good):
        async with self.condition:
            self.active -= 1
            if good:
                self.successes += 1
                if self.successes >= self.limit:
                    self.limit = min(self.ceiling, self.limit + 1)
                    self.successes = 0
            else:
                self.limit = max(1, self.limit // 2)
                self.successes = 0
            self.condition.notify_all()

    def _http(self, body, key):
        # Credentials are read at the transport boundary and never enter request
        # journals, task workspaces, errors, or model-visible messages.
        secret = Path(self.provider['key_file']).read_text().strip()
        with requests.Session() as session:
            session.trust_env = False
            response = session.post(self.provider['base_url'].rstrip('/')+'/chat/completions',
                headers={'Authorization':'Bearer '+secret,'Idempotency-Key':key}, json=body,
                timeout=(15,self.provider.get('timeout_seconds',180)))
            try: value = response.json()
            except ValueError: value = {'error':{'code':'non_json_response'}}
            return response.status_code, value

    def _bounded_http(self, body, key):
        while True:
            for index in range(self.ceiling):
                with (self.quota_root / f'{index}.lock').open('a') as lease:
                    try:
                        fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    try:
                        return self._http(body, key)
                    finally:
                        fcntl.flock(lease, fcntl.LOCK_UN)
            time.sleep(.05)

    async def complete(self, messages, *, key, lane='continuation', max_output_tokens=8192, tools=None,
                       generation_options=None):
        lock = self.key_locks.setdefault(key, asyncio.Lock())
        async with lock:
            return await self._complete(messages,key=key,lane=lane,max_output_tokens=max_output_tokens,
                                        tools=tools,generation_options=generation_options)

    async def _complete(self, messages, *, key, lane, max_output_tokens, tools, generation_options=None):
        if lane not in ('correction','continuation','task_generation'): raise ValueError('unknown teacher lane')
        body={'model':self.provider['model'],'messages':messages,'max_tokens':max_output_tokens,'temperature':0}
        allowed = ('reasoning_effort','reasoning_budget_tokens','temperature','top_p','top_k')
        if generation_options is not None and (not isinstance(generation_options,dict)
                or any(key not in allowed for key in generation_options)):
            raise ValueError('unsupported generation option')
        for option in allowed:
            if option in self.provider:
                body[option] = self.provider[option]
        body.update(generation_options or {})
        if tools is not None: body.update(tools=tools,tool_choice='auto',parallel_tool_calls=True)
        encoded=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        identity=hashlib.sha256(encoded.encode()).hexdigest()
        reservation=len(encoded.encode())+max_output_tokens
        if self.provider.get('tpm') and reservation>self.provider['tpm']:
            raise ValueError('one complete request exceeds TPM; input was not truncated')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT input_sha,state,response FROM requests WHERE key=?',(key,)).fetchone()
            if row:
                if row[0]!=identity: raise ValueError('idempotency key reused with different input')
                if row[1]=='done': return json.loads(row[2])
                if row[1] in ('sending','uncertain'): raise TeacherUnavailable('request outcome is uncertain; no automatic replay')
                if row[1]=='failed': raise TeacherUnavailable('provider previously rejected this request')
            else:
                count,total=db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM requests').fetchone()
                if self.max_requests is not None and count>=self.max_requests: raise TeacherUnavailable('request cap reached')
                if self.max_tokens is not None and total+reservation>self.max_tokens: raise TeacherUnavailable('token cap reached')
                db.execute('INSERT INTO requests(key,input_sha,state,reserved,created) VALUES(?,?,?,?,?)',(key,identity,'queued',reservation,time.time()))
        priority={'correction':0,'continuation':1,'task_generation':2}[lane]
        for attempt in range(4):
            await self._enter(priority,reservation)
            attempt_id=uuid.uuid4().hex
            with self.db() as db:
                db.execute('BEGIN IMMEDIATE')
                attempts,total=db.execute('SELECT coalesce(sum(attempts),0),coalesce(sum(reserved),0) FROM requests').fetchone()
                capped = ((self.max_requests is not None and attempts>=self.max_requests)
                    or (attempt>0 and self.max_tokens is not None and total+reservation>self.max_tokens))
                if not capped and attempt>0:
                    db.execute('UPDATE requests SET reserved=reserved+? WHERE key=?',(reservation,key))
            if capped:
                await self._leave(False)
                raise TeacherUnavailable('attempt budget cap reached')
            with self.db() as db:
                db.execute("UPDATE requests SET state='sending',attempts=attempts+1 WHERE key=?",(key,))
                db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',(attempt_id,key,'sending',None,None,time.time(),None))
            status,value=None,None
            try:
                status,value=await asyncio.to_thread(self._bounded_http,body,key)
            except BaseException as exc:
                with self.db() as db:
                    db.execute("UPDATE requests SET state='uncertain',error=? WHERE key=?",(type(exc).__name__,key))
                    db.execute("UPDATE attempts SET state='uncertain',ended=? WHERE id=?",(time.time(),attempt_id))
                raise TeacherUnavailable('teacher transport outcome uncertain: '+type(exc).__name__) from None
            finally:
                await self._leave(status==200)
            good=status==200 and isinstance(value.get('choices'),list) and bool(value['choices'])
            usage=value.get('usage')
            with self.db() as db:
                db.execute('UPDATE attempts SET state=?,status=?,usage=?,ended=? WHERE id=?',
                    ('done' if good else 'rejected',status,json.dumps(usage),time.time(),attempt_id))
                if good:
                    db.execute("UPDATE requests SET state='done',response=?,usage=? WHERE key=?",(json.dumps(value),json.dumps(usage),key))
                    return value
                error=value.get('error') or {}
                code=error.get('code') if isinstance(error,dict) else 'provider_error'
                retry=status in (429,500,502,503,504) and code not in ('model_not_found','invalid_api_key') and attempt<3
                db.execute('UPDATE requests SET state=?,error=? WHERE key=?',('retry' if retry else 'failed',f'HTTP {status}: {code}',key))
            if not retry: raise TeacherUnavailable(f'{self.provider["id"]}: HTTP {status}: {code}')
            await asyncio.sleep(min(8,2**attempt))

    def status(self):
        with self.db() as db:
            rows=db.execute('SELECT state,count(*),sum(reserved) FROM requests GROUP BY state').fetchall()
            usage=[json.loads(x[0]) for x in db.execute("SELECT usage FROM requests WHERE state='done' AND usage IS NOT NULL")]
        return {'provider':self.provider['id'],'model':self.provider['model'],'concurrency':self.limit,
            'requests':{s:n for s,n,_ in rows},'reserved_tokens':sum(n for _,_,n in rows),
            'reported_tokens':sum((u or {}).get('total_tokens',0) for u in usage),
            'cost':None,'cost_status':'provider prices not supplied; usage and unknown reservations retained'}
