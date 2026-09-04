# B10 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是基础设施失败：239 次 RWKV 请求和 1 次 Strong 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- 外部黑盒验收 8 项通过 6 项；输入中的四处版本信息本来已经一致，但 Agent 没有创建要求的 `reports/version_audit.json`，验证脚本失败。

## State 与工具上下文核验

- Selector 决策 56 次，首轮从全 zero State 开始，后续 55/55 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 56/56 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具名称、描述。
- 55/55 个后续输入包含最近动作结果和最近 Step Auditor 反馈。
- 因此本例中的重复工具选择不能归因为 next-state 未传递或工具描述缺失。

## 行为轨迹

- 56 次 Selector 决策全部选择 `list_directory`；55 次动作均为成功的目录枚举。
- Step Auditor 记录 55 条，其中 52 条可解析、42 条以 `repair` 被接受，另有 13 次 Step Auditor 协议拒绝。
- Executor 有 129 次协议拒绝；两类协议拒绝合计 142 次，最终耗尽 transition budget。
- Strong Planner 生成 S1–S3 三步计划，但没有任何步骤完成，最终 frontier 仍为 S1。
- 所有 239 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

本例的初始版本文件已经互相一致，实际目标是读取审计输入并生成报告。虽然当前阶段、最近动作结果、Auditor 修复反馈和完整工具说明都持续进入 Selector，冻结的全 zero State Selector 仍重复枚举目录，没有转入文件读取或报告写入；Executor 随后长期产生 JSON 协议拒绝。最终失败属于 zero-State 参数在反馈利用、工具切换和长程格式稳定性上的能力不足，而非 next-state、工具描述或基础设施缺失。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B10_S20260903_RESULT.json`
- `B10_S20260903_BASELINE_METRICS.json`
- `B10_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B10-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B10-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B10-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B10-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B10-S20260903/state_timeline.json.gz`
