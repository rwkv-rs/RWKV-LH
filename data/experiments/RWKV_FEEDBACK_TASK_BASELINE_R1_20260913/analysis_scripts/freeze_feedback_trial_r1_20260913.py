from pathlib import Path
import sys,json,shutil,subprocess,time
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as r
from rwkv_lh.run_lifecycle import RUN_LIFECYCLE_POLICY_KEY,run_lifecycle_policy_document
D=R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913';A=R/'data/experiments/TASK_OUTCOME_AUDIT_REFORM_R1_20260913';M=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
old=json.loads((M/'REGRESSION_REGISTRATION.json').read_text());oldrun=json.loads((M/'RUN_REGISTRATION.json').read_text())
pins=json.loads((A/'FORWARD_SOURCE_MANIFEST.json').read_text());assert all(r.file_digest(R/p)==sha for p,sha in pins.items())
for p in pins:
 target=D/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/p,target)
reg={'round':D.name,'cases':old['cases'],'model_name':oldrun['model_name'],'model_sha256':oldrun['model_sha256'],'base_url':oldrun['base_url'],'sampling':old['sampling'],'state':old['state'],'runner_sha256':r.file_digest(R/'temp/run_feedback_task_baseline_r1_20260913.py'),'source_pins':pins,'source_commit_local_only':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'frozen_epoch':time.time(),'runtime_policy':{RUN_LIFECYCLE_POLICY_KEY:run_lifecycle_policy_document('goal')},'budget':{'max_calls_per_task':6,'max_output_tokens':1800,'wall_seconds_per_task':300,'max_total_calls':48,'wall_seconds_total':3000,'repeated_identical_read_success_stop':3,'protocol_feedback':True,'automatic_resume':False,'forced_final':False},'scope':'same four approved cases two repeats; new feedback task baseline, not gain vs historical stop probes','arm':'feedback','tool_menu':'unchanged production full 19 with R4 read description','assistance':'rwkv_independent','server_inventory_evidence_sha256':r.file_digest(D/'SERVER_COMPLETE_INVENTORY_R2.json'),'preexisting':json.loads((A/'PREEXISTING.json').read_text()),'start_checks':json.loads((D/'OFFLINE_POLICY_CHECK.json').read_text())}
r.write_once(D/'REGISTRATION.json',reg)
for p in (A/'forward_contracts').glob('*.json'):
 c=r.load_contract(p);c['execution_identity']['budget']=r.digest(reg['budget']);c['execution_identity']['state']=r.digest({'state':reg['state'],'runtime_policy':reg['runtime_policy']})
 r.freeze_contract(c,D/'contracts'/p.name)
r.write_once(D/'PLAN.json',{'question':'在真实协议反馈与正确观察/State续接下，RWKV能否自主完成同一小任务？','quality':'复用已冻结逐项验收，完整4题×2遍全部met为固定组质量门；协议错误另报','attribution':'本轮建立基线；与历史stop试验有执行策略差异，不能当输入优化收益','next':'先核对实际反馈消费、输入、State与结果，再决定是否设计单因素输入对照','offline_check_correction':'初次检查错误期待 INTERRUPTED；生产 Goal 策略以 RUNNING + run_yielded 保存，已按真实语义核验。评测预算终止与持久运行状态分开，无模型调用或生产修复。'})
for n in ['run_feedback_task_baseline_r1_20260913.py','check_feedback_trial_policy_r1_20260913.py','freeze_feedback_trial_r1_20260913.py','verify_feedback_server_r1_20260913.py']:
 target=D/'analysis_scripts'/n;target.parent.mkdir(exist_ok=True);shutil.copyfile(R/'temp'/n,target)
print('frozen',r.file_digest(D/'REGISTRATION.json'))
