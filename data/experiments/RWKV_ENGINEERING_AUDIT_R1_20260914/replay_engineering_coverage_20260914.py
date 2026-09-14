from pathlib import Path
import json,hashlib
from rwkv_lh.direct_trace_data import replay_run
root=Path('/home/chase/GitHub/RWKV-LH');out=root/'data/experiments/RWKV_ENGINEERING_AUDIT_R1_20260914'
names=['RWKV_EXPLICIT_EDIT_R1_20260914','RWKV_ATOMIC_CHANGE_R1_20260914','RWKV_GOAL_DELIVERY_R1_20260914','RWKV_AGENT_ARCHITECTURE_BATCH_R1_20260914','RWKV_ASSISTED_RECOVERY_R1_20260914','RWKV_QUERY_REPAIR_FEEDBACK_R1_20260914','RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913']
paths=sorted({p.parent for n in names for p in (root/'data/experiments'/n).rglob('RESULT.json') if (p.parent/'state_snapshot.json').is_file() and (p.parent/'model_trace.jsonl').is_file()})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'REPLAY_REGISTRATION.json').write_text(json.dumps({'criterion':'production exact token/State reconstruction, not acceptance or training admission','sources':[str(p.relative_to(root)) for p in paths],'script_sha256':sha(Path(__file__)),'source_sha256':{str((p/f).relative_to(root)):sha(p/f) for p in paths for f in ('RESULT.json','state_snapshot.json','model_trace.jsonl')}},indent=2))
results=[]
for p in paths:
 r=json.loads((p/'RESULT.json').read_text());state=json.loads((p/'state_snapshot.json').read_text());entry={'run':str(p.relative_to(root)),'task_digest':hashlib.sha256(state['goal']['request'].encode()).hexdigest(),'scope':r.get('tool_scope'),'assistance':r.get('assistance'),'termination':r.get('termination'),'calls':r.get('generation_started')}
 try:
  rows=replay_run(p,'559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65');entry.update(replayed=True,generations=len(rows))
 except Exception as e:entry.update(replayed=False,error=type(e).__name__+': '+str(e))
 results.append(entry)
(out/'REPLAY_COVERAGE.json').write_text(json.dumps(results,indent=2))
print(json.dumps({'runs':len(results),'passed':sum(r['replayed'] for r in results),'distinct_request_texts':len({r['task_digest'] for r in results}),'results':results},indent=2))
