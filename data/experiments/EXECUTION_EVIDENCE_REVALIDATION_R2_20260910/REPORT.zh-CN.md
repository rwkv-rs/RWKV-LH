# 充值恢复后的执行修复复测 R2

充值后独立 R2：**Strict 0/7、completed 0/7、mutation 2、动作 18**。终止原因：identical_success_budget_exhausted: 5；protocol_rejection_budget_exhausted: 1；goal_audit_protocol_rejection_budget_exhausted: 1。

同源码、同参数的 15 题关联视图（R1 已生成 8 题 + R2 补做 7 题）：**Strict 0/15、completed 0/15、mutation 6、动作 46**。终止原因：protocol_rejection_budget_exhausted: 4；identical_success_budget_exhausted: 10；goal_audit_protocol_rejection_budget_exhausted: 1。这是跨运行、逐题标注来源的覆盖视图，不是新的一次性 15 题运行；R1 原始 Strict 0/15、completed 0/15、mutation 4、动作 28 和七次 HTTP402 记录保留，不改分。

## 逐题结果

| 题目 | Strict | completed | mutation | 动作 | 原始终止原因 |
| --- | ---: | ---: | ---: | ---: | --- |
| RP-CLI-02 | 0 | 0 | 0 | 3 | identical_success_budget_exhausted |
| RP-DATA-01 | 0 | 0 | 0 | 3 | identical_success_budget_exhausted |
| RP-DATA-02 | 0 | 0 | 0 | 3 | identical_success_budget_exhausted |
| RP-FULL-01 | 0 | 0 | 0 | 3 | identical_success_budget_exhausted |
| RP-FULL-02 | 0 | 0 | 0 | 0 | protocol_rejection_budget_exhausted |
| RP-WEB-01 | 0 | 0 | 0 | 3 | identical_success_budget_exhausted |
| RP-WEB-02 | 0 | 0 | 2 | 3 | goal_audit_protocol_rejection_budget_exhausted |

本轮 Supervisor 最终请求失败 0，输出耗尽中断 0；关联 15 题分别为 0 和 0。输出耗尽统计检查所有已记录响应，包括重试前响应。原 R1 的 HTTP402 与 SupervisorGenerationInterrupted 分开计数。最新固定 15 题基线 Su 已是 0，本轮 0 不能叫“下降”，也不能换用早先两次中断的 R5 来宣称满足门槛。

**KEEP 未通过。** Strict 数值持平，但都是 0 分；关联十五题最终 `model_transport_failure` 事件 0。Native 首错审计存在真实工厂接线缺口，零事件不能证明无首错丢失。详见本轮 `NATIVE_AUDIT_WIRING_FINDING.zh-CN.md`。离线四角色 POST/404/404/POST 恢复全部成功却未送达首错；这是新增可复核的工程缺陷，不是一次真实线上故障发生次数。R1 对 Native 零日志的过强解释由本报告更正，封存原文不篡改。

## 角色与证据

R2 Selector 选择边界 27；生成次数 {"executor_args": 41, "auditor_step": 19}。已返回 60 次完整输入 token 与 60 次角色输入字节核验全部通过。关联 15 题角色生成次数 {"executor_args": 115, "auditor_step": 45}。Finalizer / Final Auditor 未到达不能视为通过；字节一致不是标签正确或 Agent 能力通过。

RP-FULL-02 的 12 次 Executor 输出均为 length，恰好耗尽既定 1800 token，未闭合 JSON；最后按原逻辑协议拒绝预算阻塞，不能混入 strong Supervisor 的中断计数。原始输出、request ID、SHA 和每次预算见 `RP-FULL-02.PUBLIC_ACTION_GENERATION_FACTS.json`。本轮不增输出额度、不修改 parser/stop boundary、不重评分；该任务不能只标为纯语法能力缺陷。

RP-WEB-02 还有 6 次 Executor length，之后成功两次写入 index.html，最终 Step Auditor 反复生成不满足 continue 条件或字段集合的决策而阻塞。全 R2 Executor length 共 18 次；两次写入不是任务完成。该题动作只有一次 search_text 和两次 write_file，没有执行 check_command / run_command，因此历史 WEB-02 命令路径未由本轮 Agent 实际覆盖。

