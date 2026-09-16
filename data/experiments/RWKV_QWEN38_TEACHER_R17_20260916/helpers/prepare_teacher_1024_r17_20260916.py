from pathlib import Path
import sys,json,hashlib,sqlite3,shutil,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.direct_trace_data import replay_run
from rwkv_lh.correction_snapshots import validate_generation_snapshot
D=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916';B=D/'bulk_deployment';REMOTE=Path('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
B.mkdir(parents=True,exist_ok=True);shutil.copytree(R/'rwkv_lh',B/'rwkv_lh',ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=True)
original20=json.loads((D/'deployment/TASK_SELECTION.json').read_text())['tasks'];byid={r['id']:r for r in original20}
records=[]
for name in ['RWKV_DUAL_COLLECTION_R10_20260916','RWKV_COLLECTION_R13_20260916']:
 for p in sorted((R/'data/experiments'/name/'campaign/batches').glob('rl*/queue.sqlite3')):
  with sqlite3.connect(f'file:{p}?mode=ro',uri=True) as db:records.extend(json.loads(r[0]) for r in db.execute("select result from tasks where status='recorded'"))
assert len(records)==len({r['id'] for r in records})==1024,len(records)
records.sort(key=lambda x:(x['id'] not in byid, list(byid).index(x['id']) if x['id'] in byid else x['id']))
rows=[]
for n,record in enumerate(records):
 dest=B/'inputs'/record['id'];dest.mkdir(parents=True,exist_ok=True)
 if record['id'] in byid:
  row=dict(byid[record['id']]['original_binding']);old=R/'data/experiments/RWKV_LOCAL_TEACHER_PILOT_R15_20260916/sources'/row['id'];actual=json.loads((old/'INPUT.json').read_text());audit=json.loads((old/'SOURCE_AUDIT.json').read_text());root=Path(row['source_root']);seal=Path(row['manifest']);before=Path(row['snapshot']);manifest=json.loads(seal.read_text())
 else:
  if 'storage_retirement' in record:
   seal=Path(record['storage_retirement']['evidence'])/'MANIFEST.json'
  else:
   retirement=R/'data/experiments/RWKV_STATE_LIFECYCLE_R12_20260916';relative='sealed/'+record['id']+'/MANIFEST.json';seal=retirement/relative
   assert sha(seal)==json.loads((retirement/'RETIREMENT_EVIDENCE_INDEX.json').read_text())[relative]
  manifest=json.loads(seal.read_text());root=Path(manifest['run_root']);replay=replay_run(root,manifest['model_sha256']);assert replay
  cp,actual=list(replay.items())[-1];before=validate_generation_snapshot(root,actual,manifest['source_files'])
  row={'id':record['id'],'stratum':record['termination_reason'],'source_root':str(root),'manifest':str(seal),'manifest_sha256':sha(seal),'checkpoint':cp,'request_id':actual['request_id'],'snapshot':str(before),'input_sha256':hashlib.sha256(actual['input_text'].encode()).hexdigest(),'source_result_sha256':sha(root/'RESULT.json'),'conversion':str(root.parent.parent/'item.json')}
  audit=dict(row,original_output=actual['raw_generation']['raw_output'])
 save(dest/'INPUT.json',actual);save(dest/'SOURCE_AUDIT.json',audit);save(dest/'COLLECTION_RESULT.json',record);shutil.copy2(seal,dest/'MANIFEST.json')
 for name,digest in manifest['source_files'].items():
  p=root/name;assert sha(p)==digest,(record['id'],name)
  out=dest/'original'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
 rel=before.relative_to(root);shutil.copytree(before,dest/'original'/rel,dirs_exist_ok=True)
 item=json.loads(Path(row['conversion']).read_text());shutil.copy2(row['conversion'],dest/'ORIGINAL_ITEM.json');shutil.copy2(item['acceptance_path'],dest/'acceptance.json');assert sha(dest/'acceptance.json')==item['acceptance_sha256'];item['acceptance_path']=str(REMOTE/'inputs'/row['id']/'acceptance.json');save(dest/'ITEM.json',item)
 rows.append(dict(row,source_root=str(REMOTE/'inputs'/row['id']/'original'),manifest=str(REMOTE/'inputs'/row['id']/'MANIFEST.json'),snapshot=str(REMOTE/'inputs'/row['id']/'original'/rel),conversion=str(REMOTE/'inputs'/row['id']/'ITEM.json'),original_binding=row,collection_artifact_passed=record['external_acceptance']['status']=='passed'))
 if (n+1)%32==0:print('prepared',n+1,flush=True)
save(B/'TASK_SELECTION.json',{'tasks':rows,'selection':'all1024 R10+R13 RL source IDs exactly once; original20 source boundaries preserved, remainder latest verified generation snapshot; not SFT','known_collection_artifact_passed':sum(r['collection_artifact_passed'] for r in rows)})
(B/'temp').mkdir(exist_ok=True);runner=(R/'temp/run_teacher_r17_20260916.py').read_text()
runner=runner.replace(" save(root/'BASELINE.json',verify_python_submission(workspace,contract['cases']))",""" baseline=verify_python_submission(workspace,contract['cases']);save(root/'BASELINE.json',baseline)
 if baseline['passed']:
  result={'id':'TEACHER-'+row['id'],'termination':'existing_artifact','termination_reason':'existing_artifact_passed_pending_semantic_review','execution_authority':'source_rwkv','generation_started':0,'actions':[]}
  save(root/'DELIVERY.json',{'result':result,'external_artifact':baseline,'final_tree':tree_identity(workspace),'semantic_review':'pending','training_admitted':False});return result""")
(B/'temp/run_teacher_r17_20260916.py').write_text(runner);shutil.copy2(R/'temp/run_teacher_1024_r17_20260916.py',B/'temp/run_teacher_1024_r17_20260916.py')
reg=json.loads((D/'REGISTRATION.json').read_text());reg.update(scope='all1024 RL owner explicit authorization',task_ids=[r['id'] for r in rows],workers=2,stop='1024 dispositions or infrastructure error or owner stop; no automatic retry of interrupted work',prior20='stopped while waiting_for_model, no teacher generations; same original20 source boundaries included here');save(B/'REGISTRATION.json',reg);save(D/'BULK_REGISTRATION.json',reg)
files={str(p.relative_to(B)):sha(p) for p in sorted(B.rglob('*')) if p.is_file() and p.name!='FILES.json'};save(B/'FILES.json',{'files':files});save(D/'BULK_DEPLOYMENT_IDENTITY.json',{'remote_root':str(REMOTE),'manifest_sha256':sha(B/'FILES.json'),'files':len(files),'bytes':sum(p.stat().st_size for p in B.rglob('*') if p.is_file())});print('ALL1024 READY',flush=True)
