"""Continue pending cases from byte-identical isolated source, within original wall budget."""
from pathlib import Path
from datetime import datetime,timezone
import os,json,sys,time,signal,subprocess,hashlib,importlib.util
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-execute-coverage-a-local-20260911');O=R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911'
def write(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
def frozen_driver():
 spec=importlib.util.spec_from_file_location('frozen_a_driver',R/'temp/run_execute_coverage_a_20260911.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.ROOT=W
 sys.path=[str(W)]+[p for p in sys.path if p!=str(R) and p!=str(W)]
 return m
if len(sys.argv)>1:
 m=frozen_driver();m.case(sys.argv[1]);raise SystemExit(0)
# First two workers already passed the original frozen source guard. No reruns.
web_start=datetime.fromisoformat(json.loads((O/'RP-WEB-02.log').read_text().splitlines()[0])['at']).timestamp()
web_timeout=False
while not (O/'all_zero/RP-WEB-02.result.json').exists():
 if time.time()-web_start >= 1800:
  web_timeout=True;os.killpg(1469625,signal.SIGTERM);time.sleep(2)
  if Path('/proc/1469625/stat').exists() and Path('/proc/1469625/stat').read_text().split()[2]!='Z':os.killpg(1469625,signal.SIGKILL)
  break
 time.sleep(1)
while Path('/proc/1469625/stat').exists() and Path('/proc/1469625/stat').read_text().split()[2]!='Z':time.sleep(0.1)
os.kill(1467669,signal.SIGTERM);os.kill(1467669,signal.SIGCONT)
records=[json.loads((O/'RP-CLI-01.completion.json').read_text())]
web={'task_id':'RP-WEB-02','exit_code':(-15 if web_timeout else 0),'error':('preregistered_wall_budget_exhausted' if web_timeout else None),'wall_seconds':time.time()-web_start,'result_recorded':(O/'all_zero/RP-WEB-02.result.json').exists(),'completion_collector':'isolated continuation; original worker; same1800s deadline'}
write(O/'RP-WEB-02.completion.json',web);records.append(web)
started=datetime.fromisoformat(json.loads((O/'STARTED.json').read_text())['at']).timestamp()
for task in ['NEW-DIAG-01','NEW-DIAG-02']:
 budget=min(1800,7200-(time.time()-started))
 if budget<=0:records.append({'task_id':task,'started':False,'reason':'preregistered_total_wall_budget_exhausted'});continue
 before=time.monotonic();error=None
 with (O/f'{task}.log').open('x') as f:
  p=subprocess.Popen([sys.executable,str(Path(__file__)),task],cwd=W,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
  try:code=p.wait(timeout=budget)
  except subprocess.TimeoutExpired:
   error='preregistered_wall_budget_exhausted';os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
   code=p.returncode
 record={'task_id':task,'exit_code':code,'error':error,'wall_seconds':time.monotonic()-before,'result_recorded':(O/f'all_zero/{task}.result.json').exists(),'source_location':str(W)}
 write(O/f'{task}.completion.json',record);records.append(record);print(json.dumps(record),flush=True)
m=frozen_driver();benchmark,*_=m.configure()
write(O/'COMPLETION.json',{'cases':records,'wall_seconds':time.time()-started,'source_unchanged':benchmark._source_tree_manifest(W)==json.loads((O/'all_zero/source_tree_manifest.json').read_text()),'source_location_continuation_sha256':hashlib.sha256((O/'SOURCE_LOCATION_CONTINUATION.json').read_bytes()).hexdigest(),'optimizer_steps':0,'ended_at':datetime.now(timezone.utc).isoformat()})
