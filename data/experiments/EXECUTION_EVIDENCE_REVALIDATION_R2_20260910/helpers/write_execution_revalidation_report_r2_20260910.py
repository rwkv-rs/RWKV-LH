"""Write final R2 reports from immutable results; no scoring or production edits."""
from collections import Counter
from pathlib import Path
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
R1 = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
def read(path):
    return json.loads(path.read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    with (OUT / name).open('x') as stream:
        stream.write(value)
summary = read(OUT / 'AGENT_SUMMARY.json')
linked = read(OUT / 'LINKED_15_TASK_SUMMARY.json')
evidence = read(OUT / 'ROLE_AND_INFRASTRUCTURE_EVIDENCE.json')
verifiers = read(OUT / 'VERIFIER_EXECUTION_METADATA.json')
completion = read(OUT / 'COMPLETION.json')
a, b = summary['agent'], linked['agent']
if not (a['counts_complete'] and completion['source_unchanged'] and a['recorded'] == 7):
    raise SystemExit('Incomplete or changed-source run')
def agent_line(agent, denominator):
    return f"Strict {agent['strict']}/{denominator}、completed {agent['completed']}/{denominator}、mutation {agent['mutation_count']}、动作 {agent['action_count']}"
def term(agent):
    return '；'.join(f'{key}: {value}' for key, value in agent['termination_reasons'].items())
rows = '\n'.join(f"| {r['task_id']} | {int(r['strict'])} | {int(r['completed'])} | {r['mutation_count']} | {r['action_count']} | {r['termination']} |" for r in summary['cases'])
role_calls = Counter()
for case in linked['cases']:
    role_calls.update(case['role_calls'])
browser_rows = [row for row in verifiers['cases'] if any(check['browser'] for check in row['project_behavior_checks'])]
browser_diagnostics = sum(any(check['playwright_diagnostic_present'] for check in row['project_behavior_checks']) for row in browser_rows)
common = f"""充值后独立 R2：**{agent_line(a, 7)}**。终止原因：{term(a)}。

同源码、同参数的 15 题关联视图（R1 已生成 8 题 + R2 补做 7 题）：**{agent_line(b, 15)}**。终止原因：{term(b)}。这是跨运行、逐题标注来源的覆盖视图，不是新的一次性 15 题运行；R1 原始 Strict 0/15、completed 0/15、mutation 4、动作 28 和七次 HTTP402 记录保留，不改分。
"""
report = f"""# 充值恢复后的执行修复复测 R2

{common}
## 逐题结果

| 题目 | Strict | completed | mutation | 动作 | 原始终止原因 |
| --- | ---: | ---: | ---: | ---: | --- |
{rows}

本轮 Supervisor 最终请求失败 {a['supervisor_failures']}，输出耗尽中断 {a['supervisor_generation_interruptions']}；关联 15 题分别为 {b['supervisor_failures']} 和 {b['supervisor_generation_interruptions']}。输出耗尽统计检查所有已记录响应，包括重试前响应。原 R1 的 HTTP402 与 SupervisorGenerationInterrupted 分开计数。最新固定 15 题基线 Su 已是 0，本轮 0 不能叫“下降”，也不能换用早先两次中断的 R5 来宣称满足门槛。

**KEEP 未通过。** Strict 数值持平，但都是 0 分；关联十五题最终 `model_transport_failure` 事件 {b['runtime_transport_failures']}。Native 首错审计存在真实工厂接线缺口，零事件不能证明无首错丢失。详见本轮 `NATIVE_AUDIT_WIRING_FINDING.zh-CN.md`。离线四角色 POST/404/404/POST 恢复全部成功却未送达首错；这是新增可复核的工程缺陷，不是一次真实线上故障发生次数。R1 对 Native 零日志的过强解释由本报告更正，封存原文不篡改。

## 角色与证据

R2 Selector 选择边界 {evidence['selector']['boundaries']}；生成次数 {json.dumps(evidence['role_calls'], ensure_ascii=False)}。已返回 {evidence['generation_contexts_verified']} 次完整输入 token 与 {evidence['role_inputs_verified']} 次角色输入字节核验全部通过。关联 15 题角色生成次数 {json.dumps(dict(role_calls), ensure_ascii=False)}。Finalizer / Final Auditor 未到达不能视为通过；字节一致不是标签正确或 Agent 能力通过。

RP-FULL-02 的 12 次 Executor 输出均为 length，恰好耗尽既定 1800 token，未闭合 JSON；最后按原逻辑协议拒绝预算阻塞，不能混入 strong Supervisor 的中断计数。原始输出、request ID、SHA 和每次预算见 `RP-FULL-02.PUBLIC_ACTION_GENERATION_FACTS.json`。本轮不增输出额度、不修改 parser/stop boundary、不重评分；该任务不能只标为纯语法能力缺陷。

RP-WEB-02 还有 6 次 Executor length，之后成功两次写入 index.html，最终 Step Auditor 反复生成不满足 continue 条件或字段集合的决策而阻塞。全 R2 Executor length 共 18 次；两次写入不是任务完成。该题动作只有一次 search_text 和两次 write_file，没有执行 check_command / run_command，因此历史 WEB-02 命令路径未由本轮 Agent 实际覆盖。

R2 七题现有私有黑盒验证器均由 runner 调用，四题带 browser 要求，已有日志中 {browser_diagnostics} 题出现 Playwright 诊断。只读取调用/退出码/隔离元数据并哈希输出，未读取私有实现或期望值。验证器早期失败不等于完成页面交互验证；本轮没有借 browser=true 宣告 Web 验收成功。详见 `VERIFIER_EXECUTION_METADATA.json`。

## 冻结、范围与验证

Owner 原文“我充值好了，可以继续使用了”授权后，只选择原 R1 初始 Planner HTTP402 且 RWKV/action 均为 0 的全部七题。`BALANCE_RECOVERY_REGISTRATION.json` 固定前身结果 SHA、选择规则和新预算；不是按成绩挑题。每题 1800 秒、200 transitions、全角色 zero、同模型采样、native_transport_resume_attempts=1，实际耗时 {completion['wall_seconds']:.3f} 秒。底层 `run_case` 的默认值为 0，CLI 默认 1，因此此驱动显式传 1。原始 REGISTRATION 的 metrics 描述继承了源 12 题套件分母；实际 task_ids 明确七题，本报告与原始 case 结果按七题汇总，不修改冻结登记。

客户端生产源码等于 b3e89de6，e00b1809 只提交 R1 文档和证据。R2 前后及 R1 两套运行的源码文件清单、runner、Supervisor、四角色、sampling、stateful_goal、tokenizer、Selector 身份均逐项相等，见 `LINKED_15_TASK_SUMMARY.json`。服务完整源码清单在 R1 已实际核验，R2 沿用同一运行配置与 Native 身份；服务器无 Git 操作。没有修改 rwkv_lh/、测试、评分或协议。

完整回归沿用冻结生产源码的 1447 passed、0 failed、0 skipped（244.64 秒）成功记录；初次并行 pytest 的共享 basetemp 冲突和串行全绿日志均保留于 R1。成功日志 SHA `{sha(R1 / 'PYTEST_ISOLATED.log')}`。R2 只增加审阅和记录，未再无理由重复全套测试。所有后续脚本执行结果及现有 case 交接均另留证。

## Waiver 与后续结论

双 AI reviewer 的明确授权已执行。原六文件全量 draft 没有直接改成 accept；独立审阅后只批准 14 个旧来源、仅 Selector 的绑定范围，整题排除旧 check_command 语义受影响的 RP-WEB-02。两份精确审批、waiver、scope 与 CLI wrapper 相互 pin，正式提取已完成，旧九边界 / 27 行逐字节保留。恢复 60 自动候选、126 待复核；因 execute=0、跨切分相似度 101/281 超阈值仍 INVALID。无语义标签通过、无新训练数据版本、optimizer steps=0。详见 R1 `WAIVER_RESULT.md`；本次充值补跑不扩大该 waiver。

正式架构结论见 `ARCHITECTURE_FIT_REVIEW.zh-CN.md`：保留五角色职责继续验证有依据，宣布架构能力通过没有依据。三项流程改进仍在首轮 StateTune 后各自单变量登记；Native 审计接线是另一个工程正确性缺口，不能通过训练掩盖。

## 证据定位

`AGENT_SUMMARY.json` SHA `{sha(OUT / 'AGENT_SUMMARY.json')}`；`LINKED_15_TASK_SUMMARY.json` SHA `{sha(OUT / 'LINKED_15_TASK_SUMMARY.json')}`。逐题原始结果在 `all_zero/`；完整原 trace / SQLite 在按项目规则忽略提交的 `all_zero/cases/` 中本地保留，公开因果审阅、参数、结果、脚本和逐文件 SHA 随轮次提交。不能把被 Git 忽略的原始工件称为已推送。全目录文件路径与 SHA 最终登记在 `EVIDENCE_SHA256.json`。未读取 Real Agent Holdout V2，未训练，未 push。
"""
write('REPORT.zh-CN.md', report)
architecture = f"""# 五角色架构正式适配复核：R2 补证

{common}
**结论：保持五角色职责作为后续逐角色验证的工作架构；本次 Agent KEEP 不成立，也没有支持推翻五角色的受控对比证据。** 分工使部分根因可定位，但不能把可归因等同于能力证明。全部完成数为零，后两个角色未观察，本轮没有同代码合并角色消融或足够的双零噪声估计，不能宣称 adjacency 原则已经获得比较验证。

## 原 KEEP 判据

| 判据 | 证据 | 结论 |
| --- | --- | --- |
| 不再出现首错丢失 unknown 死链 | RP-CLI-02 已进入 RWKV；四角色真实工厂离线恢复证明底层首错仍丢日志。现有实际最终事件仍可读，底层恢复发生次数不可由零日志确定 | 未通过，存在审计接线缺陷 |
| Su 下降 | 固定最新基线 0，关联 15 题 {b['supervisor_generation_interruptions']}；本次 Supervisor 请求失败 {b['supervisor_failures']}。R1 七次402独立保留 | 没有严格下降证据 |
| Strict 不劣化 | 固定基线 0/15，关联视图 {b['strict']}/15 | 数值持平；零分下限不能证明没有能力回归 |

完整旧十五题已经各有至少一次充值前或后的真实模型执行证据，不再把 R1 七题402称作仍待充值。但关联视图不能伪装成一次性运行，原始 R1 原分数不可替换。RP-WEB-02 是否触及历史命令问题，只按真实动作记录判断；未执行对应命令不等于命令行为已获 Agent 验证。

## 三项流程弱点的正式判断

1. **执行证据与审计合同。** R1 RP-API-01 的 Step Auditor 将列目录当作内容读取完成，随后 Stage Checker明确指出缺失内容证据，并成功触发 Planner 修正。R1 ULTRA-Code_00001 的早期成功条件却只要求创建 main.py，正确性被推迟；该假推进同时涉及上游成功条件，不能全部归罪于 Auditor。R2 WEB-01 错误 continue 被本地合同拒绝，之后 Auditor 改为 repair，说明已有约束能拦部分错误，但仍不等于审计语义正确。R2 WEB-02 在 README 中搜索 README 只返回第8行单行约束；CE-000025/27 的 Step Auditor 和 CE-000030 的 Stage Checker 均视为满足“读取README内容与大小”。单行与完整当前文件内容不是同一证据，Stage Checker 也不总能兜底。应收紧的是从上游成功条件到角色裁决的证据合同，不能把修复局限为单个审计提示词。

2. **无进展与计划调整。** 大量 repair 后仍重复查找或列目录，最终真实标为阻塞。API-01 已存在有依据的 Planner 二次修正，故“从不再调 Planner”不是全局事实。不能添加“重复即强制多调模型”的状态机掩盖 RWKV 问题。计划调整需继续由计划遗漏、依赖或目标覆盖证据授权；角色训练应使模型从已有反馈作出有效下一动作。

3. **反馈利用与动作形成。** DATA-01 在越界路径反馈后把 `.` 改成 `README.md`，但在 Auditor repair 后连续三次执行完全相同的 `public interface` 搜索。它能改一个参数，却没有稳定补全读取证据。R1 MAINT-01 有 repair 后换为 read_file 并推进的反例，所以“反馈完全无效”过强。单凭选择 search_text 不能判定 Selector 错误：该工具也可返回所需内容，需结合目标、参数和实际结果分离 Selector 与 Executor 责任。

上述三项各自独立预注册，仍排在首轮 StateTune 后；不改合法菜单、不按题特判、不用外置 Head 或额外模型替代职责。首轮训练继续受当前 Selector 数据覆盖、切分、独立标签和登记预算约束，不被后两角色未到达或 Agent 低分本身禁止。

## 本轮补充的两个具体限制

Native 首错审计接线缺陷已经在真实工厂离线复现，影响生产和 benchmark，必须作为独立工程正确性事项修复。完整回归1447通过没有覆盖工厂把底层日志送入角色 sink 的场景。此项未修复，不可写成“首错问题已解决”；详见 `NATIVE_AUDIT_WIRING_FINDING.zh-CN.md`。

RP-FULL-02 不是正常结束的十二份坏 JSON：十二次 Executor 都 length=1800，第一次输出还出现重复扩展的 helper 函数。真实终止原因保持 protocol_rejection_budget_exhausted，同时注明输出耗尽的因果证据。WEB-02 也有六次 Executor length，随后两次真实写入，但最终由 Step Auditor 非法决策阻塞；没有触及历史 check/run 命令路径。改预算或生成策略若成为下一轮假设，须独立登记、保持其他变量固定；本轮不即时加 token 重跑挑最好分，也不把它计成 DeepSeek 的 Su。持续会话 E5 仍仅设计与可行性探针，本轮没有落地实现或进入成功 Web 端到端验收。

## 可复核材料

本轮逐题 `PUBLIC_CAUSAL_OBSERVATION.json` / `PUBLIC_ACTION_GENERATION_FACTS.json`、原 model_trace 与 ROLE_AND_INFRASTRUCTURE_EVIDENCE，及 R1 `ARCHITECTURE_CASE_NOTES.md` / `ARCHITECTURE_FIT_REVIEW.zh-CN.md`。R1 对 Native 零事件的强结论以本轮更正为准，旧文件不修改。脚本和全部材料 SHA 在证据清单；本轮只评测与评估，未训练、未改变生产代码。
"""
write('ARCHITECTURE_FIT_REVIEW.zh-CN.md', architecture)
print(json.dumps({'report_sha256': sha(OUT / 'REPORT.zh-CN.md'),
                  'architecture_sha256': sha(OUT / 'ARCHITECTURE_FIT_REVIEW.zh-CN.md')}, ensure_ascii=False))
