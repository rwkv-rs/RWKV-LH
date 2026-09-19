from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');B=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/bulk_deployment';D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';remote=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916')
rows=json.loads((B/'TASK_SELECTION.json').read_text())['tasks'];inventory=[]
for i,row in enumerate(rows):
 snap=B/Path(row['snapshot']).relative_to(remote);task=snap/'TASK.md';assert task.is_file();dest=D/'tasks'/row['id'];dest.mkdir(parents=True,exist_ok=True);shutil.copy2(task,dest/'TASK.md')
 inventory.append({'id':row['id'],'ordinal':i,'task_sha256':hashlib.sha256(task.read_bytes()).hexdigest(),'original_snapshot':str(snap),'original_binding':row,'known_original_passed':row['collection_artifact_passed'],'status':'pending_codex_review'})
(D/'INVENTORY.json').write_text(json.dumps({'count':len(inventory),'tasks':inventory},indent=2));(D/'REGISTRATION.json').write_text(json.dumps({'scope':'all1024 owner authorized direct Codex correction','author':'Codex','no_teacher_generation':True,'verification':'same sealed private cases, no hidden answers exposed to author; public task and original workspace only','attribution':'Codex corrected, never RWKV independent','training':'candidates only until original-boundary applicability and independent review gates; no training','budget':'each candidate validator case timeout remains source contract; manual code authorship; no synthetic bulk solution templating','model_cleanup':'Qwen3.8 and old CoderNext weights only; shared engine retained'},indent=2))
print('registered',len(inventory),'original_passed',sum(x['known_original_passed'] for x in inventory))
