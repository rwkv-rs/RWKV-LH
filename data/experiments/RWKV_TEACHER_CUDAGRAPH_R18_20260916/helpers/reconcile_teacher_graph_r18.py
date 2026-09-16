from pathlib import Path
import sys,json,time,hashlib
R=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916');sys.path.insert(0,str(R))
from rwkv_lh.collection_queue import CollectionQueue
out=R/'outputs';records=[]
with CollectionQueue(out/'queue.sqlite3') as q:
 for item in list(q.items('running')):
  name=item['teacher_source']['id'];source=out/'runs'/name;target=out/'interrupted_r18'/name
  if target.exists():raise RuntimeError('already archived')
  target.parent.mkdir(exist_ok=True);source.rename(target)
  record={'source_id':item['source_id'],'task_id':item['job']['task_id'],'reason':'operator_cuda_graph_deployment_interruption','time':time.time(),'preserved':str(target),'trace_sha256':hashlib.sha256((target/'execution/strong_trace.jsonl').read_bytes()).hexdigest(),'retry_authorized':'same task, separate attempt under R18 engine identity','accepted':False}
  (target/'INTERRUPTION_R18.json').write_text(json.dumps(record,indent=2));records.append(record)
  q.db.execute("UPDATE tasks SET status='pending', updated=? WHERE source_id=? AND status='running'",(time.time(),item['source_id']))
(out/'RECONCILIATION_R18.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records,indent=2))
