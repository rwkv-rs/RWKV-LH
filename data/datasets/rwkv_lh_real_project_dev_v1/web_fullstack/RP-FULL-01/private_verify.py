"""Private behavior grader. Workspace is read-only; all runtime files are temporary."""
from pathlib import Path
import contextlib, functools, json, os, socket, sqlite3, subprocess, sys, tempfile, threading, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from playwright.sync_api import sync_playwright, expect

TASK = 'RP-FULL-01'
WORKSPACE = Path(sys.argv[1]).resolve()
def require(v,message):
    if not v: raise AssertionError(message)
def port():
    with socket.socket() as s: s.bind(('127.0.0.1',0));return s.getsockname()[1]
def request(base,path,method='GET',body=None,expected=200):
    payload=None if body is None else json.dumps(body).encode()
    req=Request(base+path,data=payload,method=method,headers={'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=8) as r: status,data=r.status,r.read()
    except HTTPError as e: status,data=e.code,e.read()
    require(status==expected,f'{method} {path}: expected HTTP {expected}, got {status}')
    return json.loads(data)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
class Service:
    def __init__(self,tmp): self.tmp=tmp;self.port=port();self.base=f'http://127.0.0.1:{self.port}';self.process=None;self.http=None;self.log=None;self.db=tmp/'database.sqlite'
    def start(self):
        if TASK.startswith('RP-WEB'):
            self.http=ThreadingHTTPServer(('127.0.0.1',self.port),functools.partial(QuietHandler,directory=str(WORKSPACE)));self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        else:
            self.log=(self.tmp/'server.log').open('ab');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
            self.process=subprocess.Popen([sys.executable,str(WORKSPACE/'server.py'),'--host','127.0.0.1','--port',str(self.port),'--db',str(self.db)],cwd=self.tmp,env=env,stdout=self.log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if self.process and self.process.poll() is not None: raise AssertionError('server exited before ready')
            try:
                with urlopen(self.base+'/',timeout=.5) as r:
                    if r.status==200:return
            except (OSError,URLError): time.sleep(.05)
        raise AssertionError('server readiness timed out')
    def stop(self):
        if self.http:self.http.shutdown();self.http.server_close();self.http=None
        if self.process:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
            self.process=None
        if self.log:self.log.close();self.log=None
    def restart(self):self.stop();self.start()

def kanban(page,service,tmp):
    title=page.get_by_label('Task title',exact=True)
    title.fill('Release alpha');page.get_by_label('Description',exact=True).fill('First pass');page.get_by_label('Priority',exact=True).select_option('high');title.press('Enter')
    first=page.get_by_role('article',name='Task Release alpha',exact=True);expect(first).to_be_visible()
    title.fill('Review docs');page.get_by_label('Description',exact=True).fill('Readme');page.get_by_label('Priority',exact=True).select_option('low');page.get_by_role('button',name='Add task',exact=True).click()
    expect(page.get_by_role('article')).to_have_count(2)
    title.fill('   ');page.get_by_role('button',name='Add task',exact=True).click();expect(page.get_by_role('article')).to_have_count(2);expect(page.get_by_role('alert')).not_to_be_empty()
    page.get_by_label('Priority filter').select_option('high');expect(page.get_by_role('article')).to_have_count(1)
    first.get_by_role('button',name='Edit',exact=True).click();title.fill('Release beta');page.get_by_label('Description',exact=True).fill('Updated detail');page.get_by_label('Priority',exact=True).select_option('medium');page.get_by_role('button',name='Save task',exact=True).click()
    page.get_by_label('Priority filter').select_option('all');first=page.get_by_role('article',name='Task Release beta',exact=True);expect(first).to_contain_text('Updated detail')
    first.get_by_role('button',name='Move to doing',exact=True).click();page.get_by_label('Status filter').select_option('doing');expect(page.get_by_role('article')).to_have_count(1);page.get_by_label('Search tasks').fill('BETA');expect(first).to_be_visible()
    page.reload();page.get_by_label('Search tasks').fill('');page.get_by_label('Status filter').select_option('all');page.get_by_label('Priority filter').select_option('all');expect(first).to_be_visible();expect(first).to_contain_text('doing');expect(first).to_contain_text('medium')
    move=first.get_by_role('button',name='Move to done',exact=True);move.focus();move.press('Enter');expect(first).to_contain_text('done')
    page.get_by_role('article',name='Task Review docs',exact=True).get_by_role('button',name='Delete',exact=True).click();page.reload();expect(page.get_by_role('article')).to_have_count(1);expect(first).to_contain_text('done')

def reading(page,service,tmp):
    for title,author,tags in [('Networks','A. Rivers','systems, history'),('Kernel Notes','B. Stone','systems, computing'),('Old Maps','C. Vale','history')]:
        page.get_by_label('Book title',exact=True).fill(title);page.get_by_label('Author',exact=True).fill(author);page.get_by_label('Tags',exact=True).fill(tags);page.get_by_role('button',name='Add book',exact=True).click()
    expect(page.get_by_role('article')).to_have_count(3);page.get_by_label('Tag: systems',exact=True).check();page.get_by_label('Tag: history',exact=True).check();expect(page.get_by_role('article')).to_have_count(1);expect(page.get_by_role('article',name='Book Networks',exact=True)).to_be_visible()
    page.get_by_label('Tag: history',exact=True).uncheck();expect(page.get_by_role('article')).to_have_count(2);page.get_by_label('Tag: systems',exact=True).uncheck();page.get_by_label('Search books').fill('stone');expect(page.get_by_role('article',name='Book Kernel Notes',exact=True)).to_be_visible();expect(page.get_by_role('article')).to_have_count(1);page.get_by_label('Search books').fill('')
    with page.expect_download() as event:page.get_by_role('button',name='Export JSON',exact=True).click()
    out=tmp/'export.json';event.value.save_as(out);value=json.loads(out.read_text());require(value['version']==1 and len(value['books'])==3,'export must contain entire library');require({b['title'] for b in value['books']}=={'Networks','Kernel Notes','Old Maps'},'export titles differ');require(len({b['id'] for b in value['books']})==3,'unique export ids required')
    page.get_by_role('article',name='Book Old Maps',exact=True).get_by_role('button',name='Delete',exact=True).click();page.reload();expect(page.get_by_role('article')).to_have_count(2)
    good={'version':1,'books':[{'id':'import-57','title':'Coastal Atlas','author':'D. Lane','tags':['geography','reference']}]};path=tmp/'good.json';path.write_text(json.dumps(good));page.get_by_label('Import JSON',exact=True).set_input_files(path);page.get_by_role('button',name='Import books',exact=True).click();expect(page.get_by_role('article',name='Book Coastal Atlas',exact=True)).to_be_visible();expect(page.get_by_role('article')).to_have_count(1)
    bad={'version':1,'books':[good['books'][0],{'id':'broken','title':'Bad partial','author':'Nobody','tags':7}]};path=tmp/'bad.json';path.write_text(json.dumps(bad));page.get_by_label('Import JSON',exact=True).set_input_files(path);page.get_by_role('button',name='Import books',exact=True).click();expect(page.get_by_role('alert')).to_contain_text('rejected');page.reload();expect(page.get_by_role('article')).to_have_count(1);expect(page.get_by_role('article',name='Book Coastal Atlas',exact=True)).to_be_visible()
    duplicate={'version':1,'books':[good['books'][0],good['books'][0]]};path=tmp/'duplicate.json';path.write_text(json.dumps(duplicate));page.get_by_label('Import JSON',exact=True).set_input_files(path);page.get_by_role('button',name='Import books',exact=True).click();expect(page.get_by_role('alert')).to_contain_text('rejected');expect(page.get_by_role('article')).to_have_count(1)

def tickets(page,service,tmp):
    for title,desc in [('Broken export','CSV download stops early'),('Login help','Account access problem')]:
        page.get_by_label('Ticket title',exact=True).fill(title);page.get_by_label('Ticket description',exact=True).fill(desc);page.get_by_role('button',name='Create ticket',exact=True).click();expect(page.get_by_role('article',name='Ticket '+title,exact=True)).to_be_visible()
    first=page.get_by_role('article',name='Ticket Broken export',exact=True);first.get_by_label('Assignee',exact=True).fill('Ada');first.get_by_role('button',name='Assign',exact=True).click();expect(first.get_by_label('Assignee',exact=True)).to_have_value('Ada');first.get_by_role('button',name='Close',exact=True).click();expect(first).to_contain_text('closed')
    page.get_by_label('Status filter').select_option('closed');expect(page.get_by_role('article')).to_have_count(1);page.get_by_label('Search tickets').fill('CSV');expect(first).to_be_visible();page.get_by_label('Search tickets').fill('Account');expect(page.get_by_role('article')).to_have_count(0);page.get_by_label('Status filter').select_option('all');expect(page.get_by_role('article',name='Ticket Login help',exact=True)).to_be_visible()
    rows=request(service.base,'/api/tickets')['tickets'];require(len(rows)==2,'API list missing tickets');ticket=next(t for t in rows if t['title']=='Broken export');require(ticket['assignee']=='Ada' and ticket['status']=='closed','API state differs from UI')
    request(service.base,'/api/tickets','POST',{'title':' ','description':'bad'},400);request(service.base,'/api/tickets/'+str(ticket['id']),'PATCH',{'status':'invalid','assignee':'Unwanted'},400)
    again=next(t for t in request(service.base,'/api/tickets')['tickets'] if t['id']==ticket['id']);require(again['assignee']=='Ada' and again['status']=='closed','invalid patch partially changed ticket')
    service.restart();page.reload();page.get_by_label('Search tickets').fill('');page.get_by_label('Status filter').select_option('all');expect(page.get_by_role('article')).to_have_count(2);expect(first.get_by_label('Assignee',exact=True)).to_have_value('Ada');expect(first).to_contain_text('closed')
    with sqlite3.connect(service.db) as db:require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity failed')
    second=page.context.browser.new_context();other=second.new_page();other.goto(service.base);expect(other.get_by_role('article',name='Ticket Broken export',exact=True)).to_contain_text('closed');second.close()

def votes(page,service,tmp):
    for title,desc in [('Focus Friday','Reserve quiet work time'),('Team demos','Share weekly prototypes')]:
        page.get_by_label('Proposal title',exact=True).fill(title);page.get_by_label('Proposal description',exact=True).fill(desc);page.get_by_role('button',name='Create proposal',exact=True).click();expect(page.get_by_role('article',name='Proposal '+title,exact=True)).to_be_visible()
    first=page.get_by_role('article',name='Proposal Focus Friday',exact=True);page.get_by_label('Your name',exact=True).fill('Alice');page.get_by_label('Your name',exact=True).press('Tab');first.get_by_role('button',name='Vote',exact=True).click();expect(first).to_contain_text('Votes: 1')
    page.get_by_label('Your name',exact=True).fill('Bob');page.get_by_label('Your name',exact=True).press('Tab');first.get_by_role('button',name='Vote',exact=True).click();expect(first).to_contain_text('Votes: 2')
    rows=request(service.base,'/api/proposals?sort=votes')['proposals'];ident=next(p['id'] for p in rows if p['title']=='Focus Friday');request(service.base,f'/api/proposals/{ident}/vote','PUT',{'voter':'Bob','active':True});require(request(service.base,'/api/proposals?sort=votes')['proposals'][0]['votes']==2,'duplicate vote increased count')
    first.get_by_role('button',name='Remove vote',exact=True).click();expect(first).to_contain_text('Votes: 1');first.get_by_role('button',name='Vote',exact=True).click();expect(first).to_contain_text('Votes: 2');page.get_by_label('Sort proposals').select_option('votes');expect(page.get_by_role('article').first).to_have_attribute('aria-label','Proposal Focus Friday')
    first.get_by_role('button',name='Close voting',exact=True).click();expect(first).to_contain_text('Voting closed');expect(first.get_by_role('button',name='Remove vote',exact=True)).to_be_disabled();request(service.base,f'/api/proposals/{ident}/vote','PUT',{'voter':'Cara','active':True},409);request(service.base,f'/api/proposals/{ident}/vote','PUT',{'voter':'Bob','active':False},409)
    request(service.base,'/api/proposals','POST',{'title':' ','description':'bad'},400);service.restart();page.reload();first=page.get_by_role('article',name='Proposal Focus Friday',exact=True);expect(first).to_contain_text('Votes: 2');expect(first).to_contain_text('Voting closed');expect(page.get_by_role('article')).to_have_count(2)
    persisted=next(p for p in request(service.base,'/api/proposals?sort=votes')['proposals'] if p['id']==ident);require(persisted['closed'] is True and persisted['votes']==2,'restart changed closed proposal or votes')
    with sqlite3.connect(service.db) as db:require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity failed')

def main():
    with tempfile.TemporaryDirectory(prefix='rwkv-project-browser-') as name:
        tmp=Path(name);service=Service(tmp)
        try:
            service.start()
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,args=['--no-sandbox']);context=browser.new_context(accept_downloads=True);page=context.new_page();page.set_default_timeout(8000);page.goto(service.base)
                {'RP-WEB-01':kanban,'RP-WEB-02':reading,'RP-FULL-01':tickets,'RP-FULL-02':votes}[TASK](page,service,tmp)
                context.close();browser.close()
        finally:service.stop()
    print(json.dumps({'task_id':TASK,'passed':True,'verification':'real_browser_and_runtime_behavior'}))
if __name__=='__main__':main()
