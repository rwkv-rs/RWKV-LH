from pathlib import Path
import json,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
for phase in ['budget_probe','file_scope_probe','requested_advice_probe','advice_label_probe']:
 P=D/phase;b=json.loads((P/'BATCH.json').read_text())
 # Preserve initial orchestration-path error; judgments and scores do not change.
 for row in b['reviews']:
  for key in ['contract','run','judgment']:row[key]=row[key].removeprefix(phase+'/')
  row['evidence_root']='..'
 (P/'BATCH_LOCAL_PATHS.json').write_text(json.dumps(b,ensure_ascii=False,indent=2)+'\n')
 subprocess.run([str(R/'.venv/bin/python'),str(R/'scripts/review_agent_task.py'),'aggregate','--input',str(P/'BATCH_LOCAL_PATHS.json'),'--output',str(P/'CLI_SUMMARY.json')],check=True)
 assert json.loads((P/'CLI_SUMMARY.json').read_text())==json.loads((P/'TASK_SUMMARY.json').read_text())
print('Four phase original evidence bindings and summaries verified')
