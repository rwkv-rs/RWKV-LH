from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';calls=[];strong=[]
for folder in ['correction_r4b','correction_r5','collection']:
 for p in (P/folder).glob('runs/*/model_trace.jsonl'):
  for line in p.read_text().splitlines():
   e=json.loads(line)
   if e['type']=='model_session_generation_returned':g=e['raw_generation'];calls.append({'path':str(p.relative_to(P)),'input_tokens':len(g['prompt_token_ids']),'output_tokens':len(g['raw_token_ids']),'finish':g['finish_reason']})
for folder in ['curation','curation_review_r2']:
 for p in (P/folder).rglob('strong_trace.jsonl'):
  for line in p.read_text().splitlines():
   e=json.loads(line)
   if e['type']=='supervisor_response_envelope_received':strong.append({'path':str(p.relative_to(P)),'call_id':e['call_id'],'usage':e['usage'],'finish_reason':e['finish_reason'],'latency_ms':e['latency_ms']})
result={'rwkv_calls':len(calls),'input_tokens_full_logical_context':sum(c['input_tokens'] for c in calls),'output_tokens_exact':sum(c['output_tokens'] for c in calls),'rwkv_calls_detail':calls,'strong_responses':len(strong),'strong_details':strong,'optimizer_steps_before_training':0,'cost_money':None,'cost_note':'No price/billing attestation; full logical input token lengths are not incremental recurrent prefill compute; teacher failures included; do not infer qualified-task cost savings.'};(P/'PRETRAINING_RESOURCE_LEDGER.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['rwkv_calls_detail','strong_details']})
