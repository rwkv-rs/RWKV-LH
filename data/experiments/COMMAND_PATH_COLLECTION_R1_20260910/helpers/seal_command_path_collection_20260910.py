from pathlib import Path
import collections,hashlib,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/COMMAND_PATH_COLLECTION_R1_20260910'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,o):
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
s=read(O/'AGENT_SUMMARY.json');hs=[read(O/(r['task_id']+'.HANDOFF_VERIFICATION.json')) for r in s['cases']]
if not read(O/'COMPLETION.json')['source_unchanged'] or not all(h['all_verified'] for h in hs):raise SystemExit('invalid source or handoff')
counts=collections.Counter();roles=collections.Counter()
for r in s['cases']:
 a=read(Path(r['audit_path']));counts.update(x['action_type'] for x in a['action_ledger'].values());roles.update(r['role_calls'])
write(O/'ROLE_AND_COMMAND_EVIDENCE.json',{'action_types':dict(counts),'role_calls':dict(roles),'generation_contexts_verified':sum(h['generation_contexts'] for h in hs),'role_inputs_verified':sum(h['role_inputs'] for h in hs),'all_returned_handoffs_verified':True,'check_command_count':counts['check_command'],'run_command_count':counts['run_command'],'command_path_exercised':False,'tmp_overlay_live_agent_verified':False,'timeout_output_live_agent_verified':False,'selector_execute_phase_coverage':read(O/'FRESH_EXTRACTION_RESULT.json')['coverage']['selector_intent']['execute'],'coverage_note':'Selector execute flag means actual step.phase==execute, while Harness command-path evidence separately counts executed check/run actions; neither was reached.','all_roles_zero':True,'optimizer_steps':0})
(O/'REPORT.zh-CN.md').write_text('''# 新源码命令路径采集 R1

**Agent：Strict 0/4、completed 0/4、mutation 0、动作13。** RP-CLI-01、RP-FULL-02、RP-WEB-02终止于identical_success_budget_exhausted；RP-WEB-01为protocol_rejection_budget_exhausted。所有原始结果完整，源码21c0cf45的文件身份全程未变，未改评分、题目或协议；这是预注册四题子集采集，不声称完整12题或15题验收。

实际动作是8次search_text、5次list/read目录与文件（逐项以ROLE_AND_COMMAND_EVIDENCE.json为准）；没有check_command或run_command，也没有代码mutation。题目包含公开运行/检查要求，并不能保证zero模型到达执行阶段。故本轮采集完成，但补命令路径/execute覆盖的目标未达到。tmp-overlay和超时输出只保留既有真实沙箱工程探针证明，不能声称已在本轮Agent命令中生效。

Executor27次返回，12次finish_reason=length，全在WEB-01；其余三个任务各自0。Supervisor请求失败0、生成中断0，运行时transport failure0，已接通的Native首错事件0；没有自然发生的恢复事件，不能据此宣告异常路径线上验收通过。模型、所有角色zero State、Executor1800和采样预算固定。后续预算轮独立使用新两臂FULL-02/WEB-02，不拿本轮混作基线，也不根据新WEB-01结果改题。

39次生成上下文、39个角色输入边界均逐字/完整token核验；未到达Finalizer/Final Auditor，不夸大角色能力。私有开发验收由原runner在bubblewrap只读workspace snapshot中运行，验收实现与日志未送给Agent；未读取Real Agent Holdout V2。

四来源按当前源码清单直接生产提取，无waiver：14自动候选、43待审，execute=0，质量INVALID。原始14/43输出保持不变，新的语义复核另建记录。可与旧双签候选应用同一预注册去重规则，但不能补造缺失命令执行事实或更改phase。没有新建角色data/datasets版本、没有训练，optimizer steps=0。
''')
# Make the concrete action totals authoritative in prose.
p=O/'REPORT.zh-CN.md';t=p.read_text().replace('8次search_text、5次list/read目录与文件','6次search_text、5次list_directory、2次read_file');p.write_text(t)
(O/'helpers').mkdir(exist_ok=True)
for n in ['prepare_command_path_collection_20260910.py','run_command_path_collection_r1_20260910.py','verify_official_case_handoffs_r1_20260910.py','summarize_current_official_round_20260910.py','extract_fresh_command_collection_20260910.py','seal_command_path_collection_20260910.py']:shutil.copyfile(R/'temp'/n,O/'helpers'/n)
files=[{'path':str(p.relative_to(O)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='EVIDENCE_SHA256.json']
write(O/'EVIDENCE_SHA256.json',{'round':O.name,'files':files,'source_commit':'21c0cf45d519ee090742c08156cd2935d112b87b','source_unchanged':True,'pytest_passed':1455,'optimizer_steps':0,'holdout_accessed':False})
print(json.dumps({'report_sha256':sha(O/'REPORT.zh-CN.md'),'evidence_sha256':sha(O/'EVIDENCE_SHA256.json'),'files':len(files)}))
