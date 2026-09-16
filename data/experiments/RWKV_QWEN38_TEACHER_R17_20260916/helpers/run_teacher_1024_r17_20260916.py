from pathlib import Path
import sys,json,time,hashlib,os,multiprocessing,traceback,shutil
import requests
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R));sys.path.insert(0,str(R/'temp'))
from rwkv_lh.collection_queue import CollectionQueue
import run_teacher_r17_20260916 as teacher
Q=R/'outputs/queue.sqlite3';S=R/'outputs/STATUS.json'
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def worker(number,stop):
 try:
  with CollectionQueue(Q) as queue:
   while not stop.is_set():
    if shutil.disk_usage(R).free<64*1024**3:raise RuntimeError('64GiB free-space reserve reached; stop dispatch')
    item=queue.claim()
    if item is None:return
    row=item['teacher_source'];save(R/'outputs'/f'worker{number}.json',{'phase':'executing','id':row['id'],'time':time.time()})
    result=teacher.run(row)
    delivery=R/'outputs/runs'/row['id']/'DELIVERY.json'
    queue.finish(item['source_id'],{'id':item['job']['task_id'],'termination':result['termination'],'termination_reason':result['termination_reason'],'delivery':str(delivery),'delivery_sha256':hashlib.sha256(delivery.read_bytes()).hexdigest(),'training_admitted':False})
    if result['termination']=='error':raise RuntimeError('infrastructure error; inspect '+row['id'])
    save(R/'outputs'/f'worker{number}.json',{'phase':'recorded','id':row['id'],'time':time.time()})
 except BaseException as exc:
  stop.set();save(R/'outputs'/f'worker{number}.json',{'phase':'blocked','error':repr(exc),'traceback':traceback.format_exc(),'time':time.time()});raise

def main():
 for name,digest in json.loads((R/'FILES.json').read_text())['files'].items():
  if hashlib.sha256((R/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen file mismatch '+name)
 reg=json.loads((R/'REGISTRATION.json').read_text());rows=json.loads((R/'TASK_SELECTION.json').read_text())['tasks'];assert len(rows)==1024
 S.parent.mkdir(parents=True,exist_ok=True)
 with CollectionQueue(Q) as queue:
  if not queue.counts():
   for row in rows:
    item=json.loads(Path(row['conversion']).read_text());item['teacher_source']=row;item['job']['task_id']='TEACHER-'+row['id'];queue.admit(item)
  queue.seal({'manifest_sha256':hashlib.sha256((R/'FILES.json').read_bytes()).hexdigest(),'registration':reg})
  if queue.counts().get('running',0):raise RuntimeError('unfinished running tasks require explicit trace reconciliation; no automatic retry')
 session=requests.Session();session.trust_env=False
 for _ in range(720):
  try:
   r=session.get('http://127.0.0.1:18244/v1/models',timeout=5);r.raise_for_status()
   assert any(m['id']=='qwen3.8-27b-r17' and m['max_model_len']==262144 for m in r.json()['data'])
   model=json.loads(Path('/home/chase/GitHub/RWKV-LH-teacher-r17-20260916/MODEL_MANIFEST.json').read_text());assert model['revision']==reg['revision'];break
  except requests.RequestException:
   save(S,{'phase':'waiting_for_model','total':1024,'generation_started':False,'time':time.time()});time.sleep(10)
 else:raise RuntimeError('model readiness deadline exhausted')
 session.close()
 context=multiprocessing.get_context('spawn');stop=context.Event();workers=[context.Process(target=worker,args=(i,stop)) for i in range(2)]
 for p in workers:p.start()
 while any(p.is_alive() for p in workers):
  if any(p.exitcode not in (None,0) for p in workers):stop.set()
  with CollectionQueue(Q) as queue:counts=queue.counts()
  save(S,{'phase':'draining_after_error' if stop.is_set() else 'correcting','total':1024,'counts':counts,'time':time.time(),'workers':2,'training_admitted':0})
  time.sleep(5)
 for p in workers:p.join()
 with CollectionQueue(Q) as queue:counts=queue.counts()
 good=counts.get('recorded',0)==1024 and all(p.exitcode==0 for p in workers)
 save(S,{'phase':'complete_pending_semantic_review' if good else 'blocked','total':1024,'counts':counts,'time':time.time(),'training_admitted':0})
 if not good:raise RuntimeError('campaign blocked; unfinished tasks preserved')
if __name__=='__main__':
 try:main()
 except BaseException as exc:
  previous=json.loads(S.read_text()) if S.exists() else {};save(S,{**previous,'phase':'blocked','error':repr(exc),'traceback':traceback.format_exc(),'time':time.time()});raise
