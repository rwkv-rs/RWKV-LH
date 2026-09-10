from pathlib import Path
import json,collections
p=Path('/home/chase/GitHub/RWKV-LH/data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910/WAIVER_REVIEW_ONE_SELECTOR_SCOPE.json')
s=json.loads(p.read_text())['sources']
for r in s:
 lanes=[l for b in r['boundaries'] for l in b['lanes']]
 print(r['run_id'],'lanes',len(lanes),'equal',sum(l.get('byte_equal',False) for l in lanes),'errors',[(l['request_id'],l.get('error')) for l in lanes if not l.get('byte_equal')])
 if r['run_id']=='RP-WEB-02':
  for a in r['actions']:
   if a['action_type']=='check_command':print(json.dumps(a,ensure_ascii=False))
  for b in r['boundaries']:print('BOUNDARY',b['boundary_event_id'],'prior',b['prior_actions'],'lanes',[(l['request_id'],l.get('selected_operation')) for l in b['lanes']])
