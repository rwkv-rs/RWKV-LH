"""R2 repairs only the missing-file fixture; scorer/model path remains R1."""
from pathlib import Path
import sys,json,copy,time
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R/'temp'));sys.path.insert(0,str(R/'scripts'))
import run_single_read_diagnostic_r1_20260912 as driver
from validate_single_read_fixture_r2_20260912 import validate_fixture
from run_rwkv_e2e_benchmark import materialize_workspace
D=R/'data/experiments/RWKV_SINGLE_READ_FIXTURE_REPAIR_R2_20260912'
if sys.argv[1]=='freeze':
 old=json.loads((driver.D/'REGISTRATION.json').read_text());c=copy.deepcopy(next(c for c in old['cases'] if c['id']=='missing-2'))
 taskpath=R/'benchmarks/rwkv_e2e/rwkv_real_project_dev_v1/tasks.json'
 catalog=json.loads(taskpath.read_text());task=next(t for t in catalog['tasks'] if t['task_id']==c['case'])
 source=D/'initial_workspace';materialize_workspace(task,source)
 c['workspace_source']=str(source.relative_to(R));c['workspace_sha256']=driver.inventory(source);validate_fixture(c,R)
 reg=copy.deepcopy(old);reg.update(round=D.name,created_at=time.time(),cases=[c],stop='3 independent generations maximum, same R1 scorer and sampling, 1800 tokens each, one hour wall time; no semantic retry',repair='R1 final snapshot contained index.html created after missing-file trace. R2 uses existing authored public task initial workspace; historical failure source unchanged.',source_task={'path':str(taskpath.relative_to(R)),'sha256':driver.sha(taskpath)},source_type='existing owner-authorized public initial workspace and R5 missing-file trace; controlled single-read diagnostic, not role training data',r1_invalid_case='missing-2; keep R1 original results without rescoring; exclude all 3 repetitions as fixture-invalid evidence')
 for p in [Path(__file__),R/'temp/validate_single_read_fixture_r2_20260912.py',R/'scripts/run_rwkv_e2e_benchmark.py']:reg['source_pins'][str(p.relative_to(R))]=driver.sha(p)
 assert not (D/'REGISTRATION.json').exists();driver.save(D/'REGISTRATION.json',reg);print('FROZEN',driver.sha(D/'REGISTRATION.json'),flush=True)
else:
 reg=json.loads((D/'REGISTRATION.json').read_text())
 for c in reg['cases']:validate_fixture(c,R)
 driver.D=D;driver.run()
