from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';sys.path.insert(0,str(D/"source"))
from rwkv_lh import task_review as review
from rwkv_lh.token_budget import tokenizer
from rwkv_lh.model_io import render_event_append,render_bootstrap
from rwkv_lh.schema import RunState
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.read_only_agent import ReadOnlyHarness as ActionHarness
from rwkv_lh.run_lifecycle import RUN_LIFECYCLE_POLICY_KEY,run_lifecycle_policy_document
import re
reg=json.loads((D/'REGISTRATION.json').read_text());cases={c['id']:c for c in reg['cases']};rows=[]
for run_dir in sorted((D/'runs').iterdir()):
 p=run_dir/'execution'
 if not (p/'RESULT.json').is_file():continue
 result=json.loads((p/'RESULT.json').read_text());s=RunState.from_dict(json.loads((p/'state_snapshot.json').read_text()));case=cases[run_dir.name.rsplit('-',2)[0]]
 assert all(review.file_digest(run_dir/'workspace'/q)==sha for q,sha in case['files'].items())
 events=[json.loads(l) for l in (p/'model_trace.jsonl').read_text().splitlines()]
 gens={e['candidate_checkpoint_id']:e['raw_generation'] for e in events if e['type']=='model_session_generation_returned'}
 starts={e['request_id']:e for e in events if e['type']=='model_session_generation_started'}
 model=LongHorizonModel(ModelSession(client=object(),settings=RuntimeSettings(base_url='http://unused.invalid',api_key='',model='audit',tool_disclosure_mode='full')),harness=ActionHarness())
 initial=RunState(run_id=s.run_id,goal=model.create_literal_goal(case['request'],str(run_dir/'workspace'),runtime_policy={RUN_LIFECYCLE_POLICY_KEY:run_lifecycle_policy_document('goal')}))
 bootstrap=render_bootstrap(model.direct_definitions(),model._assignment(initial,recent_limit=None));calls=[];consumed=set()
 for e in events:
  if e['type']!='model_session_generation_returned':continue
  raw=e['raw_generation'];start=starts[e['request_id']];cp=s.model_states[start['input_checkpoint_id']];chain=[]
  while cp:chain.append(cp);cp=s.model_states.get(cp.parent_checkpoint_id)
  assert chain[-1].transcript==bootstrap
  ids=[];seen=set()
  for cp in reversed(chain):
   assert len(cp.event_ids)==len(set(cp.event_ids))
   if cp.checkpoint_id in gens:ids.extend(gens[cp.checkpoint_id]['raw_token_ids'])
   else:
    if cp.parent_checkpoint_id:
     delta=set(cp.event_ids)-set(s.model_states[cp.parent_checkpoint_id].event_ids);assert len(delta)==1
     eid=next(iter(delta));assert eid not in seen;seen.add(eid)
     assert render_event_append(s.model_events[eid],previous_transcript=s.model_states[cp.parent_checkpoint_id].transcript)==cp.transcript
    ids.extend(tokenizer().encode(cp.transcript))
   assert cp.state_profile_id=='zero' and cp.state_profile_sha256=='0'*64
   assert cp.native_state_metadata['model_sha256']==reg['model_sha256']
   if cp.parent_checkpoint_id:assert cp.native_state_metadata['cache_binding']['parent_state_digest']==s.model_states[cp.parent_checkpoint_id].native_state_digest
  assert raw['prompt_token_ids']==[0]+ids
  assert start['input_digest']==s.model_states[start['input_checkpoint_id']].native_state_digest
  assert raw['sampling']==reg['sampling'] and raw['max_output_tokens']==1800
  consumed.update(seen)
  (p/'actual_inputs').mkdir(exist_ok=True)
  text=tokenizer().decode(ids);assert not re.search(r'(?:Assistant:|\*\*Tool Call:\*\*)\s*```json\n\s*\nUser:',text); (p/'actual_inputs'/f'{e["request_id"]}.txt').write_text(text)
  calls.append({'request':e['request_id'],'input_tokens':len(raw['prompt_token_ids']),'output_tokens':len(raw['raw_token_ids']),'input_sha256':hashlib.sha256(text.encode()).hexdigest(),'input_checkpoint':start['input_checkpoint_id'],'finish':raw['finish_reason'],'events':sorted(seen),'raw_output':raw['raw_output']})
 observations=[]
 for action in result['actions']:
  eid='EV-ACTION-'+action['action_id'];event=s.model_events.get(eid);item={'action':action['action_id'],'operation':action['action_type'],'event_registered':event is not None,'consumed':eid in consumed,'success':action['result']['success']}
  if action['result']['success'] and action['action_type']=='read_file':
   b=(run_dir/'workspace'/action['arguments']['path']).read_bytes();chunk=action['result']['metadata']['chunk']
   assert action['result']['output'].encode()==b[chunk['byte_start']:chunk['byte_end']]
   item['complete_file']=chunk['byte_start']==0 and chunk['byte_end']==len(b)
  if event:
   obs=event.payload['result']['observation'];item['projection_complete']=obs['projection_complete']
   if action['result']['success'] and action['action_type']=='read_file':
    b=(run_dir/'workspace'/action['arguments']['path']).read_bytes();chunk=action['result']['metadata']['chunk']
    assert action['result']['output'].encode()==b[chunk['byte_start']:chunk['byte_end']]
    assert ''.join(v['content'] for v in obs['exact_spans'])==action['result']['output']
    item['complete_file']=chunk['byte_start']==0 and chunk['byte_end']==len(b)
   if action['result']['success'] and action['action_type']=='search_text':
    out=json.loads(action['result']['output']);projected=event.payload['result']['structured_output'];assert projected['match_count']==out['match_count']
    for m in out['matches']:
     b=(run_dir/'workspace'/m['path']).read_bytes();raw=b[m['line_text_start_byte']:m['line_text_end_byte']]
     assert raw.decode()==m['line_text'] and hashlib.sha256(raw).hexdigest()==m['line_text_sha256']
     assert hashlib.sha256(b).hexdigest()==out['source_snapshots'][m['path']]
    for m in projected['matches']:assert any(m['path']==v['path'] and m['line_text']==v['line_text'] for v in out['matches'])
  observations.append(item)
 rejections=[{'event':key,'consumed':key in consumed,'payload':ev.payload} for key,ev in s.model_events.items() if ev.event_type=='protocol_rejection']
 rows.append({'run':run_dir.name,'calls':calls,'generation_started':len(starts),'generation_returned':len(calls),'input_and_state_verified':True,'observations':observations,'feedback':rejections,'protocol_rejections':s.protocol_rejections,'terminal_reasons':[v.payload.get('reason') for v in s.causal_records.values() if v.event_type in ('run_yielded','run_completed','run_interrupted')],'final':result['final']})
name=sys.argv[1] if len(sys.argv)>1 else 'MECHANICAL.json'
review.write_once(D/name,{'runs':rows,'completed_records':len(rows),'checked_generations':sum(len(r['calls']) for r in rows),'all_returned_inputs_and_parent_states_verified':True,'pending_events_at_budget_are_not_consumed_feedback':True})
print('audited',len(rows),'returned calls',sum(len(r['calls']) for r in rows))
