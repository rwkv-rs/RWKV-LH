from pathlib import Path
import json,sys,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');B=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913';sys.path.insert(0,str(D/'source'))
from rwkv_lh.token_budget import tokenizer
rows=[]
for p in sorted((B/'dev').iterdir()):
 es=list(map(json.loads,(p/'model_trace.jsonl').read_text().splitlines()));gs=[e['raw_generation'] for e in es if e['type']=='model_session_generation_returned'];r=json.loads((p/'RESULT.json').read_text());row={'run':p.name,'accepted_generations':[]}
 for i in range(len(r['actions'])):
  decoded=tokenizer().decode(gs[i]['raw_token_ids']);assert decoded.endswith('```');row['accepted_generations'].append({'generation':i+1,'json_fence_closed_in_actual_tokens':True,'raw_token_tail':decoded[-16:]})
 rows.append(row)
(D/'INPUT_BOUNDARY_AUDIT.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('all accepted raw outputs include closing fence')
