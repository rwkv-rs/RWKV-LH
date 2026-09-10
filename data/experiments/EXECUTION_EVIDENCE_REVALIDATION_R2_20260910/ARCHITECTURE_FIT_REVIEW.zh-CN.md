# 五角色架构正式适配复核：R2 补证

充值后独立 R2：**Strict 0/7、completed 0/7、mutation 2、动作 18**。终止原因：identical_success_budget_exhausted: 5；protocol_rejection_budget_exhausted: 1；goal_audit_protocol_rejection_budget_exhausted: 1。

同源码、同参数的 15 题关联视图（R1 已生成 8 题 + R2 补做 7 题）：**Strict 0/15、completed 0/15、mutation 6、动作 46**。终止原因：protocol_rejection_budget_exhausted: 4；identical_success_budget_exhausted: 10；goal_audit_protocol_rejection_budget_exhausted: 1。这是跨运行、逐题标注来源的覆盖视图，不是新的一次性 15 题运行；R1 原始 Strict 0/15、completed 0/15、mutation 4、动作 28 和七次 HTTP402 记录保留，不改分。

**结论：保持五角色职责作为后续逐角色验证的工作架构；本次 Agent KEEP 不成立，也没有支持推翻五角色的受控对比证据。** 分工使部分根因可定位，但不能把可归因等同于能力证明。全部完成数为零，后两个角色未观察，本轮没有同代码合并角色消融或足够的双零噪声估计，不能宣称 adjacency 原则已经获得比较验证。

## 原 KEEP 判据

| 判据 | 证据 | 结论 |
| --- | --- | --- |
| 不再出现首错丢失 unknown 死链 | RP-CLI-02 已进入 RWKV；四角色真实工厂离线恢复证明底层首错仍丢日志。现有实际最终事件仍可读，底层恢复发生次数不可由零日志确定 | 未通过，存在审计接线缺陷 |
| Su 下降 | 固定最新基线 0，关联 15 题 0；本次 Supervisor 请求失败 0。R1 七次402独立保留 | 没有严格下降证据 |
| Strict 不劣化 | 固定基线 0/15，关联视图 0/15 | 数值持平；零分下限不能证明没有能力回归 |

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
