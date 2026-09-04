# B06 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是请求前基础设施失败：238 次 RWKV 请求和 2 次 Strong 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- Strong Planner 使用 GPT-5.6，S1 完成后 Claude Stage Checker 接受阶段证据；这是本轮首个完成 Planner 阶段的公开用例。
- 工作区未发生越界写入，但配置兼容迁移未实现，外部单元测试仍有 2 个失败。

## State 与工具上下文核验

- Selector 决策 47 次，首轮从全 zero State 开始，后续 46/46 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 47/47 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具描述。
- 45 个动作后输入包含最近动作和最近 Step Auditor 反馈；跨阶段边界按新 frontier 重建当前步骤投影。
- 候选菜单明确区分目录枚举与文件移动等职责，本次不能归因为工具职责未披露。

## 行为轨迹

- 47 次 Selector 决策包含 27 次 `list_directory` 和 20 次 `move_file`，证明全 zero State Selector 能在特定任务语义下切换工具标签。
- 46 次已执行动作包含 26 次目录枚举和 20 次文件移动，Harness 均返回成功。
- 20 次 `move_file` 的源路径与目标路径相同，属于成功返回的 no-op，未形成配置兼容迁移的语义进展。
- 计划包含 S1–S5；S1 已完成，stage 1 已关闭，最终 frontier 位于 S2。
- 协议拒绝共 170 次：Executor 146 次、Step Auditor 24 次。
- 所有 238 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

本次展示了局部 Agent 能力：目录勘察可形成足够的 S1 证据，并通过独立 Stage Checker；Selector 也能从目录枚举切换到移动标签。然而 Executor 未能为移动工具生成有意义的不同源/目标参数，随后长 State 又进入输出协议退化。最终失败属于冻结的全 zero State 参数语义与长上下文稳定性不足，而非 next-state、工具描述或基础设施缺失。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B06_S20260903_RESULT.json`
- `B06_S20260903_BASELINE_METRICS.json`
- `B06_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B06-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B06-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B06-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B06-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B06-S20260903/state_timeline.json.gz`
