from pathlib import Path
import json,sys,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';sys.path.insert(0,str(D/'source'))
from rwkv_lh.schema import RunState
from rwkv_lh.model_io import render_event_append
reg=json.loads((D/'RUN_REGISTRATION.json').read_text());rows=[]
for p in sorted((D/'dev').iterdir()):
 s=RunState.from_dict(json.loads((p/'state_snapshot.json').read_text()));events=list(map(json.loads,(p/'model_trace.jsonl').read_text().splitlines()));gids={e['candidate_checkpoint_id'] for e in events if e['type']=='model_session_generation_returned'};observations=[]
 for cp in s.model_states.values():
  assert cp.state_profile_id=='zero' and cp.state_profile_sha256=='0'*64
  assert cp.native_state_metadata['model_sha256']==reg['model_sha256']
  if not cp.parent_checkpoint_id:continue
  parent=s.model_states[cp.parent_checkpoint_id];assert cp.native_state_metadata['cache_binding']['parent_state_digest']==parent.native_state_digest
  if cp.checkpoint_id in gids:continue
  delta=set(cp.event_ids)-set(parent.event_ids);assert len(delta)==1;eid=next(iter(delta));assert cp.event_ids.count(eid)==1;assert render_event_append(s.model_events[eid])==cp.transcript;observations.append(eid)
 actual=[json.loads(f.read_text())['event_id'] for f in sorted(p.glob('observation_*.json'))];assert sorted(observations)==sorted(actual);assert len(set(observations))==len(observations)
 rows.append(dict(run=p.name,retained_checkpoints=len(s.model_states),observation_children=len(observations),all_retained_parent_profile_and_event_edges_verified=True,includes_last_observation_without_next_generation=True))
(D/'TERMINAL_STATE_AUDIT.json').write_text(json.dumps(rows,indent=2)+'\n');print('retained checkpoints',sum(r['retained_checkpoints'] for r in rows),'observations',sum(r['observation_children'] for r in rows))
