from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912';reg=json.loads((D/'REGISTRATION.json').read_text());c=next(c for c in reg['cases'] if c['id']=='missing-2')
events=json.loads((R/c['source_event_log']).read_text());proof=[]
for e in events:
 if e['type']=='action_finished':
  a=e['data']['action']
  if a['arguments'].get('path')==c['path']:
   proof.append({'event_id':e['event_id'],'action_id':a['action_id'],'operation':a['action_type'],'success':a['result']['success'],'error':a['result'].get('error'),'artifacts':a['result'].get('artifacts')})
v={'invalid_case':'missing-2','affected_repetitions':[1,2,3],'classification':'fixture_invalid_not_model_failure','original_registration_sha256':hashlib.sha256((D/'REGISTRATION.json').read_bytes()).hexdigest(),'original_scoring_unchanged':True,'failure':'Historical missing-file event was paired with final workspace after later creation. Existence was not validated at freeze.','proof':proof,'repair_round':'RWKV_SINGLE_READ_FIXTURE_REPAIR_R2_20260912','reporting':'Report original frozen score and valid-evidence score separately; never substitute R2 into R1 denominator.'}
(D/'FIXTURE_INVALIDITY.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(proof)
