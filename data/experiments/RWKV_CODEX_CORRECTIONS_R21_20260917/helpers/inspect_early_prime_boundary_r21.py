from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));from rwkv_lh.direct_trace_data import replay_run
D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';r=json.loads((D/'INVENTORY.json').read_text())['tasks'][71];root=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/bulk_deployment/inputs'/r['id']/'original';model=json.loads((D/'boundary_audit_corrected'/f"{r['id']}.json").read_text())['model_sha256'];task=(D/'tasks'/r['id']/'TASK.md').read_bytes().decode();rows=[]
for cp,x in replay_run(root,model).items():
 if task in x['input_text'] or json.dumps(task,ensure_ascii=False)[1:-1] in x['input_text']:
  record={'checkpoint':cp,'request':x['request_id'],'input_tokens':len(x['input_token_ids']),'input_sha256':hashlib.sha256(x['input_text'].encode()).hexdigest(),'output':x['raw_generation']['raw_output']};rows.append(record);print(record)
(D/'EARLY_PRIME_BOUNDARIES.json').write_text(json.dumps(rows,indent=2))
