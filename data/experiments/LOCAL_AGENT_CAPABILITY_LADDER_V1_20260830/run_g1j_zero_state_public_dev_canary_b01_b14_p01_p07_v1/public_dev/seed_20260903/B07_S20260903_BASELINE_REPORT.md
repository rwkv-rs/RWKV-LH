# B07 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是请求前基础设施失败：239 次 RWKV 请求和 1 次 Strong 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- 外部黑盒验收 5 项通过 2 项；目标 `outputs/region_summary.json` 未创建，验证脚本退出码为 1。

## State 与工具上下文核验

- Selector 决策 57 次，首轮从全 zero State 开始，后续 56/56 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 57/57 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具名称、描述。
- 56/56 个后续输入包含最近动作参数、完整 Harness 结果和最近 Step Auditor 反馈。
- Step Auditor 多次明确指出需要读取 `scripts/verify_region_summary.py` 和 `data/orders.csv`，因此本次不能归因为 next-state 丢失或工具职责未披露。

## 行为轨迹

- 57 次 Selector 决策全部选择 `list_directory`。
- 56 次已执行动作全部为目录枚举，Harness 均返回成功；没有读取文件内容，也没有创建目标输出。
- Step Auditor 生成 56 条可解析记录，其中 50 条合法 `repair` 被接受；另有 6 次 Step Auditor 协议拒绝。
- Executor 在有效动作之后产生 127 次协议拒绝，最终耗尽 transition budget。
- Strong Planner 生成 S1–S3 三步计划，但没有任何步骤完成，最终 frontier 仍为 S1。
- 所有 239 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

本次 next-state、parent WKV、工具描述和 Auditor gap 均已真实到达下一轮，但全 zero State Selector 仍持续把“读取脚本和数据内容”的当前目标映射为 `list_directory`。在 56 次成功但无语义进展的目录枚举后，Executor 又进入长期 JSON 协议退化。最终失败属于冻结的全 zero State 参数在工具语义路由、利用反馈和长上下文格式稳定性上的能力不足，而非状态更新、工具描述或基础设施缺失。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B07_S20260903_RESULT.json`
- `B07_S20260903_BASELINE_METRICS.json`
- `B07_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B07-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B07-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B07-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B07-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B07-S20260903/state_timeline.json.gz`
