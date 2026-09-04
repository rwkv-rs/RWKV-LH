# B08 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是基础设施失败：239 次 RWKV 请求和 1 次 Strong 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- 外部黑盒验收 8 项通过 5 项；非目标示例与归档配置保持不变，但活动配置未更新，验证命令退出码为 1。

## State 与工具上下文核验

- Selector 决策 66 次，首轮从全 zero State 开始，后续 65/65 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 66/66 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具名称、描述。
- 65/65 个后续输入包含最近动作和最近 Step Auditor 反馈。
- 当前 frontier 明确列出活动实现、验证脚本、活动配置、示例配置和归档配置的读取范围；本次不能归因为工作区目标或工具职责未披露。

## 行为轨迹

- 66 次 Selector 决策全部选择 `list_directory`。
- 65 次已执行动作全部为目录枚举，其中 12 次成功、53 次失败；没有读取文件内容，也没有修改活动配置。
- Step Auditor 记录 65 次，其中 57 次可解析、31 次合法 `repair` 被接受；另有 34 次 Step Auditor 协议拒绝。
- Executor 在动作阶段之后产生 109 次协议拒绝，最终耗尽 transition budget。
- Strong Planner 生成 S1–S3 三步计划，但没有任何步骤完成，最终 frontier 仍为 S1。
- 所有 239 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

本次 State 连续传递、动作结果、Auditor 反馈和工具描述均已到达下一轮，但全 zero State Selector 始终没有从目录枚举转移到文件读取或修改。重复目录调用中多数参数指向无效位置，随后 Executor 又进入长期 JSON 协议退化。最终失败属于冻结的全 zero State 参数在工具路由、路径参数生成、利用失败反馈和长上下文格式稳定性上的能力不足，而非 next-state、工具描述或基础设施缺失。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B08_S20260903_RESULT.json`
- `B08_S20260903_BASELINE_METRICS.json`
- `B08_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B08-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B08-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B08-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B08-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B08-S20260903/state_timeline.json.gz`
