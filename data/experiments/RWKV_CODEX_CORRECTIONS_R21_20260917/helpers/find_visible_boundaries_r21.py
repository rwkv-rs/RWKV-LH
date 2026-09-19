from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import replay_run
D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';B=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/bulk_deployment';remote=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916');rows={r['id']:r for r in json.loads((D/'INVENTORY.json').read_text())['tasks']};report=[]
for p in sorted((D/'boundary_audit_corrected').glob('*.json')):
 audit=json.loads(p.read_text())
 if audit.get('task_visible') is not False:continue
 row=rows[audit['id']];root=B/Path(row['original_binding']['source_root']).relative_to(remote);replayed=replay_run(root,audit['model_sha256']);task=(D/'tasks'/row['id']/'TASK.md').read_bytes().decode('utf-8');eligible=[]
 for cp,actual in replayed.items():
  if task in actual['input_text'] or json.dumps(task,ensure_ascii=False)[1:-1] in actual['input_text']:
   snapshot=root/'generation_snapshots'/actual['request_id']/'before'
   if snapshot.is_dir():eligible.append({'checkpoint':cp,'request_id':actual['request_id'],'input_checkpoint_id':actual['input_checkpoint_id'],'input_sha256':hashlib.sha256(actual['input_text'].encode()).hexdigest(),'input_tokens':len(actual['input_token_ids']),'snapshot':str(snapshot)})
 report.append({'id':row['id'],'original_selected_boundary_visible':False,'later_visible_real_boundaries':eligible,'status':'alternative_real_boundary_found' if eligible else 'no_complete_visible_task_in_recorded_generations','training_admitted':False});print(row['id'],len(eligible),flush=True)
(D/'ALTERNATIVE_VISIBLE_BOUNDARIES.json').write_text(json.dumps(report,indent=2))
