from pathlib import Path
import hashlib,json,tarfile
from rwkv_lh.direct_trace_data import replay_run
root=Path('/home/chase/GitHub/RWKV-LH')
out=root/'data/experiments/RWKV_TRACE_REPLAY_AND_GROUPING_R1_20260914'
archive=root/'data/experiments/RWKV_EXPLICIT_EDIT_R1_20260914/EVIDENCE.tar.gz'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
registration={'source':str(archive.relative_to(root)),'source_sha256':sha(archive),'script_sha256':sha(Path(__file__)),'replayer_sha256':sha(root/'rwkv_lh/direct_trace_data.py'),'criterion':'Exact production token and native State replay; no semantic rescoring','model_sha256':'559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'}
(out/'REGISTRATION.json').write_text(json.dumps(registration,indent=2))
results=[]
with tarfile.open(archive) as tar:
 for trial in ('atomic-1','atomic-2'):
  prefix=f'runs/{trial}/execution/'
  members=[m for m in tar.getmembers() if m.name in [prefix+n for n in ('RESULT.json','state_snapshot.json','model_trace.jsonl')]]
  tar.extractall(out/'replay_sources',members=members,filter='data')
  rows=replay_run(out/'replay_sources'/prefix,registration['model_sha256'])
  results.append({'trial':trial,'generations':len(rows),'recomputed':all(r['recomputed'] for r in rows.values()),'request_ids':[r['request_id'] for r in rows.values()]})
(out/'REPLAY_RESULTS.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
