from pathlib import Path
import json,sys,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.schema import RunState
from rwkv_lh.summary_advice import build_advice_request
D=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913';P=D/'correction_candidates';P.mkdir()
seeds=[('numeric_relation',R/'data/experiments/RWKV_FACT_FIDELITY_FOCUSED_R1_20260913/runs/rag_overview-focused-r1/execution'),('requirements_as_implementation',D/'runs/code_and_requirements-focused-r1/execution'),('remaining_status_code',D/'order_probe/runs/code_and_requirements-focused-r2/execution')];rows=[]
for name,e in seeds:
 s=RunState.from_dict(json.loads((e/'state_snapshot.json').read_text()));result=json.loads((e/'RESULT.json').read_text());files={}
 for a in result['actions']:
  if a['action_type']=='read_file' and a['result']['success']:
   path=a['arguments']['path'];files[path]=(Path(s.goal.workspace_root)/path).read_text()
 payload=build_advice_request(s.goal,files,result['final']);p=P/(name+'.input.json');p.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 rows.append(dict(id=name,parent_execution=str(e.relative_to(R)),parent_result_sha256=hashlib.sha256((e/'RESULT.json').read_bytes()).hexdigest(),input_path=p.name,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status='prepared_only_not_called_not_corrected_not_training_data'))
(P/'MANIFEST.json').write_text(json.dumps(dict(candidates=rows,policy='Unique production advice builder; only original goal, already visible source files and actual candidate. No hidden review answers. Strong correction, RWKV continuation and independent verification still required before any data eligibility.'),ensure_ascii=False,indent=2)+'\n')
