from pathlib import Path
import importlib.util,json,sqlite3,subprocess,socket,time,urllib.request,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
V=D/'external_verification';V.mkdir(exist_ok=False)
def load(path):
    spec=importlib.util.spec_from_file_location('inspection_target',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
src=V/'backup';shutil.copytree(D/'fixtures/backup_check',src)
m=load(src/'config_store/sqlite_io.py');db=src/'source.sqlite';backup=src/'backup.sqlite'
with sqlite3.connect(db) as connection:
    connection.execute('CREATE TABLE settings(key TEXT,value TEXT)');connection.execute('PRAGMA user_version=1');connection.execute("INSERT INTO settings VALUES('a','b')")
backup.write_bytes(b'preexisting destination sentinel')
error=None
try:m.write_backup_exclusive(db,backup)
except Exception as exc:error=type(exc).__name__
assert error=='FileExistsError';assert backup.read_bytes()==b'preexisting destination sentinel';assert not list(src.glob('.config-stage-*'))
backup.unlink();m.write_backup_exclusive(db,backup)
with sqlite3.connect(backup) as c:assert c.execute('SELECT * FROM settings').fetchall()==[('a','b')]
api=V/'api';shutil.copytree(D/'fixtures/api_bug',api)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
p=subprocess.Popen([sys.executable,str(api/'server.py'),'--db',str(api/'requested.sqlite'),'--port',str(port)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
try:
    response=None
    for _ in range(100):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=.5) as r:response={'status':r.status,'body':json.loads(r.read())}
            break
        except OSError:time.sleep(.05)
    assert response=={'status':200,'body':{'ok':True}}
    assert not (api/'requested.sqlite').exists()
finally:p.terminate();stdout,stderr=p.communicate(timeout=10)
(V/'server.stderr').write_bytes(stderr)
result={'backup_existing':{'exception':error,'original_content_unchanged':True,'temporary_files_removed':True},'backup_new':{'copied_rows':[['a','b']]},'api':{'health':response,'requested_database_created':False,'interpretation':'--db is accepted but never used; health does not demonstrate persistent business implementation'},'scope':'external isolated copies; no verifier information entered model workspace or input'}
(V/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
