from pathlib import Path
import json,hashlib,subprocess,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';O=E/'SELECTOR_GATE_CONTINUATION_R1_20260910';O.mkdir(exist_ok=False)
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,o):
 with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
comparison=read(E/'EXECUTOR_OUTPUT_BUDGET_R1_20260910/COMPARISON.json');collection=read(E/'COMMAND_PATH_COLLECTION_R1_20260910/AGENT_SUMMARY.json')['agent']
rounds=['AUDIT_FANOUT_DEPLOYMENT_R1_20260910','SELECTOR_WAIVER_RENEWAL_R1_20260910','COMMAND_PATH_COLLECTION_R1_20260910','SELECTOR_SEMANTIC_REVIEW_R1_20260910','SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910','SELECTOR_SIMILARITY_POLICY_R1_20260910','SELECTOR_TRAINING_PREFLIGHT_R1_20260910','SELECTOR_TRAINING_PREFLIGHT_R2_20260910','EXECUTOR_OUTPUT_BUDGET_BASELINE1800_R1_20260910','EXECUTOR_OUTPUT_BUDGET_CANDIDATE3600_R1_20260910','EXECUTOR_OUTPUT_BUDGET_R1_20260910']
verified=[]
for name in rounds:
 folder=E/name;m=read(folder/'EVIDENCE_SHA256.json');bad=[f['path'] for f in m['files'] if not (folder/f['path']).is_file() or sha(folder/f['path'])!=f['sha256']]
 if bad:raise SystemExit('sealed evidence changed: '+name+str(bad))
 verified.append({'round':name,'evidence_sha256':sha(folder/'EVIDENCE_SHA256.json'),'files_verified':len(m['files']),'report_sha256':sha(folder/'REPORT.zh-CN.md')})
