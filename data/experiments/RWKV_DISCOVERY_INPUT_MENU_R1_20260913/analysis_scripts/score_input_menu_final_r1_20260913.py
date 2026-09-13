from pathlib import Path
import json,hashlib,collections
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
packets=json.loads((D/'DEV_REVIEW_PACKETS.json').read_text());assert len(packets)==16;labels=json.loads((D/'SUBMITTED_ANSWER_REVIEW.json').read_text())
mapping=json.loads((D/'DEV_REVIEW_MAPPING.json').read_text());mechanical={r['run']:r for r in json.loads((D/'DEV_MECHANICAL.json').read_text())};reviews=[];diags=[]
for p in packets:
 m=mechanical[mapping[p['id']]];reviews.append(dict(id=p['id'],run=m['run'],arm=m['arm'],repeat=m['repeat'],location=None,answer=0,fidelity=None,task_pass=False,false_work_completion=False,quality='无答案提交',note='未完成；不把中间工具成功当任务完成，最终事实忠实性不适用。'))
for v in reviews:
 if v['run'] not in labels:continue
 p=next(p for p in packets if mapping[p['id']]==v['run']);label=labels[v['run']];assert hashlib.sha256(p['final'].encode()).hexdigest()==label['answer_sha256'];v.update(label)
for p in packets:
 if p['final'] is not None:assert mapping[p['id']] in labels,'Unreviewed final'
for m in mechanical.values():
 p=D/'dev'/m['run'];r=json.loads((p/'RESULT.json').read_text());gs=[e['raw_generation'] for e in map(json.loads,(p/'model_trace.jsonl').read_text().splitlines()) if e['type']=='model_session_generation_returned'];counts=collections.Counter((a['action_type'],json.dumps(a['wire_arguments'],sort_keys=True)) for a in r['actions']);diags.append(dict(run=m['run'],arm=m['arm'],repeat=m['repeat'],termination=r['termination'],error=r['error'],length_stops=sum(g['finish_reason']=='length' for g in gs),unknown_parameter_rejection=bool(r['error'] and 'unknown arguments' in r['error']),successful_tools=sum(a['result']['success'] for a in r['actions']),empty_searches=sum(a['action_type']=='search_text' and a['result']['success'] and json.loads(a['result']['output'])['match_count']==0 for a in r['actions']),max_identical_call_count=max(counts.values(),default=0),tool_sequence=[a['action_type'] for a in r['actions']]))
summary={};resources={}
for a in ['full','readonly']:
 ms=[m for m in mechanical.values() if m['arm']==a];ds=[d for d in diags if d['arm']==a];summary[a]=dict(tasks=len(ms),task_pass=sum(v['task_pass'] for v in reviews if v['arm']==a),submitted=sum(m['submitted'] for m in ms),mutation=sum(not m['workspace_unchanged'] for m in ms),false_work_completion=0,terminations=dict(collections.Counter(m['termination'] for m in ms)),input_state_verified=all(m['input_and_state_verified'] for m in ms),complete_target_read=sum(m['complete_read'] for m in ms),length_stops=sum(d['length_stops'] for d in ds),unknown_parameter_rejections=sum(d['unknown_parameter_rejection'] for d in ds),successful_tools=sum(d['successful_tools'] for d in ds));resources[a]=dict(generated_calls=sum(len(m['calls']) for m in ms),input_tokens_full_logical=sum(c['input_tokens'] for m in ms for c in m['calls']),output_tokens=sum(c['output_tokens'] for m in ms for c in m['calls']),elapsed_seconds=sum(m['elapsed_seconds'] for m in ms),strong_calls=0,optimizer_steps=0,cost_money=None,peak_gpu_memory=None)
for name,x in [('REVIEWS.json',reviews),('DIAGNOSTICS.json',diags),('SUMMARY.json',summary),('RESOURCES.json',resources),('GATE.json',dict(passed=False,reason='Neither arm meets two repetitions each4/4 with zero illegal parameters; one useful submission is insufficient for fixed-group stability or broad causal attribution; no production retention or training'))]:
 p=D/name;assert not p.exists();p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print(summary);print(resources)
