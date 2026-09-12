from pathlib import Path
import sys,json,collections,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments'/sys.argv[1]
reg=json.loads((D/'REGISTRATION.json').read_text());out={}
for c in reg['cases']:
 entries=[]
 for p in sorted((D/'runs').glob(c['id']+'-r*/model_trace.jsonl')):
  for e in map(json.loads,p.read_text().splitlines()):
   if e['type']=='model_session_generation_returned':
    g=e['raw_generation'];entries.append({'run':p.parent.name,'input_sha256':hashlib.sha256(json.dumps(g['prompt_token_ids']).encode()).hexdigest(),'output_sha256':g['raw_output_sha256'],'input_tokens':len(g['prompt_token_ids']),'output_tokens':len(g['raw_token_ids']),'finish_reason':g['finish_reason']})
 out[c['id']]={'entries':entries,'identical_inputs':len(entries)==3 and len(set(e['input_sha256'] for e in entries))==1,'identical_outputs':len(entries)==3 and len(set(e['output_sha256'] for e in entries))==1}
(D/'REPEATABILITY.json').write_text(json.dumps(out,indent=2)+'\n');print({k:{x:y for x,y in v.items() if x!='entries'} for k,v in out.items()})