if subprocess.check_output(['git','diff','21c0cf45','--','rwkv_lh','scripts','tests','pyproject.toml','uv.lock'],cwd=R):raise SystemExit('production/test source changed')
write(O/'EVIDENCE_INTEGRITY_VERIFICATION.json',{'rounds':verified,'all_verified':True,'source_unchanged_from_1455_green_tests':True,'optimizer_steps':0})
rows=[('新命令路径采集',collection)] + [(a['arm'],a['summary']['agent']) for a in comparison['arms']]
table='| 轮次 | Strict | completed | mutation | 动作 | 终止原因 |\n|---|---:|---:|---:|---:|---|\n'
for name,a in rows:table+=f"| {name} | {a['strict']}/{a['selected']} | {a['completed']}/{a['selected']} | {a['mutation_count']} | {a['action_count']} | "+'；'.join(f'{k}×{v}' for k,v in a['termination_reasons'].items())+' |\n'
status=f'''# 六项继续执行结果 R1

{table}
以上是不同注册任务/预算的独立轮次，不合并为一次统一Agent评分。当前能力仍是历史上证明过的给定工作区代码文件写入；没有可靠自主初始化、实现、运行、调试和交付项目的证据。新工程回归全绿不代表Agent已能完成项目。

1. 指定f34e4964、21c0cf45已push到origin/chase/rwkv-goal-loop-v2-cleanup，远端SHA21c0cf45d519ee090742c08156cd2935d112b87b。后续记录按AGENTS分轮本地提交，owner负责后续push。
2. 同一14来源/Selector、累计十文件冻结→当前SHA的waiver已独立双AI accept；固定wrapper恢复原60候选与126待审行，全字段不变。双审纠正附件仅绑定同一原来源，未扩大waiver到命令或其它角色。waiverSHA f53186ecfca2f97126b132f41b1bc37bdef46e77ce91b3cde4a68385ef0a3aaa。
3. 已部署21c0cf45，新根/home/chase/GitHub/RWKV-LH-audit-fanout-r1-20260910，完整项目131文件与engine6393文件SHA核验，服务器从未调用Git。新四题采集完成，但check/run=0、execute=0，补命令路径目标未达到；不能宣称tmp-overlay和超时输出已获本轮Agent覆盖。
4. Executor1800→3600采用两道固定题、两个全新臂、同一源码/driver，只改变next_command的max_output_tokens。结果{comparison['decision']}；按原始记录与预注册条件解释，未替换失败题、未调评分、未自适应补跑，生产默认1800未改。基线WEB-02的Planner返回HTTP200/natural stop但content为空，8496输出token均计reasoning，未进入RWKV；它不是余额402。详细length及逐项条件见预算COMPARISON.json。
5. 原126行完成34原标签+68纠正+24reject；新43行完成18原标签+16纠正+9reject。共169条待审全部处置，136双审接受、33拒绝；一票否决，不要求改签。74自动+136双审=210候选按预注册边界聚类保留20（15/3/2），190行明确排除，原5评估anchor不变；超相似对0/81。最终20中3条train与中间20不同，已在预检R2更正R1文字并对最终全部20重跑normalize，20/20通过。
6. 首轮Selector StateTune没有启动或伪登记：execute仍0，候选INVALID；freeze_dataset重提取尚未传递waiver与注册筛选规则。optimizer steps=0，无正式角色data/datasets新版本。首次freeze可在合格候选生成固定regression后不带prior；三重pin只在复用既有regression时必需，不能变成循环禁训门。Agent低分与后序角色未到达不是这里的禁令，owner既有训练/AI复核授权仍有效。

下一步的实际工作是修复可再现的冻结接口，并预注册能产生真实execute阶段/命令证据的生产采集。不得通过改phase、硬塞命令、删掉覆盖门或绕过重建来开训；全部数据条件通过后再登记具体预算、模型/数据/训练器/State身份，执行zero-State注入与optimizer steps>0的smoke。五角色架构暂维持，流程单变量轮仍遵循既定顺序。

验证：WSL完整tests/ 1455 passed，0failed/0skipped；之后rwkv_lh/scripts/tests/依赖锁相对21c0cf45无改动。所有本轮封存证据逐文件SHA复验通过；各报告和清单完整SHA见EVIDENCE_INTEGRITY_VERIFICATION.json。未读Real Agent Holdout V2。
'''
(O/'REPORT.zh-CN.md').write_text(status)
old=(R/'docs/HANDOFF.zh-CN.md').read_text();boundary=old.index('2026-09-10 [充值后执行复测R2]')
intro=f'''# 当前交接

**当前能力：已证明在给定工作区写入代码文件，尚未证明可靠自主创建并交付项目。** 最新三轮独立Agent结果如下，不合并分母：

{table}
最新全流程状态见[六项继续执行结果](../data/experiments/SELECTOR_GATE_CONTINUATION_R1_20260910/REPORT.zh-CN.md)。指定f34e4964与21c0cf45已push；当前部署根`/home/chase/GitHub/RWKV-LH-audit-fanout-r1-20260910`，项目manifest SHA `f7569e52896794cda754bce231ea9d449b5013516fd2dfc890064f0099343926`，engine SHA `5c229e24e9158a5d66df8c67d508c2934044766f49dbea39f4a89d64080c1d74`，服务完整文件身份与健康通过，服务器无Git。生产源码保持21c0cf45，完整回归1455 passed/0failed/0skipped。

[重签](../data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910/REPORT.zh-CN.md)已双AI accept，waiver `f53186ecfca2f97126b132f41b1bc37bdef46e77ce91b3cde4a68385ef0a3aaa`恢复原14来源60候选、126待审行。[旧126复核](../data/experiments/SELECTOR_SEMANTIC_REVIEW_R1_20260910/REPORT.zh-CN.md)和[新43复核](../data/experiments/SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910/REPORT.zh-CN.md)均已完成处置：136共同接受、33拒绝，待审0。按[预注册去重](../data/experiments/SELECTOR_SIMILARITY_POLICY_R1_20260910/REPORT.zh-CN.md)，210→20（15train/3dev/2confirmation），原5anchor不变，超相似对0/81。

[新四题采集](../data/experiments/COMMAND_PATH_COLLECTION_R1_20260910/REPORT.zh-CN.md)仍check/run=0、execute=0，命令路径覆盖目标未达到。[预算试验](../data/experiments/EXECUTOR_OUTPUT_BUDGET_R1_20260910/REPORT.zh-CN.md)为{comparison['decision']}，生产Executor默认1800不变。[最终训练预检R2](../data/experiments/SELECTOR_TRAINING_PREFLIGHT_R2_20260910/REPORT.zh-CN.md)纠正R1中间/最终行相同的文字，已对实际最终20条全部normalize通过。候选仍INVALID：缺execute覆盖，freeze_dataset又未接通waiver/筛选再现。首轮尚未登记、optimizer steps=0；首次freeze不要求虚构prior，已有regression复用才要求三重pin。owner授权有效，低分不是禁训门；下一步补真实execute来源与冻结接口，再按数据门登记smoke/首训。

以下R2及更早段落是冻结历史，旧文中的“尚未部署”“待重签”“仅授权waiver”及旧源码首错缺陷状态以以上最新证据为准。后续本地记录提交按AGENTS由owner push。

'''
(R/'docs/HANDOFF.zh-CN.md').write_text(intro+old[boundary:])
plan=R/'docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md';lines=plan.read_text().splitlines();lines[2]='更新日期：2026-09-11。适用于当前生产、数据抽取、训练登记和评测；owner最新指令优先。当前结果与具体未满足数据门统一见[当前交接](HANDOFF.zh-CN.md)：审计扇出源码已部署，指定提交已push，双AI重签/语义复核及预注册相似度处置已落地；新四题仍未到命令路径，Executor预算独立轮未KEEP。首次冻结可无prior，复用既有regression才要求三重pin；不得把它改成循环禁训门。Agent低分不禁训，真实execute覆盖与可再现冻结条件尚待满足，optimizer steps=0。后续规范门槛不因本轮结果改写。';plan.write_text('\n'.join(lines)+'\n')
pipeline=R/'docs/STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md';pl=pipeline.read_text().splitlines();pl[2]='更新日期：2026-09-11。新四题Agent采集Strict 0/4、completed 0/4、mutation 0、动作13；三题重复动作无进展，一题Executor协议拒绝。独立Executor1800/3600预算轮结果见[当前交接](HANDOFF.zh-CN.md)，不得混算不同轮次。指定源码提交已push并部署21c0cf45，完整回归1455 passed/0failed/0skipped。原14来源精确waiver已双AI accept；旧126与新43待审全部处置（136共同接受、33拒绝）。74自动+136双审共210候选，按预注册聚类保留20（15/3/2），原5验证anchor不变，超相似对0/81；execute仍0，候选INVALID。最终20条已全部经生产normalize校验，源zero/tokenizer条件通过，详情及R1文字更正见[预检R2](../data/experiments/SELECTOR_TRAINING_PREFLIGHT_R2_20260910/REPORT.zh-CN.md)。freeze_dataset尚未传递waiver与筛选策略再现，首训/optimizer smoke未启动，steps=0。首次freeze可无prior，只有复用既有regression才要求三重pin；不把Agent低分或缺prior造成循环禁训。';ptext='\n'.join(pl)+'\n';ptext=ptext.replace('`scripts/run_state_tune.py freeze` 重新从生产 trace 抽取并核对完整候选清单，原子发布 train 与固定 regression；训练入口仅解析 train','`scripts/run_state_tune.py freeze` 基础重提取/原子发布已接通，训练只读train；当前waiver与预注册去重派生来源的精确再现尚未接通，不能绕过校验直接消费');pipeline.write_text(ptext)
(O/'helpers').mkdir();shutil.copyfile(Path(__file__),O/'helpers'/Path(__file__).name)
write(O/'DOCUMENT_REFERENCES.json',{'files':[{'path':str(p),'sha256':sha(p)} for p in (R/'docs/HANDOFF.zh-CN.md',plan,pipeline)]})
files=[{'path':str(p.relative_to(O)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(O.rglob('*')) if p.is_file()]
write(O/'EVIDENCE_SHA256.json',{'round':O.name,'files':files,'referenced_rounds':verified,'optimizer_steps':0})
print(json.dumps({'report_sha256':sha(O/'REPORT.zh-CN.md'),'evidence_sha256':sha(O/'EVIDENCE_SHA256.json'),'verified_files':sum(x['files_verified'] for x in verified)}))
