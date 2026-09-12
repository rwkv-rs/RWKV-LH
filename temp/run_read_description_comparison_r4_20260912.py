"""Before/after frozen clients, same R1 single-read runner and scoring."""
from pathlib import Path
import sys,json,hashlib,shutil,time,ast
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_READ_PARAMETER_DESCRIPTION_R4_20260912'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def stripped_ast(path):
 tree=ast.parse(path.read_text())
 for n in ast.walk(tree):
  if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='ActionDefinition' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='read_file':
   n.args[1]=ast.Constant(value='')
   for v in n.args[6].values:
    pairs=[(k,x) for k,x in zip(v.keys,v.values) if not (isinstance(k,ast.Constant) and k.value=='description')]
    v.keys=[k for k,x in pairs];v.values=[x for k,x in pairs]
 return ast.dump(tree)
if sys.argv[1]=='freeze':
 sys.path.insert(0,str(R/'temp'))
 from validate_single_read_fixture_r2_20260912 import validate_fixture
 before=D/'frozen_before';after=D/'frozen_after'
 shutil.copytree(R/'rwkv_lh',after/'rwkv_lh',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 b=inventory(before);a=inventory(after)
 assert set(a)==set(b)
 assert [p for p in a if a[p]!=b[p]]==['rwkv_lh/harness.py']
 assert stripped_ast(before/'rwkv_lh/harness.py')==stripped_ast(after/'rwkv_lh/harness.py')
 save(D/'SOURCE_AFTER.json',a)
 one=json.loads((R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912/REGISTRATION.json').read_text());two=json.loads((R/'data/experiments/RWKV_SINGLE_READ_FIXTURE_REPAIR_R2_20260912/REGISTRATION.json').read_text())
 cases=[{**c,'suite':'primary_r1_valid7'} for c in one['cases'] if c['id']!='missing-2']+[{**c,'suite':'supplement_r2_missing1'} for c in two['cases']]
 for c in cases:
  validate_fixture(c,R);assert inventory(R/c['workspace_source'])==c['workspace_sha256']
 pins={str(p.relative_to(R)):sha(p) for p in sorted((R/'rwkv_lh').rglob('*.py'))}
 for p in [Path(__file__),R/'temp/run_single_read_diagnostic_r1_20260912.py',R/'temp/validate_single_read_fixture_r2_20260912.py']:pins[str(p.relative_to(R))]=sha(p)
 registration={**one,'round':D.name,'created_at':time.time(),'cases':cases,'source_pins':pins,'frozen_before_sha256':sha(D/'SOURCE_BEFORE.json'),'frozen_after_sha256':sha(D/'SOURCE_AFTER.json'),'description_only_ast_verified':True,'predecessor':'R3 NO_KEEP: primary 19/21 to 14/21, supplement 3/3 to 2/3; archived independently','hypothesis':'Concise positive legal-input semantics without naming illegal fields or negative sentinel examples; no causal claim about negative priming yet','additional_trials':'Only this additional description candidate; no further automatic wording search this task','treatment':'Only read_file description and parameter descriptions differ; both frozen before first generation, no rwkv_lh edits between/during arms. Model/state/sampling/scorer unchanged.','comparison':'before then after, each 3 passes through same 7 primary plus 1 supplemental case; 21+3 per arm. Report primary and supplemental separately, no historical R1/R2 pooling.','gate':{'primary':'after primary suite all 7 pass in repetitions 2 and 3 consecutively','supplemental':'after supplemental missing case passes repetitions 2 and 3 consecutively','zero_errors':'zero illegal-parameter/protocol errors and zero premature final_answer in those two full passes','no_regression':'any case with baseline 3/3 must retain candidate 3/3','scope':'fixed cases only; no universal reliability claim; stop at single-read even if gate passes'},'false_completion_measure':'Any final_answer instead of the required single read is conservatively premature and fails gate. Actual Harness failure is never marked tool success. No second generation or post-observation answer is assessed.','stop':'48 model generations maximum, 1800 output tokens each; each arm one hour wall budget; infrastructure failure stops arm without scored retry','historical_correction':'R1 rejected outputs: two end_byte=-1; third max_lines=2048 plus max_bytes=8192. Earlier all-end_byte report is incorrect; archived historical scores untouched.'}
 assert not (D/'REGISTRATION.json').exists();save(D/'REGISTRATION.json',registration)
 for arm in ['before','after']:
  output=D/arm;output.mkdir();save(output/'REGISTRATION.json',{**registration,'arm':arm})
 print('FROZEN',sha(D/'REGISTRATION.json'),flush=True)
else:
 arm=sys.argv[1];assert arm in ['before','after']
 reg=json.loads((D/'REGISTRATION.json').read_text());source=D/('frozen_'+arm)
 assert inventory(source)==json.loads((D/('SOURCE_'+arm.upper()+'.json')).read_text())
 # Import the selected frozen package before the historical runner adds ROOT.
 sys.path.insert(0,str(source));import rwkv_lh
 assert Path(rwkv_lh.__file__).resolve().is_relative_to(source)
 from rwkv_lh.runtime.settings import load_local_env
 load_local_env(R/'.env.local')
 sys.path.insert(0,str(R/'temp'))
 import run_single_read_diagnostic_r1_20260912 as driver
 from validate_single_read_fixture_r2_20260912 import validate_fixture
 assert Path(sys.modules['rwkv_lh.harness'].__file__).resolve().is_relative_to(source)
 for c in reg['cases']:validate_fixture(c,R)
 driver.D=D/arm;driver.run()
