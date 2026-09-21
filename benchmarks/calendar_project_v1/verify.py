"""Private black-box program; run only through benchmark_verifier isolation."""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

root = Path(sys.argv[1])
results = []
process = None
work = Path(tempfile.mkdtemp(prefix='calendar-check-'))
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
base = f'http://127.0.0.1:{port}'
log = (work / 'server.log').open('w+')

def start():
    return subprocess.Popen([sys.executable, str(root / 'app.py'), '--host', '127.0.0.1',
        '--port', str(port), '--db', str(work / 'calendar.sqlite3')], cwd=root, stdout=log, stderr=log)

def request(method, path, payload=None):
    raw = None if payload is None else json.dumps(payload).encode()
    try:
        response = urlopen(Request(base+path, data=raw, method=method,
            headers={'Content-Type':'application/json'}), timeout=3)
    except HTTPError as exc:
        response = exc
    with response:
        body = response.read()
        return response.status, json.loads(body) if body else None

def ready():
    for _ in range(80):
        try:
            if request('GET','/api/health') == (200, {'ok':True}): return
        except Exception: pass
        if process.poll() is not None: break
        time.sleep(.1)
    raise AssertionError('application did not become healthy')

def check(name, fn, available=True):
    if not available:
        results.append({'check':name,'passed':False,'status':'blocked_by_startup'}); return
    try:
        fn(); results.append({'check':name,'passed':True,'status':'passed'})
    except Exception as exc:
        results.append({'check':name,'passed':False,'status':'failed','error':str(exc)[:400] or type(exc).__name__})

def expect(status, value, expected):
    assert status==expected, (status,value)
    return value

def event(title, start='2026-10-05T09:00:00Z', end='2026-10-05T10:00:00Z', **extra):
    return dict(calendar_id=calendar['id'], title=title, start=start, end=end,
                description='release planning', location='Room A', **extra)

