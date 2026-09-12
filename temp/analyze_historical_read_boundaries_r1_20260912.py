from pathlib import Path
import json,collections,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912'
rows=json.loads((D/'HISTORICAL_READS.json').read_text());counts=collections.Counter();checks=[]
for r in rows:
 a=r['action'];res=a['result'];args=a['arguments'];p=R/r['source'];file=p.parent/'workspace'/args['path'];entry={'case':r['case'],'action':a['action_id'],'path':args['path'],'source':r['source'],'snapshot_identity_matches':False,'result_matches_actual_bytes':None}
 if res['success']:
  artifact=next((x for x in res['artifacts'] if Path(x['path'])==Path(args['path'])),None)
  if file.is_file() and artifact and hashlib.sha256(file.read_bytes()).hexdigest()==artifact['sha256']:
   entry['snapshot_identity_matches']=True;b=file.read_bytes();m=res['metadata'];start=m['start_byte'];end=m['end_byte'];entry['result_matches_actual_bytes']=res['output'].encode()==b[start:end]
   counts['exact_eof' if start==len(b) else 'nonzero_interior' if start else 'from_zero']+=1
  else:counts['snapshot_unresolved']+=1
 else:counts['missing_file']+=1
 checks.append(entry)
base=R/'data/experiments/COORDINATOR_ATOMIC_ACTOR_STATE_ABLATION_R5_20260912';errors=collections.Counter();raw=[]
for arm in ['arm_b_atomic','arm_b_atomic_continuation']:
 for p in sorted((base/arm/'cases').glob('*/event_log.json')):
  for e in json.loads(p.read_text()):
   if e['type']=='model_call_rejected':
    d=e['data'];errors[d.get('error','')]+=1
    if 'read_file' in json.dumps(d.get('raw_generation',{})):raw.append({'case':p.parent.name,'event_id':e['event_id'],'error':d.get('error'),'raw_generation':d.get('raw_generation')})
out={'read_count':len(rows),'unique_case_path_offset':len(set((r['case'],r['action']['arguments']['path'],r['action']['arguments'].get('start_byte',0)) for r in rows)),'boundary_counts':dict(counts),'snapshot_exact_results':sum(x['result_matches_actual_bytes'] is True for x in checks),'checks':checks,'protocol_errors':dict(errors),'read_related_rejections':raw}
(D/'HISTORICAL_BOUNDARY_AUDIT.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print({k:v for k,v in out.items() if k not in ['checks','read_related_rejections','protocol_errors']});print('error groups',[(k[:180],v) for k,v in errors.most_common(8)])
