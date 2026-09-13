from pathlib import Path
import json,hashlib,sys,time,importlib.util,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');B=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913';sys.path.insert(0,str(D/'source'))
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import canonical_json
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.token_budget import tokenizer
from rwkv_lh.harness import ActionHarness
from rwkv_lh.inference.uploaded_sources import source_inventory
spec=importlib.util.spec_from_file_location('input_menu_runner',R/'temp/run_input_menu_r1_20260913.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
menus={}
for arm,h in [('full',ActionHarness()),('readonly',runner.ReadOnlyMenuHarness())]:
 m=LongHorizonModel(ModelSession(client=object(),settings=RuntimeSettings(base_url='http://unused.invalid',api_key='',model='offline',tool_disclosure_mode='full')),harness=h);menus[arm]=m.direct_definitions()
assert menus['readonly']==[d for d in menus['full'] if d['name']=='final_answer' or (ActionHarness().definition(d['name']).read_only and not ActionHarness().definition(d['name']).side_effect)]
assert all(d in menus['full'] for d in menus['readonly']);assert next(d for d in menus['full'] if d['name']=='read_file')==next(d for d in menus['readonly'] if d['name']=='read_file')
save(D/'MENU_ADAPTER_CHECK.json',dict(only_removes_permission_blocked_tools=True,tool_definitions_unchanged=True,menus={a:dict(names=[d['name'] for d in v],tokens=len(tokenizer().encode(canonical_json(v)))) for a,v in menus.items()}))
old=json.loads((B/'REGRESSION_REGISTRATION.json').read_text());er={**old,'round':D.name,'max_total_calls':96,'wall_seconds':7200,'comparison':'Only input tool menu scope changes: 19 full versus policy-allowed readonly definitions; same callbacks/validation/readonly guard, literal tasks and rubric. No rewritten schema, prompt protocol, observation, chosen parameters or forced tool order.','parent_registration_sha256':sha(B/'REGRESSION_REGISTRATION.json')};save(D/'REGRESSION_REGISTRATION.json',er)
prior=json.loads((B/'RUN_REGISTRATION.json').read_text());reg={**prior,'profiles':{a:{'id':'zero','sha256':'0'*64} for a in ['full','readonly']},'regression_fingerprint':sha(D/'REGRESSION_REGISTRATION.json'),'runner_sha256':sha(R/'temp/run_input_menu_r1_20260913.py'),'source_pins':{p:h for p,(h,n) in source_inventory(D/'source').items()},'server_identity_sha256':sha(D/'SERVER_IDENTITY.json'),'source_commit_local_only':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'frozen_at_epoch':time.time(),'authorization':'Owner asks to diagnose input sensitivity; bounded same-case paired input-only diagnostic, no production edits/training/strong calls/new datasets','menu_adapter_sha256':sha(D/'MENU_ADAPTER_CHECK.json'),'causal_limit':'Whole-menu input scope comparison, not proof of which removed field/tool causes effects; stochastic two repeats, raw outcomes no posthoc rescore; runtime permitted tools identical'};save(D/'RUN_REGISTRATION.json',reg);print((D/'MENU_ADAPTER_CHECK.json').read_text());print(sha(D/'RUN_REGISTRATION.json'))
