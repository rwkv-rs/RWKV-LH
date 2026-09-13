from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913';out=[];inputs=outputs=calls=0
for P in [D,D/'order_probe']:
 reg=json.loads((P/'REGISTRATION.json').read_text());a=json.loads((P/'MECHANICAL.json').read_text())
 for p in sorted((P/'runs').iterdir()):
  result=json.loads((p/'execution/RESULT.json').read_text());c=next(c for c in reg['cases'] if c['id']==p.name.rsplit('-',2)[0]);actual={str(f.relative_to(p/'workspace')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (p/'workspace').rglob('*') if f.is_file()};assert actual==c['files']
  order=[r['arguments']['path'] for r in result['actions'] if r['action_type']=='read_file']
  row=next(r for r in a['runs'] if r['run']==p.name);calls+=len(row['calls']);inputs+=sum(c['input_tokens'] for c in row['calls']);outputs+=sum(c['output_tokens'] for c in row['calls'])
  out.append(dict(phase='main' if P==D else 'order_probe',run=p.name,read_order=order,source_unchanged=True,termination=result['termination'],calls=result['generation_started']))
prev=json.loads((R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913/FINAL_SOURCE_IDENTITY.json').read_text())['files'];assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==s for p,s in prev.items())
value=dict(runs=out,returned_calls=calls,input_tokens=inputs,output_tokens=outputs,mutation_count=0,strong_calls=0,training_steps=0,production_source_changed=False,regression_basis='Identical production source to 1594 passed/0 skipped PYTEST_FINAL_R2.log; no runtime/test edits, no redundant full rerun',limits='Frozen small source/order exposure contrast; source list and physical workspace identities differ. State metadata/token replay checked, internal tensor recomputation not performed. No resource savings claim.')
(D/'ACCOUNTING.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');print(value)
