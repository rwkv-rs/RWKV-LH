from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse, json, sqlite3
from urllib.parse import urlsplit, parse_qs

KIND = 'votes'
class BadRequest(Exception): pass
class Conflict(Exception): pass
def text(v, required=False):
    if not isinstance(v,str) or (required and not v.strip()): raise BadRequest('Expected nonempty text' if required else 'Expected text')
    return v.strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,required=True);p.add_argument('--db',type=Path,required=True);args=p.parse_args()
    args.db.parent.mkdir(parents=True,exist_ok=True)
    def connect():
        c=sqlite3.connect(args.db,timeout=10);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT NOT NULL,assignee TEXT NOT NULL DEFAULT "",status TEXT NOT NULL DEFAULT "open")')
        db.execute('CREATE TABLE IF NOT EXISTS proposals(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,description TEXT NOT NULL,closed INTEGER NOT NULL DEFAULT 0)')
        db.execute('CREATE TABLE IF NOT EXISTS votes(proposal_id INTEGER NOT NULL REFERENCES proposals(id),voter TEXT NOT NULL,PRIMARY KEY(proposal_id,voter))')
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send_json(self,code,value):
            data=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def body(self):
            try: v=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))))
            except (ValueError,TypeError): raise BadRequest('Invalid JSON')
            if not isinstance(v,dict): raise BadRequest('Expected object')
            return v
        def do_GET(self): self.dispatch('GET')
        def do_POST(self): self.dispatch('POST')
        def do_PATCH(self): self.dispatch('PATCH')
        def do_PUT(self): self.dispatch('PUT')
        def dispatch(self,method):
            u=urlsplit(self.path);path=u.path;query=parse_qs(u.query)
            if method=='GET' and path in ('/','/index.html'):
                data=Path(__file__).with_name('index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
            try:
                with connect() as db:
                    if KIND=='tickets': code,value=self.tickets(db,path,query,method)
                    else: code,value=self.proposals(db,path,query,method)
                self.send_json(code,value)
            except BadRequest as e: self.send_json(400,{'error':str(e)})
            except Conflict as e: self.send_json(409,{'error':str(e)})
            except (KeyError,ValueError): self.send_json(404,{'error':'Not found'})
        def tickets(self,db,path,q,method):
            if path=='/api/tickets' and method=='GET':
                query=q.get('q',[''])[0].casefold();status=q.get('status',['all'])[0]
                if status not in ('all','open','closed'): raise BadRequest('Invalid status')
                rows=[dict(r) for r in db.execute('SELECT * FROM tickets ORDER BY id')]
                return 200,{'tickets':[r for r in rows if query in (r['title']+' '+r['description']).casefold() and (status=='all' or r['status']==status)]}
            if path=='/api/tickets' and method=='POST':
                v=self.body();title=text(v.get('title'),True);description=text(v.get('description',''))
                cur=db.execute('INSERT INTO tickets(title,description) VALUES(?,?)',(title,description));return 201,dict(db.execute('SELECT * FROM tickets WHERE id=?',(cur.lastrowid,)).fetchone())
            if path.startswith('/api/tickets/') and method=='PATCH':
                ident=int(path.rsplit('/',1)[1]);old=db.execute('SELECT * FROM tickets WHERE id=?',(ident,)).fetchone()
                if not old: raise KeyError('missing')
                v=self.body();assignee=text(v.get('assignee',old['assignee']));status=v.get('status',old['status'])
                if status not in ('open','closed'): raise BadRequest('Invalid status')
                db.execute('UPDATE tickets SET assignee=?,status=? WHERE id=?',(assignee,status,ident));return 200,dict(db.execute('SELECT * FROM tickets WHERE id=?',(ident,)).fetchone())
            raise KeyError('route')
        def proposals(self,db,path,q,method):
            if path=='/api/proposals' and method=='GET':
                voter=q.get('voter',[''])[0];sort=q.get('sort',['newest'])[0]
                if sort not in ('newest','votes'): raise BadRequest('Invalid sort')
                rows=[dict(r) for r in db.execute('SELECT p.*,count(v.voter) votes FROM proposals p LEFT JOIN votes v ON v.proposal_id=p.id GROUP BY p.id')]
                for r in rows:
                    r['closed']=bool(r['closed']);r['voted']=bool(db.execute('SELECT 1 FROM votes WHERE proposal_id=? AND voter=?',(r['id'],voter)).fetchone())
                rows.sort(key=(lambda r:(-r['votes'],r['id'])) if sort=='votes' else lambda r:-r['id'])
                return 200,{'proposals':rows}
            if path=='/api/proposals' and method=='POST':
                v=self.body();cur=db.execute('INSERT INTO proposals(title,description) VALUES(?,?)',(text(v.get('title'),True),text(v.get('description',''))));return 201,{'id':cur.lastrowid}
            parts=path.strip('/').split('/')
            if len(parts)>=3 and parts[:2]==['api','proposals']:
                ident=int(parts[2]);row=db.execute('SELECT * FROM proposals WHERE id=?',(ident,)).fetchone()
                if not row: raise KeyError('missing')
                v=self.body()
                if len(parts)==3 and method=='PATCH':
                    if v.get('closed') is not True: raise BadRequest('Only closing is supported')
                    db.execute('UPDATE proposals SET closed=1 WHERE id=?',(ident,));return 200,{'id':ident,'closed':True}
                if len(parts)==4 and parts[3]=='vote' and method=='PUT':
                    if row['closed']: raise Conflict('Voting closed')
                    voter=text(v.get('voter'),True);active=v.get('active')
                    if not isinstance(active,bool): raise BadRequest('active must be boolean')
                    if active: db.execute('INSERT OR IGNORE INTO votes(proposal_id,voter) VALUES(?,?)',(ident,voter))
                    else: db.execute('DELETE FROM votes WHERE proposal_id=? AND voter=?',(ident,voter))
                    return 200,{'id':ident,'votes':db.execute('SELECT count(*) FROM votes WHERE proposal_id=?',(ident,)).fetchone()[0]}
            raise KeyError('route')
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()

if __name__=='__main__': main()
