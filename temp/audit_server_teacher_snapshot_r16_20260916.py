from pathlib import Path
import json,hashlib,time
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_SERVER_TEACHER_R16_20260916';S=D/'server_snapshot'
rows=[];calls=prompt=completion=0
for root in sorted((S/'runs').iterdir()):
 events=[json.loads(l) for l in (root/'execution/strong_trace.jsonl').read_text().splitlines()]
 envelopes=[e['raw_response'] for e in events if e.get('type')=='supervisor_response_envelope_received']
 for e in envelopes:
  assert len(e['prompt_token_ids'])==e['usage']['prompt_tokens']
  assert len(e['choices'][0]['token_ids'])==e['usage']['completion_tokens']
  calls+=1;prompt+=len(e['prompt_token_ids']);completion+=len(e['choices'][0]['token_ids'])
 v={'id':root.name,'returned_calls':len(envelopes),'completed':False}
 if (root/'DELIVERY.json').exists():
  d=json.loads((root/'DELIVERY.json').read_text());res=d['result']
  v.update(completed=True,termination=res['termination'],termination_reason=res['termination_reason'],artifact_passed=d['external_artifact']['passed'],generation_started=res['generation_started'],protocol_rejections=res['protocol_rejections'],actions=res['actions'],semantic_review=d['semantic_review'],training_admitted=d['training_admitted'])
 rows.append(v)
out={'snapshot_time':time.time(),'status':json.loads((S/'STATUS.json').read_text()),'finished':sum(r['completed'] for r in rows),'artifact_passed':sum(r.get('artifact_passed',False) for r in rows),'returned_calls':calls,'exact_prompt_tokens':prompt,'exact_output_tokens':completion,'tasks':rows,'project_strict':'not_measured','training_admitted':0}
(D/'SNAPSHOT_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('tasks','status')},ensure_ascii=False))
