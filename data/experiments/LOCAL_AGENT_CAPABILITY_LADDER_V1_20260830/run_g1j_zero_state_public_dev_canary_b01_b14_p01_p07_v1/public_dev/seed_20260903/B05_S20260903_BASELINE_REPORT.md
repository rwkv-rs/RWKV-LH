# B05 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是请求前基础设施失败：239 次 RWKV 请求和 1 次 Strong Planner 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- 工作区未发生越界写入，但路径规范化实现未修复，外部单元测试仍有 3 个失败。

## State 与工具上下文核验

- Selector 决策 63 次，首轮从全 zero State 开始，后续 62/62 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 63/63 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具描述。
- 62/62 个后续输入均包含最近动作和最近 Step Auditor 反馈。
- 候选菜单明确区分目录元数据、文件读取、文本搜索、修改命令和只读测试；本次不能归因为工具职责未披露。

## 行为轨迹

- 63 次 Selector 决策全部为 `list_directory`。
- 62 次已执行动作仍全部为 `list_directory`，其中 2 次成功、60 次失败。
- 当前计划包含 S1、S2、S3，完成步骤数为 0，frontier 停留在 S1。
- 协议拒绝共 117 次：Executor 115 次、Step Auditor 2 次。
- 所有 239 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

Selector next-state、动作结果、审计反馈和完整工具描述在本次轨迹中均持续存在。全 zero State Selector 仍只选择目录枚举，并且 Executor 将该工具用于不适配的目标路径，造成大量动作失败；随后长 State 又出现输出协议退化。该失败属于冻结基线的模型行为，而非本轮基础设施故障。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B05_S20260903_RESULT.json`
- `B05_S20260903_BASELINE_METRICS.json`
- `B05_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B05-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B05-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B05-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B05-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B05-S20260903/state_timeline.json.gz`
