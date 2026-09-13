from pathlib import Path
import json,sys
R=Path('/home/chase/GitHub/RWKV-LH');B=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913';sys.path.insert(0,str(D/'source'))
from rwkv_lh.token_budget import tokenizer
from rwkv_lh.schema import ModelEvent
from rwkv_lh.model_io import render_event_append
rows=[]
for p in sorted((B/'dev').iterdir()):
 s=json.loads((p/'state_snapshot.json').read_text())
 for f in sorted(p.glob('observation_*.json')):
  e=ModelEvent.from_dict(json.loads(f.read_text()));wire=render_event_append(e);assert any(c['transcript']==wire for c in s['model_states'].values());matches=e.payload['result'].get('structured_output',{}).get('matches',[]);rows.append(dict(run=p.name,event_id=e.event_id,wire_tokens=len(tokenizer().encode(wire)),matched_line_tokens=sum(len(tokenizer().encode(m['line_text'])) for m in matches),sha256_mentions=wire.count('sha256'),match_count=len(matches),wire_sha256=__import__('hashlib').sha256(wire.encode()).hexdigest()))
(D/'OBSERVATION_WIRE_MEASUREMENTS.json').write_text(json.dumps(rows,indent=2)+'\n');print(rows[:2]);print([r for r in rows if r['run'].startswith('health')])
