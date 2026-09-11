from pathlib import Path
import json,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.tokenizer import RWKVTokenizer
O=R/'data/experiments/R126_CURRENT_REGRESSION_REVIEW_R1_20260911';tok=RWKVTokenizer();out=[]
for id in ['E2E-B01','E2E-B11']:
 es=json.loads((R/'data/experiments/FULL_TRACE_COLLECTION_R1_20260911/all_zero/cases'/id/'event_log.json').read_text())
 for e in es:
  if e.get('type')!='exact_tool_selection_staged':continue
  s=e['data']['selection']['raw_selection'];lanes=[]
  for k,v in s['lane_selections'].items():
   ids=v['decoder_trace']['prompt_token_ids'];prompt=tok.decode([i for i in ids if i!=0]);lanes.append({'lane':k,'selected':v['selected_operation'],'eligible':v['eligible_labels'],'prompt':prompt})
  out.append({'task_id':id,'selection_id':s['selection_id'],'selected':s['selected_operation'],'lanes':lanes})
(O/'SELECTOR_INPUT_EVIDENCE.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
for r in out:
 if r['task_id']=='E2E-B11':print(r['selected'],r['lanes'][0]['eligible'],r['lanes'][0]['prompt'][-3500:])
