from pathlib import Path
from collections import Counter
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';O=E/'EXECUTOR_OUTPUT_BUDGET_R1_20260910'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
d=read(O/'COMPARISON.json');table='| 臂 | Strict | completed | mutation | 动作 | Executor返回 | length | 时间秒 |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'; folders=[];token_evidence=[]
for arm in d['arms']:
 folder=E/('EXECUTOR_OUTPUT_BUDGET_'+arm['arm'].upper()+'_R1_20260910');folders.append(folder);a=arm['summary']['agent'];table+=f"| {arm['arm']} | {a['strict']}/2 | {a['completed']}/2 | {a['mutation_count']} | {a['action_count']} | {a['executor_returned']} | {a['executor_length']} | {arm['completion']['wall_seconds']:.2f} |\n"
 tokens=Counter();cases=[]
 for row in arm['summary']['cases']:
  audit=read(Path(row['audit_path']));ex=[e for e in audit['model_trace'] if e.get('type')=='model_session_generation_returned' and e.get('model_role')=='executor_args'];case_tokens=sum(len(e['raw_generation']['raw_token_ids']) for e in ex)
  tokens['raw_returned_token_ids']+=case_tokens;cases.append({'task_id':row['task_id'],'executor_returned':len(ex),'raw_returned_token_ids':case_tokens,'finish_reasons':dict(Counter(e['finish_reason'] for e in ex))})
 token_evidence.append({'arm':arm['arm'],'executor_raw_returned_token_ids':tokens['raw_returned_token_ids'],'cases':cases,'note':'Counts exact server-returned raw output token IDs; not full server compute, cache materialization or monetary billing. Native raw evidence has no usage object; empty executor_usage in COMPARISON is unavailable, not zero consumption.'})
 reasons='；'.join(f'{k}×{v}' for k,v in a['termination_reasons'].items())
 (folder/'REPORT.zh-CN.md').write_text(f'''# Executor预算臂 {arm['arm']}

Agent：Strict {a['strict']}/2、completed {a['completed']}/2、mutation {a['mutation_count']}、动作{a['action_count']}。终止原因：{reasons}。原始结果完整保存，不替换或重评分。

Executor返回{a['executor_returned']}，length {a['executor_length']}；实际生成请求max_tokens计数{arm['actual_executor_max_tokens']}。交接核验：{arm['handoff_generation_contexts']}次生成上下文、{arm['handoff_role_inputs']}个角色输入，all_handoffs_verified={arm['all_handoffs_verified']}。未调用角色的题目不算模型能力通过。

源码文件manifest SHA {arm['source_manifest_sha256']}，公共实验driver SHA {arm['driver_sha256']}，与另一臂比较以完整文件身份为准；本地HEAD之间只有记录提交，rwkv_lh和评测脚本没有变化。两臂共用模型/zero State/温度/任务/预算，唯一主动参数差异为Executor max_output_tokens。整体判断见父轮COMPARISON.json；本臂单独不宣布KEEP。optimizer steps=0。
''')
write(O/'TOKEN_EVIDENCE.json',{'arms':token_evidence})
baseline=d['arms'][0]['summary']['agent'];candidate=d['arms'][1]['summary']['agent']
(O/'REPORT.zh-CN.md').write_text(f'''# Executor输出预算单变量轮 R1

{table}
两臂完整保留同两道题的原始结果，生产文件manifest、实验driver、模型/zero State与采样一致；两臂之间只改变next_command的max_output_tokens，未修改生产代码、题目、parser、评分或停止边界。记录提交使Git HEAD不同，不改变冻结源码文件身份。两题小样本不能推导超越Agent噪声带的改善。

结论 **{d['decision']}**。预注册要求baseline length>0、candidate length次数至少减半且比例下降、Strict不劣化、运行完整无不可用服务；本次baseline length={baseline['executor_length']}，candidate={candidate['executor_length']}，不满足必要条件。逐项判定见COMPARISON.json；不能据此证明加倍预算有效，也不把不同计划/模型随机轨迹下的变化单独归因为预算。生产默认Executor仍1800。

基线WEB-02在Planner阶段失败：HTTP200、finish_reason=stop、最终content为空，输出8496token全部计入reasoning；未进入RWKV。这是服务响应合同失败，不是余额402或Native传输死链。COMPARISON中的no_infrastructure_failures是涵盖Supervisor不可用的保守可比性检查，本次具体类型以原始SupervisorProtocolError为准，不将其误称网络故障。基线没有Executor截断本身已足以令KEEP失败。没有为改善结论补跑失败题。

候选WEB-02的自然stop后无效JSON与length分别保留，不混为同一种错误；每次生成含retry均计数。raw output token计量见TOKEN_EVIDENCE.json，Native未提供usage对象，因此COMPARISON空usage字典不是零资源消耗。实际耗时记录在各臂COMPLETION.json。采集轮新发现的WEB-01截断未被事后加入本轮题集。

默认预算未改，optimizer steps=0；这不是StateTune。相关工程源码已在WSL完整tests/1455 passed、0failed/0skipped，之后未变。未读Real Agent Holdout V2，也没有把私有开发验收内容送入Agent。
''')
helpers=['prepare_executor_budget_driver_20260910.py','run_executor_output_budget_r1_20260910.py','launch_executor_budget_after_collection_20260910.py','finish_executor_budget_comparison_20260910.py','summarize_current_official_round_20260910.py','verify_official_case_handoffs_r1_20260910.py','seal_executor_budget_round_20260910.py']
(O/'helpers').mkdir(exist_ok=True)
for name in helpers:shutil.copyfile(R/'temp'/name,O/'helpers'/name)
for folder in folders+[O]:
 files=[{'path':str(p.relative_to(folder)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='EVIDENCE_SHA256.json']
 write(folder/'EVIDENCE_SHA256.json',{'round':folder.name,'files':files,'source_files_unchanged':True,'pytest_passed':1455,'optimizer_steps':0,'default_executor_budget_changed':False})
 print(json.dumps({'round':folder.name,'report_sha256':sha(folder/'REPORT.zh-CN.md'),'evidence_sha256':sha(folder/'EVIDENCE_SHA256.json')}))
