"""Evaluate the fixed two-arm criteria once, preserving raw scores and every length retry."""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';O=E/'EXECUTOR_OUTPUT_BUDGET_R1_20260910'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
p=read(O/'PREREGISTRATION.json'); arms=[]
for arm in p['arms_in_order']:
 folder=E/('EXECUTOR_OUTPUT_BUDGET_'+arm['id'].upper()+'_R1_20260910')
 completion=read(folder/'COMPLETION.json')
 subprocess.run([str(R/'.venv/bin/python'),str(R/'temp/summarize_current_official_round_20260910.py'),folder.name,'--seal'],cwd=R,check=True,capture_output=True)
 summary=read(folder/'AGENT_SUMMARY.json');counts=Counter();returned=Counter();tokens=Counter();commands=Counter();handoffs=[]
 for case in summary['cases']:
  task=case['task_id'];audit=read(Path(case['audit_path']))
  for ev in audit['model_trace']:
   if ev.get('model_role')!='executor_args':continue
   if ev.get('type')=='model_session_generation_started':counts[ev.get('max_tokens')]+=1
   if ev.get('type')=='model_session_generation_returned':
    returned[ev.get('finish_reason')]+=1
    raw=ev.get('raw_generation',{});usage=raw.get('usage',{}) if isinstance(raw,dict) else {}
    for k,v in usage.items():
     if isinstance(v,(int,float)):tokens[k]+=v
  for action in audit['action_ledger'].values():commands[action['action_type']]+=1
  h=folder/(task+'.HANDOFF_VERIFICATION.json')
  if not h.exists():subprocess.run([str(R/'.venv/bin/python'),str(R/'temp/verify_official_case_handoffs_r1_20260910.py'),folder.name,task],cwd=R,check=True,capture_output=True)
  handoffs.append(read(h))
 arms.append({'arm':arm['id'],'budget':arm['executor_max_output_tokens'],'summary':summary,'completion':completion,'actual_executor_max_tokens':dict(counts),'executor_finish_reasons':dict(returned),'executor_usage':dict(tokens),'action_types':dict(commands),'handoff_generation_contexts':sum(h['generation_contexts'] for h in handoffs),'handoff_role_inputs':sum(h['role_inputs'] for h in handoffs),'all_handoffs_verified':all(h['all_verified'] for h in handoffs),'source_manifest_sha256':sha(folder/'all_zero/source_tree_manifest.json'),'driver_sha256':read(folder/'REGISTRATION.json').get('driver_sha256'),'protocol_sha256':sha(folder/'all_zero/RUN_PROTOCOL.json')})
b,c=arms;ba=b['summary']['agent'];ca=c['summary']['agent'];bc=ba['executor_length'];cc=ca['executor_length'];bn=ba['executor_returned'];cn=ca['executor_returned']
complete=all(a['summary']['agent']['counts_complete'] and a['completion']['source_unchanged'] and all(x.get('exit_code')==0 and x.get('result_recorded') and not x.get('error') for x in a['completion']['cases']) for a in arms)
infra=all(a['summary']['agent']['supervisor_failures']==0 and a['summary']['agent']['runtime_transport_failures']==0 and a['summary']['agent']['native_first_errors']==0 and all(not row['native_transport_events'] for row in a['summary']['cases']) for a in arms)
passmap={r['task_id']:r['strict'] for r in b['summary']['cases']};regression=any(passmap[r['task_id']] and not r['strict'] for r in c['summary']['cases'])
gates={'complete_without_wall_exhaustion':complete,'no_infrastructure_failures':infra,'same_frozen_source':b['source_manifest_sha256']==c['source_manifest_sha256'],'all_handoffs_verified':all(a['all_handoffs_verified'] for a in arms),'effective_budget_binding':all(set(a['actual_executor_max_tokens'])=={a['budget']} for a in arms),'baseline_length_observed':bc>0,'length_count_at_most_half':cc*2<=bc,'length_rate_lower':bn>0 and cn>0 and cc*bn<bc*cn,'strict_not_degraded':ca['strict']>=ba['strict'] and not regression}
keep=all(gates.values());result={'preregistration_sha256':sha(O/'PREREGISTRATION.json'),'decision':'KEEP' if keep else 'NO_KEEP','criteria':gates,'arms':arms,'production_budget_changed':False,'optimizer_steps':0,'interpretation':'Two-task pilot only. No rerun or scoring adjustment; all outcomes retained. A zero baseline length or infrastructure interruption is inconclusive for the budget hypothesis.'}
write(O/'COMPARISON.json',result)
print(json.dumps({'decision':result['decision'],'gates':gates,'baseline':ba,'candidate':ca},ensure_ascii=False))
