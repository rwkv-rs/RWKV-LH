from pathlib import Path
import json, hashlib, collections, subprocess
R=Path('/home/chase/GitHub/RWKV-LH'); D=R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912';D.mkdir(exist_ok=True)
def save(n,x): (D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=subprocess.check_output(['git','diff','--name-only'],cwd=R,text=True).splitlines()
save('PREEXISTING_CHANGES.json',{'files':{p:sha(R/p) for p in files},'diff_sha256':hashlib.sha256(subprocess.check_output(['git','diff'],cwd=R)).hexdigest(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()})
base=R/'data/experiments/COORDINATOR_ATOMIC_ACTOR_STATE_ABLATION_R5_20260912'
rows=[]; counts=collections.Counter(); sources={}
for arm in ['arm_b_atomic','arm_b_atomic_continuation']:
 for p in sorted((base/arm/'cases').glob('*/event_log.json')):
  sources[str(p.relative_to(R))]=sha(p)
  for e in json.loads(p.read_text()):
   counts[e['type']]+=1
   if e['type']=='action_finished':
    a=e['data']['action']; counts['operation:'+a['action_type']]+=1
    if a['action_type']=='read_file':rows.append({'arm':arm,'case':p.parent.name,'event_id':e['event_id'],'action':a,'source':str(p.relative_to(R))})
save('HISTORICAL_READS.json',rows);save('HISTORICAL_AUDIT.json',{'sources':sources,'events':dict(counts),'read_count':len(rows),'read_success':sum(x['action']['result']['success'] for x in rows),'read_failures':[x for x in rows if not x['action']['result']['success']]})
print('COUNTS',dict(counts)); print('READS',len(rows),'success',sum(x['action']['result']['success'] for x in rows))
for x in rows:
 if not x['action']['result']['success']:print('FAIL',x['case'],x['action']['arguments'],x['action']['result']['error'])
c=json.loads((R/'temp/single_read_capabilities_r1_20260912.json').read_text());save('CAPABILITIES.json',c); print('CAPABILITY KEYS',list(c))
