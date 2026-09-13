from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
phases=['','budget_probe','file_scope_probe','requested_advice_probe','advice_label_probe'];rows=[];seen=set();tokens=[0,0];strong=[]
for phase in phases:
 P=D/phase;calls=[];integrity=[]
 for p in sorted((P/'runs').glob('*/execution/RESULT.json')):
  e=p.parent;s=json.loads((e/'state_snapshot.json').read_text());r=json.loads(p.read_text());ws=Path(s['goal']['workspace_root']);cid=p.parent.parent.name.rsplit('-',2)[0]
  reg=json.loads((P/'REGISTRATION.json').read_text());case=next(x for x in reg['cases'] if x['id']==cid)
  if isinstance(case['files'],dict):expected=case['files']
  else:raise ValueError('unexpected source manifest')
  actual={str(f.relative_to(ws)):hashlib.sha256(f.read_bytes()).hexdigest() for f in ws.rglob('*') if f.is_file()}
  assert actual==expected,(phase,cid,actual,expected)
  integrity.append(dict(run=p.parent.parent.name,source_unchanged=True))
  for line in (e/'model_trace.jsonl').read_text().splitlines():
   event=json.loads(line)
   if event['type']=='model_session_generation_returned':
    assert event['request_id'] not in seen;seen.add(event['request_id']);raw=event['raw_generation'];tokens[0]+=len(raw['prompt_token_ids']);tokens[1]+=len(raw['raw_token_ids']);calls.append(event['request_id'])
 rows.append(dict(phase=phase or 'baseline',tasks=len(integrity),returned_calls=len(calls),workspace_checks=integrity))
for p in sorted((D/'requested_advice_probe/runs').glob('*/advice/strong_trace.jsonl')):
 for line in p.read_text().splitlines():
  e=json.loads(line)
  if e['type']=='supervisor_request_returned':strong.append(dict(run=p.parent.parent.name,call_id=e['call_id'],model=e['model'],usage=e['usage'],latency_ms=e['latency_ms'],http_attempts=e['http_attempts'],trace=str(p.relative_to(D))))
result=dict(phases=rows,mutation_count=0,rwkv_returned_calls=len(seen),rwkv_logical_input_tokens=tokens[0],rwkv_output_tokens=tokens[1],strong_calls=strong,strong_total_tokens=sum(x['usage']['total_tokens'] for x in strong),strong_prompt_tokens=sum(x['usage']['prompt_tokens'] for x in strong),strong_completion_tokens=sum(x['usage']['completion_tokens'] for x in strong),cost_currency=None,peak_resources=None,resource_measurement_limit='未采集独占峰值、实际单价和完整服务资源，逻辑输入token不等于native增量计算量；不得推断成本收益',deduplication='只计各execution当前trace；复核父调用不重复计，标签对照复用六份strong receipt不新增调用')
(D/'FINAL_ACCOUNTING.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['phases','strong_calls']})
