from pathlib import Path
import sys,json,hashlib,sqlite3,collections
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import replay_run
from rwkv_lh.correction_snapshots import validate_generation_snapshot
from rwkv_lh import model_io
D=R/'data/experiments/RWKV_LOCAL_TEACHER_PILOT_R15_20260916';C=R/'data/experiments/RWKV_COLLECTION_R13_20260916'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for p in sorted((C/'campaign/batches').glob('*/queue.sqlite3')):
 c=sqlite3.connect(f'file:{p}?mode=ro',uri=True)
 rows += [json.loads(x[0]) for x in c.execute("select result from tasks where status='recorded'")]
groups={'protocol':[],'progress':[],'failed_submission':[]}
for row in sorted(rows,key=lambda r:r['id']):
 if row['external_acceptance']['status']=='passed':continue
 reason=row['termination_reason']
 group='protocol' if reason=='protocol_rejection_budget_exhausted' else 'progress' if reason=='identical_success_budget_exhausted' else 'failed_submission' if reason=='answer_submitted' else None
 if group:groups[group].append(row)
selected=[]
for group,n in [('protocol',8),('progress',8),('failed_submission',4)]:
 for row in groups[group]:
  if sum(x['stratum']==group for x in selected)>=n:break
  seal=Path(row['storage_retirement']['evidence'])/'MANIFEST.json';manifest=json.loads(seal.read_text());root=Path(manifest['run_root']); replay=replay_run(root,'559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65')
  candidates=[]
  for cp,actual in replay.items():
   before=validate_generation_snapshot(root,actual,manifest['source_files']);task=(before/'TASK.md').read_text()
   if task not in actual['input_text'] and json.dumps(task,ensure_ascii=False)[1:-1] not in actual['input_text']:continue
   raw=actual['raw_generation']['raw_output']
   try:cmd=model_io.parse_model_command(raw);tool=cmd.name
   except Exception:tool='INVALID'
   if group=='protocol' and tool!='INVALID':continue
   if group=='progress' and tool not in ('read_file','list_directory'):continue
   if group=='failed_submission' and tool!='final_answer':continue
   candidates.append((cp,actual,before,tool))
  if not candidates:continue
  cp,actual,before,tool=candidates[-1];folder=D/'sources'/row['id'];folder.mkdir(parents=True,exist_ok=False)
  (folder/'INPUT.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2)+'\n')
  review={'id':row['id'],'stratum':group,'source_root':str(root),'manifest':str(seal),'manifest_sha256':sha(seal),'checkpoint':cp,'request_id':actual['request_id'],'snapshot':str(before),'input_sha256':hashlib.sha256(actual['input_text'].encode()).hexdigest(),'original_tool':tool,'original_output':actual['raw_generation']['raw_output'],'source_result_sha256':sha(root/'RESULT.json'),'conversion':str(root.parent.parent/'item.json'),'trace_summary':[{'checkpoint':key,'output':v['raw_generation']['raw_output']} for key,v in replay.items()],'source_task':task}
  (folder/'SOURCE_AUDIT.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');selected.append({k:v for k,v in review.items() if k not in ('trace_summary','source_task','original_output')})
  print(group,row['id'],tool,'inputchars',len(actual['input_text']),'task',task[:100].replace('\n',' '),flush=True)
assert len(selected)==20
(D/'TASK_SELECTION.json').write_text(json.dumps({'status':'frozen_selection_pending_semantic_audit','selection':'Sort source IDs within termination strata, select last visible full TASK generation matching error type; 8 protocol /8 repeated-read /4 failed submissions; no teacher outputs used. These are strata, not proven causal labels.','tasks':selected},indent=2)+'\n')
