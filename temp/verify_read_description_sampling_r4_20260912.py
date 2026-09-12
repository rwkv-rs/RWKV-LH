from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912')
reg=json.loads((D/'REGISTRATION.json').read_text());n=0
for arm in ['before','after']:
 for p in sorted((D/arm/'runs').glob('*/model_trace.jsonl')):
  for e in map(json.loads,p.read_text().splitlines()):
   if e['type']=='model_session_generation_returned':
    g=e['raw_generation'];assert g['sampling']==reg['sampling'];assert g['max_output_tokens']==reg['max_output_tokens'];assert g['state_profile_id']=='zero' and g['state_profile_sha256']=='0'*64;n+=1
assert n==48
(D/'SAMPLING_BUDGET_VERIFICATION.json').write_text(json.dumps({'generations_checked':n,'sampling':reg['sampling'],'output_budget':reg['max_output_tokens'],'all_match':True},indent=2)+'\n');print('48 sampling/budget/profile records exact')
