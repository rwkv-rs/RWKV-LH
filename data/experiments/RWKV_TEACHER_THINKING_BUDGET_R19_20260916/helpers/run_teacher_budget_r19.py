from pathlib import Path
import sys,os,json,hashlib,multiprocessing,time
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'temp'));import run_teacher_r17_20260916 as teacher

def work(row,budget):
 os.environ['TEACHER_THINKING_BUDGET']=str(budget);teacher.run(row)
if __name__=='__main__':
 for name,digest in json.loads((R/'FILES.json').read_text())['files'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,name
 rows=json.loads((R/'TASK_SELECTION.json').read_text())['tasks']
 for budget in (2048,4096):
  ps=[multiprocessing.get_context('spawn').Process(target=work,args=(row,budget)) for row in rows]
  for p in ps:p.start()
  for p in ps:p.join()
  assert all(p.exitcode==0 for p in ps)
 (R/'DONE.json').write_text(json.dumps({'time':time.time(),'phase':'awaiting_external_review'}))
