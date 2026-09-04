# B09 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是基础设施失败：239 次 RWKV 请求和 1 次 Strong 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- 外部黑盒验收 4 项通过 2 项；构建脚本仍不会创建输出父目录，嵌套输出测试因 `FileNotFoundError` 失败。

## State 与工具上下文核验

- Selector 决策 50 次，首轮从全 zero State 开始，后续 49/49 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 50/50 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具名称、描述。
- 49/49 个后续输入包含最近动作和最近 Step Auditor 反馈。
- 本次 Selector 能在 `list_directory` 与 `move_file` 标签之间切换，因此不能简单归因为菜单完全塌缩到单一标签。

## 行为轨迹

- 50 次 Selector 决策包含 28 次 `list_directory` 和 22 次 `move_file`。
- 49 次已执行动作包含 27 次目录枚举和 22 次文件移动，Harness 均返回成功。
- 22 次 `move_file` 的源路径与目标路径完全相同，工作区摘要变化为 0；这些只算工具调用成功，不算修复或迁移成功。
- Step Auditor 的 49 条记录全部可解析并以 `repair` 被接受，没有 Step Auditor 协议拒绝。
- Executor 在动作阶段之后产生 141 次协议拒绝，最终耗尽 transition budget。
- Strong Planner 生成 S1–S4 四步计划，但没有任何步骤完成，最终 frontier 仍为 S1。
- 所有 239 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

本次展示了零 State Selector 的有限标签切换能力，但 Executor 把移动操作参数化为同源同目标，未修改 `scripts/build_report.py`，也未创建任何所需父目录。Auditor 连续返回 `repair` 后，系统仍未形成有效修改，随后 Executor 进入长期 JSON 协议退化。最终失败属于冻结的全 zero State 参数在工具语义选择、写操作参数生成、反馈利用和长上下文格式稳定性上的能力不足，而非 next-state、工具描述或基础设施缺失。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B09_S20260903_RESULT.json`
- `B09_S20260903_BASELINE_METRICS.json`
- `B09_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B09-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B09-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B09-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B09-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B09-S20260903/state_timeline.json.gz`
