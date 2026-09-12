from pathlib import Path
import json,hashlib,sys,importlib.util
from dataclasses import replace
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation_r2';old=R/'data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913/read_regression/REGISTRATION.json'
from rwkv_lh.runtime.settings import get_runtime_settings,load_local_env
load_local_env(R/'.env.local')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
if sys.argv[1]=='freeze':
 evalreg=json.loads((D/'RUN_REGISTRATION.json').read_text());prior=json.loads(old.read_text());pins={str(p.relative_to(R)):sha(p) for p in (R/'rwkv_lh').rglob('*.py')};pins['temp/run_direct_original_read_r1_20260913.py']=sha(R/'temp/run_direct_original_read_r1_20260913.py');pins[str(Path(__file__).relative_to(R))]=sha(Path(__file__))
 for arm in ['zero','candidate']:
  out=D/('read_'+arm);out.mkdir(exist_ok=False);reg={**prior,'round':P.name+'-original-read-'+arm,'source_pins':pins,'source_regression_sha256':sha(old),'profile':evalreg['profiles'][arm],'base_url':evalreg['base_url'],'model_name':evalreg['model_name'],'training':False,'new_dataset_version':False,'note':'Current Store resource-release fix is shared by both read regression arms; model input/protocol/tool contract unchanged; independent original single-read diagnostic, never full summary success.'};save(out/'REGISTRATION.json',reg)
else:
 arm=sys.argv[1];out=D/('read_'+arm);reg=json.loads((out/'REGISTRATION.json').read_text());spec=importlib.util.spec_from_file_location('fixed_reader',R/'temp/run_direct_original_read_r1_20260913.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);settings=replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model_name']);reader.get_runtime_settings=lambda:settings;reader.ACTIVE_PROFILE=reg['profile'];reader.D=out;reader.run()
