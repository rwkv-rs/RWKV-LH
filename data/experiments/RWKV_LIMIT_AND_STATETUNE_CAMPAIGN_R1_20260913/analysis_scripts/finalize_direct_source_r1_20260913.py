from pathlib import Path
import json,sqlite3,hashlib,sys
sys.path.insert(0,"/home/chase/GitHub/RWKV-LH")
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.schema import RunState
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in sorted((P/'collection/runs').iterdir()):
 original=json.loads((p/'SOURCE_MANIFEST.json').read_text());changed=[]
 for n,h in original['files'].items():
  if not (p/n).exists() or sha(p/n)!=h:
   assert n in {'state/long_horizon.db','state/long_horizon.db-wal','state/long_horizon.db-shm'},n
   changed.append(n)
 db=p/'state/long_horizon.db';con=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True)
 try:
  assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
  stored=RunState.from_dict(LongHorizonStore._deserialize(con.execute('SELECT state_json FROM runs').fetchone()[0])).to_dict();snapshot=json.loads((p/'state_snapshot.json').read_text());assert stored==snapshot
  last=con.execute('SELECT type,revision FROM events ORDER BY revision DESC LIMIT 1').fetchone();assert last[0]=='run_completed' and last[1]==snapshot['revision']
  counts={t:con.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['runs','actions' if False else 'action_index','checkpoints','events']}
 finally:con.close()
 row={'id':p.name,'original_manifest_sha256':sha(p/'SOURCE_MANIFEST.json'),'changed_members':changed,'explanation':'SQLite WAL/shm are live connection artifacts; SQLite connection context commits but does not close. Process exit checkpoints WAL into DB; logical persisted run exactly equals immutable trace snapshot. Original manifest retained as failed seal.','logical_snapshot_equal':True,'last_event':list(last),'table_counts':counts}
 finalized={**original,'files':{str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file() and f.name!='FINALIZED_SOURCE_MANIFEST.json' and not f.name.endswith(('-shm','-wal'))},'finalization':row};f=p/'FINALIZED_SOURCE_MANIFEST.json';assert not f.exists();f.write_text(json.dumps(finalized,ensure_ascii=False,indent=2)+'\n');rows.append(row)
(P/'SOURCE_FINALIZATION.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
