from pathlib import Path
import json,collections
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912'
out={}
for arm in ['before','after']:
 groups=collections.defaultdict(list)
 for p in sorted((D/arm/'runs').glob('*/state_snapshot.json')):
  r=json.loads((p.parent/'RESULT.json').read_text());s=json.loads(p.read_text());cp=next(v for v in s['model_states'].values() if v['parent_checkpoint_id'] is None)
  groups[r['case']].append({'repeat':r['repeat'],'checkpoint_id':cp['checkpoint_id'],'root_state_digest':cp['native_state_digest'],'profile_id':cp['state_profile_id'],'profile_sha256':cp['state_profile_sha256'],'input_text_digest':cp['transcript_digest'],'token_count':cp['token_count']})
 out[arm]={k:{'roots':v,'same_service_state_digest':len(set(x['root_state_digest'] for x in v))==1,'same_text':len(set(x['input_text_digest'] for x in v))==1} for k,v in groups.items()}
(D/'ROOT_STATE_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print({arm:{c:x['same_service_state_digest'] for c,x in rows.items()} for arm,rows in out.items()})
