from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913'
from rwkv_lh.token_budget import tokenizer
from rwkv_lh.model_io import render_event_append
from rwkv_lh.schema import ModelEvent
rows=[]
prior=R/'data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913/runs/trial-2/model_trace.jsonl'
for d in ['correction_r4b','correction_r5','collection']:
 for p in sorted((P/d/'runs').iterdir()):
  state=json.loads((p/'state_snapshot.json').read_text());states=state['model_states'];ev=[json.loads(s) for s in (p/'model_trace.jsonl').read_text().splitlines()];previous=[json.loads(s) for s in prior.read_text().splitlines()] if p.name.startswith('continuation') else []
  generations={e['candidate_checkpoint_id']:e['raw_generation'] for e in [*previous,*ev] if e['type']=='model_session_generation_returned'};starts={e['request_id']:e for e in ev if e['type']=='model_session_generation_started'};calls=[]
  for e in ev:
   if e['type']!='model_session_generation_returned':continue
   raw=e['raw_generation'];start=starts[e['request_id']];cp=states[start['input_checkpoint_id']];chain=[]
   while cp:
    chain.append(cp);cp=states.get(cp['parent_checkpoint_id'])
   ids=[];seen=set()
   for cp in reversed(chain):
    if cp['checkpoint_id'] in generations:ids.extend(generations[cp['checkpoint_id']]['raw_token_ids'])
    else:
     if cp['parent_checkpoint_id']:
      parent=states[cp['parent_checkpoint_id']];delta=set(cp['event_ids'])-set(parent['event_ids']);assert len(delta)==1
      eventid=next(iter(delta));assert eventid not in seen;seen.add(eventid);event=ModelEvent.from_dict(state['model_events'][eventid]);assert render_event_append(event)==cp['transcript']
     ids.extend(tokenizer().encode(cp['transcript']))
    m=cp['native_state_metadata'];assert m['model_sha256']=='559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
    if cp['parent_checkpoint_id']:assert m['cache_binding']['parent_state_digest']==states[cp['parent_checkpoint_id']]['native_state_digest']
   assert raw['prompt_token_ids']==[0]+ids and start['input_digest']==states[start['input_checkpoint_id']]['native_state_digest']
   calls.append({'request_id':e['request_id'],'input_checkpoint_id':start['input_checkpoint_id'],'candidate_checkpoint_id':e['candidate_checkpoint_id'],'input_tokens':len(raw['prompt_token_ids']),'output_tokens':len(raw['raw_token_ids']),'finish_reason':raw['finish_reason'],'input_exact':True,'observations_once':True})
  r=json.loads((p/'RESULT.json').read_text());rows.append({'round':d,'run':p.name,'calls':calls,'termination':r['termination'],'submitted':r.get('final') is not None,'elapsed_seconds':r['elapsed_seconds'],'workspace_unchanged':r.get('workspace_unchanged'),'snapshot_status':state['status']})
(P/'DIAGNOSTIC_MECHANICAL_AUDIT.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('tasks',len(rows),'calls',sum(len(r['calls']) for r in rows))