R2 七题现有私有黑盒验证器均由 runner 调用，四题带 browser 要求，已有日志中 2 题出现 Playwright 诊断。只读取调用/退出码/隔离元数据并哈希输出，未读取私有实现或期望值。验证器早期失败不等于完成页面交互验证；本轮没有借 browser=true 宣告 Web 验收成功。详见 `VERIFIER_EXECUTION_METADATA.json`。

## 冻结、范围与验证

Owner 原文“我充值好了，可以继续使用了”授权后，只选择原 R1 初始 Planner HTTP402 且 RWKV/action 均为 0 的全部七题。`BALANCE_RECOVERY_REGISTRATION.json` 固定前身结果 SHA、选择规则和新预算；不是按成绩挑题。每题 1800 秒、200 transitions、全角色 zero、同模型采样、native_transport_resume_attempts=1，实际耗时 1933.425 秒。底层 `run_case` 的默认值为 0，CLI 默认 1，因此此驱动显式传 1。原始 REGISTRATION 的 metrics 描述继承了源 12 题套件分母；实际 task_ids 明确七题，本报告与原始 case 结果按七题汇总，不修改冻结登记。

客户端生产源码等于 b3e89de6，e00b1809 只提交 R1 文档和证据。R2 前后及 R1 两套运行的源码文件清单、runner、Supervisor、四角色、sampling、stateful_goal、tokenizer、Selector 身份均逐项相等，见 `LINKED_15_TASK_SUMMARY.json`。服务完整源码清单在 R1 已实际核验，R2 沿用同一运行配置与 Native 身份；服务器无 Git 操作。没有修改 rwkv_lh/、测试、评分或协议。

完整回归沿用冻结生产源码的 1447 passed、0 failed、0 skipped（244.64 秒）成功记录；初次并行 pytest 的共享 basetemp 冲突和串行全绿日志均保留于 R1。成功日志 SHA `220f17aa00ec149b617123cc7b7a52818dd54fe9d081028eac334d4e5d0c228a`。R2 只增加审阅和记录，未再无理由重复全套测试。所有后续脚本执行结果及现有 case 交接均另留证。

## Waiver 与后续结论

双 AI reviewer 的明确授权已执行。原六文件全量 draft 没有直接改成 accept；独立审阅后只批准 14 个旧来源、仅 Selector 的绑定范围，整题排除旧 check_command 语义受影响的 RP-WEB-02。两份精确审批、waiver、scope 与 CLI wrapper 相互 pin，正式提取已完成，旧九边界 / 27 行逐字节保留。恢复 60 自动候选、126 待复核；因 execute=0、跨切分相似度 101/281 超阈值仍 INVALID。无语义标签通过、无新训练数据版本、optimizer steps=0。详见 R1 `WAIVER_RESULT.md`；本次充值补跑不扩大该 waiver。

正式架构结论见 `ARCHITECTURE_FIT_REVIEW.zh-CN.md`：保留五角色职责继续验证有依据，宣布架构能力通过没有依据。三项流程改进仍在首轮 StateTune 后各自单变量登记；Native 审计接线是另一个工程正确性缺口，不能通过训练掩盖。

## 证据定位

`AGENT_SUMMARY.json` SHA `b505998a6601aa27374b19ba61fccaae837539f3d03d78b1aadae23036373b0c`；`LINKED_15_TASK_SUMMARY.json` SHA `b849bd84dc03ab4ec60e518725eb19461fbf6e83196d5c599c258824be7719b5`。逐题原始结果在 `all_zero/`；完整原 trace / SQLite 在按项目规则忽略提交的 `all_zero/cases/` 中本地保留，公开因果审阅、参数、结果、脚本和逐文件 SHA 随轮次提交。不能把被 Git 忽略的原始工件称为已推送。全目录文件路径与 SHA 最终登记在 `EVIDENCE_SHA256.json`。未读取 Real Agent Holdout V2，未训练，未 push。
