from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation_r2';sys.path.insert(0,str(P/'training_runtime/source_r2'))
from rwkv_lh.token_budget import tokenizer
from rwkv_lh.model_io import render_event_append,render_bootstrap
from rwkv_lh.schema import ModelEvent,RunState
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.harness import ActionHarness

def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha_text(t):return hashlib.sha256(t.encode()).hexdigest()
reg=json.loads((D/'RUN_REGISTRATION.json').read_text());er=json.loads((D/'REGRESSION_REGISTRATION.json').read_text());cases={c['id']:c for c in er['cases']};split=sys.argv[1];rows=[];packets=[];mapping={}
for p in sorted((D/split).iterdir()):
 r=json.loads((p/'RESULT.json').read_text());s=RunState.from_dict(json.loads((p/'state_snapshot.json').read_text()));c=cases[r['file_id']];source=(p/'workspace'/c['path']).read_text();assert sha_text(source)==c['source_content_sha256'];events=[json.loads(l) for l in (p/'model_trace.jsonl').read_text().splitlines()];gens={e['candidate_checkpoint_id']:e['raw_generation'] for e in events if e['type']=='model_session_generation_returned'};starts={e['request_id']:e for e in events if e['type']=='model_session_generation_started'};model=LongHorizonModel(ModelSession(client=object(),settings=RuntimeSettings(base_url='http://unused.invalid',api_key='',model='replay-only',tool_disclosure_mode='full')),harness=ActionHarness());goal=model.create_literal_goal(c['request'],str(p/'workspace'));initial=RunState(run_id=s.run_id,goal=goal);bootstrap=render_bootstrap(model.direct_definitions(),model._assignment(initial,recent_limit=None));profile=reg['profiles'][r['arm']];calls=[]
 for e in events:
  if e['type']!='model_session_generation_returned':continue
  raw=e['raw_generation'];start=starts[e['request_id']];cp=s.model_states[start['input_checkpoint_id']];chain=[]
  while cp:chain.append(cp);cp=s.model_states.get(cp.parent_checkpoint_id)
  assert chain[-1].transcript==bootstrap;ids=[];seen=set()
  for cp in reversed(chain):
   if cp.checkpoint_id in gens:ids.extend(gens[cp.checkpoint_id]['raw_token_ids'])
   else:
    if cp.parent_checkpoint_id:
     delta=set(cp.event_ids)-set(s.model_states[cp.parent_checkpoint_id].event_ids);assert len(delta)==1;eid=next(iter(delta));assert eid not in seen;seen.add(eid);assert render_event_append(s.model_events[eid])==cp.transcript
    ids.extend(tokenizer().encode(cp.transcript))
   assert cp.state_profile_id==profile['id'] and cp.state_profile_sha256==profile['sha256'];m=cp.native_state_metadata;assert m['model_sha256']==reg['model_sha256']
   if cp.parent_checkpoint_id:assert m['cache_binding']['parent_state_digest']==s.model_states[cp.parent_checkpoint_id].native_state_digest
  assert raw['prompt_token_ids']==[0]+ids and start['input_digest']==s.model_states[start['input_checkpoint_id']].native_state_digest;assert raw['sampling']==er['sampling'];assert raw['max_output_tokens']==er['max_output_tokens'];calls.append({'input_tokens':len(raw['prompt_token_ids']),'output_tokens':len(raw['raw_token_ids']),'finish':raw['finish_reason'],'request_id':e['request_id'],'input_checkpoint':start['input_checkpoint_id'],'candidate_checkpoint':e['candidate_checkpoint_id'],'actual_input_sha256':sha_text(tokenizer().decode(ids))})
 reads=[]
 for n,a in enumerate(r['actions'],1):
  ev=json.loads((p/f'observation_{n}.json').read_text());obs=ev['payload']['result'].get('observation',{});text=''.join(x['content'] for x in obs.get('exact_spans',[]));reads.append(a['action_type']=='read_file' and a['arguments'].get('path')==c['path'] and a['result'].get('success') is True and a['result']['output']==source and text==source and obs.get('projection_complete') is True)
 key=sha_text('candidate-task-r2:'+p.name)[:12];mapping[key]=p.name;packets.append({'id':key,'task':c['request'],'file':source,'anchors':c['semantic_anchors'],'final':r['final']});rows.append({'run':p.name,'arm':r['arm'],'repeat':r['repeat'],'file_id':c['id'],'input_and_state_verified':True,'complete_read':any(reads),'read_calls':sum(a['action_type']=='read_file' for a in r['actions']),'tool_calls':len(r['actions']),'calls':calls,'submitted':r['final'] is not None,'termination':r['termination'],'workspace_unchanged':r['workspace_unchanged'],'elapsed_seconds':r['elapsed_seconds']})
pairs={}
for r in rows:
 if r['calls']:
  key=(r['file_id'],r['repeat']);digest=r['calls'][0]['actual_input_sha256'];assert key not in pairs or pairs[key]==digest,'initial arm inputs differ';pairs[key]=digest
save(D/(split.upper()+'_MECHANICAL.json'),rows);save(D/(split.upper()+'_REVIEW_MAPPING.json'),mapping);save(D/(split.upper()+'_REVIEW_PACKETS.json'),sorted(packets,key=lambda x:x['id']));print('audited',len(rows),'calls',sum(len(r['calls']) for r in rows))
