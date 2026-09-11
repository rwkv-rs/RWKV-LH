from pathlib import Path
import json,hashlib,shutil,collections
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911';T=R/'data/experiments/EXECUTE_COVERAGE_TASK_AUTHORING_R1_20260911';D=R/'data/experiments/EXECUTE_COVERAGE_DEPLOYMENT_A_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert '1464 passed' in (T/'PYTEST_ISOLATED_CORRECT_ROOT.log').read_text()
s=json.loads((O/'AGENT_SUMMARY.json').read_text());k=json.loads((O/'KEEP_EVALUATION.json').read_text());assert k['decision']=='KEEP'
cmd=k['commands'];assert len(cmd)==3
for a in cmd:assert a['action_type']=='check_command' and a['phase']=='execute' and a['status']=='succeeded' and a['exit_code']==a['expected_exit_code']==1
workspace=O/'all_zero/cases/NEW-DIAG-02/workspace'
assert not (workspace/'TEST_REPORT.md').exists()
assert all(a['result_metadata'].get('workspace_ephemeral') and a['result_metadata'].get('writes_discarded') and a['result_metadata'].get('sandbox_backend')=='bubblewrap' and a['workspace_digest_before']==a['workspace_digest_after'] for a in cmd)
write(O/'COMMAND_EVIDENCE_AUDIT.json',{'tmp_overlay_live_agent_verified':True,'basis':'Three actual original run_tests.py commands wrote their report within temporary bubblewrap overlay; captured stdout includes real pytest failure; original workspace digest unchanged and TEST_REPORT.md absent after run. Source has no model mutations.','command_action_ids':[a['action_id'] for a in cmd],'task_id':'NEW-DIAG-02','actual_exit_code':1,'expected_exit_code':1,'meaning':'Successful expected-failure diagnosis, NOT fixed tests or task completion.','timeout_output_live_agent_verified':False,'timeout_reason':'No natural command timeout occurred; no full timeout-path claim.','initial_keep_evaluation_note':'KEEP_EVALUATION deliberately left optional overlay flag unverified pending this separate concrete command audit. Main decision unchanged.','report_exists_in_original_workspace':False,'command_metadata':cmd})
(O/'REPORT.zh-CN.md').write_text('''# Execute覆盖采集轮次A

**Agent：Strict 0/4、completed 0/4、mutation 0、动作6。** RP-CLI-01和NEW-DIAG-02因重复成功动作耗尽无进展预算停止；RP-WEB-02和NEW-DIAG-01耗尽协议拒绝预算。没有项目修复完成，不能由本轮宣布自主开发交付能力通过。

**采集KEEP。** NEW-DIAG-02实际完成3次check_command，均在execute步骤执行python run_tests.py。expected_exit_code=actual_exit_code=1，是真实定位已有测试失败，不是pytest转绿；不能把Harness成功改写为测试通过。原始未修复库存累计测试仍1 failed/3 passed。另一个诊断题在observe前沿多次返回未展示的execute_shell，属于Executor协议问题，不伪装成Selector准入问题。

生产无waiver提取4来源，12自动候选、42待独立审阅；execute=9。原始候选INVALID，因为四个家族均为train且此单批不满足其他覆盖；KEEP只证明取得缺失来源，不能绕过合并、独立复核、去重和最终valid门。后续双AI语义复核另建SELECTOR_EXECUTE_SEMANTIC_REVIEW_R1_20260911，不修改本轮原始提取。

36次完整生成上下文和36个角色输入边界全部逐字/完整token核验。Executor31次返回、12次length均在Web对照；Strong请求失败0、生成中断0，运行时传输失败0。Finalizer/Final Auditor未到达，不能称五角色语义验收通过。Executor1800、零State、并发1、每题1800s、总7200s、max_transitions200、native resume1、pending resume0全程不变。

真实check命令在bubblewrap临时overlay中生成报告及pytest缓存，原workspace digest不变且TEST_REPORT.md不存在；COMMAND_EVIDENCE_AUDIT.json确认临时写入丢弃路径在线生效。没有自然超时，超时输出路径本轮未验证。私有验收使用只读快照，作者参考与验收代码不进入Agent workspace；全历史恶意篡改防护限制见作者报告。

运行时发现另一工作进程存在，精确比较确认其两处注册表改动早已包含在生成前源码清单中，并无运行中源码漂移。后两题转到逐文件相同的隔离工作区，未重跑前两题。迁移第一次因默认plan_cache_dir变了被配置硬门拒绝，零模型请求、未建立case；保留PRE_GENERATION_LOCATION_PREFLIGHT，恢复原缓存绝对路径后在原总预算内首次执行两道新题。所有正式生成源文件匹配冻结manifest。Git提交c6b46d01标识rwkv生产源码；本地运行器/pyproject另有预先冻结的未提交注册项，不冒充干净HEAD。

服务器部署根RWKV-LH-execute-coverage-a-20260911，完整上传项目与engine清单已核验，未使用远端Git。两条显式授权提交已push。作者定稿后完整回归1464 passed/0 failed/0 skipped；并行临时目录冲突与错误跨工作区测试目录的失败尝试全部留证，未改测试或代码使其通过。

B不启动。进入既定重签、复核、去重、密封selection、freeze、smoke/首训登记链。freeze集成尚有三个已独立确认缺口，不能宣告全部接口就绪。无新正式角色数据集、optimizer steps=0，未读取Real Agent Holdout V2。
''',encoding='utf-8')
for folder,names in [(O,['run_execute_coverage_a_20260911.py','continue_execute_coverage_a_isolated_20260911.py','run_pending_execute_cases_a_20260911.py','resume_pending_execute_cases_a_20260911.py','verify_official_case_handoffs_r1_20260910.py','extract_execute_coverage_a_20260911.py','evaluate_execute_coverage_a_20260911.py','seal_execute_coverage_a_20260911.py']),(T,['author_execute_diagnostic_tasks_20260911.py','strengthen_diagnostic_acceptance_20260911.py','validate_execute_diagnostic_tasks_20260911.py','freeze_execute_task_authoring_a_20260911.py']),(D,['freeze_execute_coverage_deployment_a_20260911.py','upload_execute_coverage_deployment_a_20260911.py'])]:
 (folder/'helpers').mkdir(exist_ok=True)
 for name in names:shutil.copyfile(R/'temp'/name,folder/'helpers'/name)
 if folder==T:
  report=folder/'REPORT.zh-CN.md';t=report.read_text().replace('本轮尚无新的 Agent 成绩。','作者验证本身不产生 Agent 成绩；后续轮次A为Strict 0/4、completed 0/4、mutation 0，取得真实execute来源而非开发完成。').replace('当前轮次 A 已启动，成绩以该轮封存结果为准','轮次 A 已完成并按采集主判据KEEP，成绩以该轮封存结果为准').replace('定稿后另有 PYTEST_FINAL.log 验证记录','定稿后隔离工作区全套1464 passed，见PYTEST_ISOLATED_CORRECT_ROOT.log；另有环境失败记录TEST_ENVIRONMENT_FAILURES.json');report.write_text(t)
 files=[]
 for p in sorted(folder.rglob('*')):
  if not p.is_file() or p.name=='EVIDENCE_SHA256.json' or '__pycache__' in p.parts:continue
  rel=p.relative_to(folder)
  if folder==T and (rel.parts[0].startswith('author_workspaces') or rel.parts[0]=='private_validation'):continue
  if folder==D and rel.parts[0]=='deployment_source':continue
  files.append({'path':str(rel),'sha256':sha(p),'bytes':p.stat().st_size})
 write(folder/'EVIDENCE_SHA256.json',{'round':folder.name,'files':files,'pytest_passed':1464,'optimizer_steps':0,'holdout_accessed':False})
 print(folder.name,sha(folder/'EVIDENCE_SHA256.json'))