try:
    process=start()
    check('startup_and_health',ready)
    available=results[-1]['passed']
    def files():
        assert (root/'app.py').is_file()
        assert list(root.rglob('*.html')) and list(root.rglob('*.js')), 'separate HTML/JS missing'
        assert (root/'README.md').is_file(), 'README missing'
    check('project_structure',files)
    calendar={}; second={}; created={}
    def calendars():
        calendar.update(expect(*request('POST','/api/calendars',{'name':'Work R38','color':'#2563eb'}),201))
        second.update(expect(*request('POST','/api/calendars',{'name':'Personal R38','color':'#16a34a'}),201))
        values=expect(*request('GET','/api/calendars'),200)
        assert {calendar['id'],second['id']} <= {r['id'] for r in values}
    check('calendar_create_list',calendars,available)
    usable=available and bool(calendar) and bool(second)
    def crud():
        created.update(expect(*request('POST','/api/events',event('Planning')),201))
        path='/api/events/'+str(created['id'])
        assert expect(*request('GET',path),200)['title']=='Planning'
        assert expect(*request('PUT',path,event('Updated planning')),200)['title']=='Updated planning'
        status,_=request('DELETE',path); assert status in (200,204)
        assert request('GET',path)[0]==404
    check('event_crud',crud,usable)
    def invalid():
        before=expect(*request('GET','/api/events'),200)
        cases=[{'title':'  '},{'start':'wrong'},{'start':'2026-10-05T09:00:00'},
               {'end':'2026-10-05T08:00:00Z'},{'calendar_id':-999},{'repeat_weekly':13}]
        for update in cases:
            payload=event('invalid'); payload.update(update)
            assert request('POST','/api/events',payload)[0]==400, update
        assert expect(*request('GET','/api/events'),200)==before
    check('invalid_input_atomicity',invalid,usable)
    def conflicts():
        expect(*request('POST','/api/events',event('Conflict anchor')),201)
        assert request('POST','/api/events',event('Overlap','2026-10-05T09:30:00Z','2026-10-05T10:30:00Z'))[0]==409
        expect(*request('POST','/api/events',event('Adjacent','2026-10-05T10:00:00Z','2026-10-05T11:00:00Z')),201)
        p=event('Other calendar');p['calendar_id']=second['id'];expect(*request('POST','/api/events',p),201)
    check('conflict_and_adjacent_intervals',conflicts,usable)
    def filters():
        from urllib.parse import urlencode
        query=urlencode({'start':'2026-10-05T08:00:00Z','end':'2026-10-05T10:00:00Z','calendar_id':calendar['id'],'q':'ANCHOR'})
        values=expect(*request('GET','/api/events?'+query),200)
        assert len(values)==1 and values[0]['title']=='Conflict anchor',values
    check('combined_range_calendar_search',filters,usable)
    def timezone():
        p=event('Offset','2026-10-05T17:30:00+08:00','2026-10-05T18:00:00+08:00')
        assert request('POST','/api/events',p)[0]==409
        p=event('All day','2026-10-07T00:00:00Z','2026-10-08T00:00:00Z',all_day=True)
        assert expect(*request('POST','/api/events',p),201)['all_day'] is True
    check('timezone_and_all_day',timezone,usable)
    def recurrence():
        p=event('Weekly','2026-10-12T13:00:00Z','2026-10-12T14:00:00Z',repeat_weekly=2)
        values=expect(*request('POST','/api/events',p),201)['events'];assert len(values)==3
        from datetime import datetime
        times=sorted(datetime.fromisoformat(v['start'].replace('Z','+00:00')) for v in values)
        assert [(times[i+1]-times[i]).days for i in range(2)]==[7,7]
        before=expect(*request('GET','/api/events'),200)
        p=event('Atomic repeat','2026-10-05T13:00:00Z','2026-10-05T14:00:00Z',repeat_weekly=2)
        assert request('POST','/api/events',p)[0]==409
        assert expect(*request('GET','/api/events'),200)==before
    check('weekly_recurrence_atomicity',recurrence,usable)
    def persistence():
        global process
        before=expect(*request('GET','/api/events'),200)
        assert before
        process.terminate();process.wait(timeout=5)
        process=start();ready()
        assert expect(*request('GET','/api/events'),200)==before
        assert (work/'calendar.sqlite3').read_bytes()[:16]==b'SQLite format 3\x00'
    check('sqlite_restart_persistence',persistence,usable)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(timezone_id='UTC',viewport={'width':1000,'height':720})
        page.set_default_timeout(3500)
        def browser_create():
            page.goto(base,wait_until='networkidle')
            page.get_by_role('button',name='新建日程',exact=True).click()
            page.get_by_label('标题',exact=True).fill('Browser R38 meeting')
            page.get_by_label('开始时间',exact=True).fill('2026-10-09T12:00')
            page.get_by_label('结束时间',exact=True).fill('2026-10-09T13:00')
            page.get_by_label('日历',exact=True).select_option(str(calendar['id']))
            page.get_by_role('button',name='保存',exact=True).click()
            page.wait_for_timeout(400)
            assert any(e['title']=='Browser R38 meeting' for e in expect(*request('GET','/api/events'),200))
            page.reload(wait_until='networkidle')
            page.get_by_label('日期',exact=True).fill('2026-10-09')
            page.get_by_label('日期',exact=True).press('Tab')
            page.get_by_role('button',name='列表',exact=True).click()
            page.get_by_text('Browser R38 meeting',exact=True).first.wait_for(state='visible')
        check('browser_create_refresh',browser_create,usable)
        def views():
            for name in ('月','周','日','列表'):
                page.get_by_role('button',name=name,exact=True).click()
                page.get_by_text('Browser R38 meeting',exact=True).first.wait_for(state='visible')
            page.get_by_label('搜索',exact=True).fill('definitely-no-match-r38')
            page.wait_for_timeout(400)
            assert page.get_by_text('Browser R38 meeting',exact=True).count()==0 or not page.get_by_text('Browser R38 meeting',exact=True).first.is_visible()
        check('browser_date_views_and_search',views,usable)
        def browser_edit_delete():
            page.get_by_label('搜索',exact=True).fill('')
            page.get_by_text('Browser R38 meeting',exact=True).first.click()
            page.get_by_label('标题',exact=True).fill('Browser edited')
            page.get_by_role('button',name='保存',exact=True).click()
            page.wait_for_timeout(400)
            page.get_by_text('Browser edited',exact=True).first.click()
            page.on('dialog',lambda dialog:dialog.accept())
            page.get_by_role('button',name='删除',exact=True).click()
            page.wait_for_timeout(400)
            assert not any(e['title']=='Browser edited' for e in expect(*request('GET','/api/events'),200))
        check('browser_edit_delete',browser_edit_delete,usable)
        browser.close()
finally:
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=3)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    log.flush();log.seek(0)
    print(json.dumps({'checks':results,'server_log':log.read()[-1500:]},ensure_ascii=False))
    log.close()
sys.exit(0 if len(results)==13 and all(r['passed'] for r in results) else 1)
