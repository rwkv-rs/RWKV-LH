from pathlib import Path
import json,hashlib,subprocess,collections,sqlite3,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.store import LongHorizonStore
O=R/'data/experiments/R126_CURRENT_REGRESSION_REVIEW_R1_20260911';O.mkdir(exist_ok=True)
C=R/'data/experiments/FULL_TRACE_COLLECTION_R1_20260911';H='50754a2c'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def old(p):return subprocess.check_output(['git','show',H+':'+p],cwd=R)
refs=[]
for p in ['data/experiments/Round126_v19p1_full90/REPORT.md','data/experiments/Round126_V19P1_BOOTSTRAP_REQUEST_LAST_ADJACENCY_PROTOCOL.md','data/experiments/Round126_v19p1_full90/MANUAL_CAUSAL_ANALYSIS.md','rwkv_lh/model.py','scripts/run_rwkv_e2e_benchmark.py']:
 b=old(p);refs.append({'commit':H,'path':p,'sha256':sha(b),'bytes':len(b)})
write('HISTORICAL_SOURCES.json',refs)
comparisons=[]
for suite in ['rwkv_e2e_30','rwkv_e2e_extension48','rwkv_e2e_lh12']:
 tp=f'benchmarks/rwkv_e2e/{suite}/tasks.json';ap=f'benchmarks/rwkv_e2e/{suite}/acceptance.json';ot=json.loads(old(tp));nt=json.loads((R/tp).read_text());oa=json.loads(old(ap));na=json.loads((R/ap).read_text());nt={t['task_id']:t for t in nt['tasks']}
 for t in ot['tasks']:
  n=nt[t['task_id']];a=oa['cases'][t['task_id']];b=na['cases'][t['task_id']]
  comparisons.append({'task_id':t['task_id'],'task_equal':t==n,'changed_task_fields':[k for k in set(t)|set(n) if t.get(k)!=n.get(k)],'acceptance_equal':a==b,'changed_acceptance_fields':[k for k in set(a)|set(b) if a.get(k)!=b.get(k)]})
write('TASK_COMPARISON_90.json',comparisons)
ids=[v['task_id'] for v in json.loads((C/'PROGRESS.json').read_text())['cases']][:20];assert len(ids)==20
rows=[];counts=collections.Counter();ops=collections.Counter();err=collections.Counter();auditverdicts=collections.Counter();sourcepins=[]
for id in ids:
 root=C/'all_zero/cases'/id;rp=C/'all_zero'/f'{id}.result.json';res=json.loads(rp.read_text());sourcepins.append({'path':str(rp),'sha256':sha(rp.read_bytes())})
 # Completed immutable exported events, not live databases.
 ep=root/'event_log.json';raw=ep.read_bytes();events=json.loads(raw);sourcepins.append({'path':str(ep),'sha256':sha(raw)})
 if isinstance(events,dict):events=events.get('events',[])
 row={'task_id':id,'result':res,'actions':[],'selections':[],'audits':[],'plans':[],'rejections':[],'termination':[]}
 for ev in events:
  typ=ev.get('type',ev.get('event_type'));v=ev.get('data',ev)
  if 'payload' in v:v=v['payload']
  if typ=='action_finished':
   a=v['action'];args=a.get('arguments',{});action={k:a.get(k) for k in ['action_id','action_type','status','outcome_type','error','workspace_digest_before','workspace_digest_after']};action['arguments']=args;action['identical_result_count']=v.get('identical_result_count');action['result_metadata']=(a.get('result') or {}).get('metadata');row['actions'].append(action);ops[a['action_type']]+=1
  elif typ=='exact_tool_selection_staged':
   sel=v.get('selection',{});row['selections'].append({'selected_operation':v.get('selected_operation'),'selection_keys':list(sel),'selection_id':v.get('selection_id')})
  elif typ in ['goal_audit_accepted','goal_audit_rejected']:
   a={k:v.get(k) for k in ['audit','feedback','error','boundary','request_id','audit_id']};a['type']=typ;row['audits'].append(a)
   if typ=='goal_audit_rejected':err[str(v.get('error'))]+=1
   else:auditverdicts[v.get('audit',{}).get('verdict')]+=1
  elif typ=='goal_audit_recorded':
   g=v.get('raw_generation',{});row.setdefault('audit_outputs',[]).append({'request_id':v.get('request_id'),'raw_output':g.get('raw_output'),'audit':v.get('audit')})
  elif typ in ['run_blocked','run_completed']:row['termination'].append(v);counts[v.get('reason',typ)]+=1
  elif typ=='goal_plan_patch_committed':row['plans'].append(v)
  elif typ=='protocol_rejection_recorded':row['rejections'].append(v)
 rows.append(row)
write('CURRENT_20_CASE_ANALYSIS.json',rows);write('SOURCE_PINS.json',sourcepins)
summary={'snapshot_case_count':len(rows),'strict':sum(r['result']['passed'] for r in rows),'completed':sum(r['result']['agent_completed'] for r in rows),'external_passed':sum(r['result']['external_passed'] for r in rows),'actions':sum(len(r['actions']) for r in rows),'mutating_actions':sum(bool(a['workspace_digest_before'] and a['workspace_digest_after'] and a['workspace_digest_before']!=a['workspace_digest_after']) for r in rows for a in r['actions']),'terminations':dict(counts),'operations':dict(ops),'audit_rejection_errors':dict(err),'accepted_audit_verdicts':dict(auditverdicts),'common_90_task_count':sum(r['task_id'] in {t['task_id'] for t in comparisons} for r in rows),'task_equal_90':sum(t['task_equal'] for t in comparisons),'acceptance_equal_90':sum(t['acceptance_equal'] for t in comparisons)}
write('SUMMARY.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
