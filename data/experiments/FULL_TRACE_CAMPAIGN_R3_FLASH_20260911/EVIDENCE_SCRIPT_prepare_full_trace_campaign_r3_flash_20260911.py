from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');W=R.with_name('RWKV-LH-full-trace-r2-20260911');C=R/'data/experiments/FULL_TRACE_CAMPAIGN_R3_FLASH_20260911';O=R/'data/experiments/FULL_TRACE_COLLECTION_R3_FLASH_20260911';D=R/'data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911';C.mkdir();O.mkdir();B=O/'bundle';B.mkdir()
C1=R/'data/experiments/FULL_TRACE_CAMPAIGN_R1_20260911';O1=R/'data/experiments/FULL_TRACE_COLLECTION_R1_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
reg=json.loads((C1/'REGISTRATION.json').read_text());reg.update(strong_model='deepseek-flash',model_change_authorization='Owner explicitly requests deepseek-flash for official API; applies to Planner and Stage Checker',round_id=C.name,created_at=datetime.now(timezone.utc).isoformat(),owner_authorization='Owner requests deploy latest changes and rerun using latest source as trace.',source_commit='de029c88',production_change_commit='de029c88',prior_campaign={'path':str(C1/'REGISTRATION.json'),'sha256':sha(C1/'REGISTRATION.json')},systemic_failure_policy='Check official balance before model generation; on HTTP402 stop scheduling remaining tasks and retain first failure. No retry of unknown mutations.',protocol_migration='New current role protocols only; no historical waiver or State reused. Old traces remain historical and are not admitted as new protocol data.')
for s in reg['suites']:
 for role in ['tasks','acceptance']:
  p=Path(s[role+'_path']);new=W/p.relative_to(R.with_name('RWKV-LH-full-trace-r1-20260911'));assert sha(new)==s[role+'_sha256'];s[role+'_path']=str(new)
shutil.copyfile(C1/'TASK_QUEUE.json',C/'TASK_QUEUE.json');write(C/'REGISTRATION.json',reg)
for n in ['tasks.json','acceptance.json']:shutil.copyfile(O1/'bundle'/n,B/n)
m=json.loads((O1/'bundle/MANIFEST.json').read_text());m['campaign_registration']={'path':str(C/'REGISTRATION.json'),'sha256':sha(C/'REGISTRATION.json')};write(B/'MANIFEST.json',m)
scope=json.loads((O1/'COVERAGE_SCOPE.json').read_text());scope['objective']='Selector production tool choice across the owner-authorized 117 public development tasks; current role coverage, not final Agent acceptance';write(O/'COVERAGE_SCOPE.json',scope)
write(O/'BATCH_PREREGISTRATION.json',{'campaign_sha256':sha(C/'REGISTRATION.json'),'bundle_sha256':sha(B/'MANIFEST.json'),'task_count':117,'model_requests_started':False,'task_selection_uses_scores':False,'optimizer_steps':0,'systemic_failure_policy':reg['systemic_failure_policy']})
s=(R/'temp/run_full_trace_collection_r1_20260911.py').read_text().replace('RWKV-LH-full-trace-r1-20260911',W.name).replace('FULL_TRACE_COLLECTION_R1_20260911',O.name).replace('FULL_TRACE_CAMPAIGN_R1_20260911',C.name).replace('da067f25','de029c88')
anchor='    load_local_env()'
addition="""
    from rwkv_lh.exact_tool_selector.input_protocol import CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL
    deployment=RECORD_ROOT/'data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911'
    decoder=json.loads((deployment/'DECODER_MANIFEST.json').read_text())
    os.environ['RWKV_LH_SELECTOR_INPUT_PROTOCOL']=CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL
    os.environ['RWKV_LH_SELECTOR_DECODER_SHA256']=digest(deployment/'DECODER_MANIFEST.json')
    os.environ['RWKV_LH_SELECTOR_DECODER_ID']=decoder['decoder_id']
    os.environ['RWKV_LH_SELECTOR_DECODER_PROTOCOL']=decoder['decoder_protocol']
"""
assert s.count(anchor)==1;s=s.replace(anchor,anchor+addition)
anchor='def collect():\n'
helper="""def check_balance(planner):
    import requests
    with requests.Session() as session:
        session.trust_env=False
        response=session.get(planner.base_url.rstrip('/')+'/user/balance',headers={'Authorization':'Bearer '+planner.api_key},timeout=(5,20))
        response.raise_for_status();value=response.json()
    record={'at':datetime.now(timezone.utc).isoformat(),'http_status':response.status_code,'is_available':value.get('is_available') is True,'model_generation_started':False}
    (ROUND/'BALANCE_PREFLIGHT.json').write_text(json.dumps(record,indent=2)+'\\n')
    if not record['is_available']:
        (ROUND/'BLOCKED_BEFORE_GENERATION.json').write_text(json.dumps({'reason':'official_planner_insufficient_balance','pending_task_count':117,'optimizer_steps':0},indent=2)+'\\n')
        raise SystemExit('Official Planner balance unavailable; no task generation started')
    return record

"""
s=s.replace(anchor,helper+anchor)
anchor="    r=json.loads((ROUND/'REGISTRATION.json').read_text());started=time.monotonic();completions=[]"
s=s.replace(anchor,"    check_balance(planner)\n"+anchor)
anchor="    write(ROUND/'COMPLETION.json',{'cases':completions,'wall_seconds':time.monotonic()-started,"
insert="""        if record['result_recorded']:
            result=json.loads((OUTPUT/(task_id+'.result.json')).read_text())
            if result.get('supervisor_failure',{}).get('http_status')==402:
                write(ROUND/'PAUSED_SYSTEMIC_FAILURE.json',{'reason':'official_planner_http_402','failed_task_id':task_id,'remaining_task_ids':r['task_ids'][len(completions):],'optimizer_steps':0})
                return
"""
assert s.count(anchor)==1;s=s.replace(anchor,insert+anchor)
s=s.replace('deepseek-v4-pro','deepseek-flash')
p=R/'temp/run_full_trace_collection_r3_flash_20260911.py';p.write_text(s);shutil.copyfile(p,O/('EVIDENCE_SCRIPT_'+p.name));shutil.copyfile(Path(__file__),C/('EVIDENCE_SCRIPT_'+Path(__file__).name))
print('Registered 117 unchanged tasks on de029c88, current protocols, balance gate before generation')
