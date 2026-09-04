# B03 全 zero State Agent 基线报告

## 结论

- 分类：`valid_zero_state_capability_failure`
- Goal 在冻结的 240 transitions 内未完成；状态保持 `running`，没有 `final_answer`，没有进入 Finalizer 或 Final Auditor。
- 本次不是请求前基础设施失败：239 次 RWKV 请求和 1 次 Strong Planner 请求均进入正式轨迹，`supervisor_failure.failed=false`。
- 工作区未发生越界写入，但目标 JSON 未修改，验证脚本仍返回 1。

## State 与工具上下文核验

- Selector 决策 57 次，首轮从全 zero State 开始，后续 56/56 个 `selector_parent_state_digest` 均与前一轮 Selector State digest 一致。
- 57/57 个 Selector 输入均包含 `GoalFrontierStateV1` 和完整候选工具描述。
- 56/56 个后续输入均包含最近动作；56/56 个后续输入均包含最近 Step Auditor 反馈。
- 典型审计反馈明确指出“未读取 `config/runtime.json`”和“未检查 `scripts/validate_runtime_config.py`”；候选菜单同时明确提供 `read_json`、`read_file` 和 `check_command` 的职责描述。

## 行为轨迹

- 57 次 Selector 决策全部为 `list_directory`。
- 56 次已执行动作全部为成功的 `list_directory`。
- 当前计划包含 S1、S2、S3，但完成步骤数为 0，frontier 始终停在 S1。
- 协议拒绝共 144 次：Executor 127 次、Step Auditor 17 次。Executor 长 State 后主要产生未闭合 Markdown 围栏或非单一合法 JSON。
- 所有 239 个 G1J 生成输入均以唯一冻结格式 `**Tool Call:**` + ` ```json` 结束；没有 `Assistant: ```json` 混合格式。

## 失败归因

旧链路中的“Selector next-state 未承接”和“候选工具缺少语义描述”在本次轨迹中均被直接证据否定。当前失败是全 zero State 模型行为：Selector 虽持续接收到最新动作结果、审计缺口和完整工具描述，仍不能从目录枚举切换到文件读取；随后 Executor 在增长的同角色 State 中逐渐失去单一 JSON 输出稳定性。

本报告只描述冻结基线，不执行 Head 训练、StateTune、参数调整或用例特判。

## 可复核制品

- `B03_S20260903_RESULT.json`
- `B03_S20260903_BASELINE_METRICS.json`
- `B03_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B03-S20260903/audit.json`
- `cases/PUBLIC-CANARY-B03-S20260903/causal_ledger.json`
- `cases/PUBLIC-CANARY-B03-S20260903/model_trace.json`
- `cases/PUBLIC-CANARY-B03-S20260903/event_log.json`
- `cases/PUBLIC-CANARY-B03-S20260903/state_timeline.json.gz`
