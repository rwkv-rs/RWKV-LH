# B01 全 zero State 基线结果

分类：`valid_zero_state_capability_failure`。

- Strong Planner：GPT-5.6 成功提交一个三步嵌套阶段计划；无 Supervisor failure。
- Goal 终止：未出现合法 `final_answer`，240/240 transitions 后保持 `status=running`，未伪装完成。
- RWKV：239 次请求；53 次 Selector 决策、52 次成功工具动作、136 次协议拒绝。
- 工具选择：53 次全部为 `list_directory`；52 次动作也全部为 `list_directory`。
- next-state：53/53 个 Selector 输入都有 `GoalFrontierStateV1`；52/52 个后续输入都有上一动作和 Auditor feedback。
- 工具描述：53/53 个 Selector 输入中的候选工具名称和描述全部非空。
- State 连续性：第一个 parent 为空；后续 52/52 个 parent digest 与上一 Selector state digest 匹配。
- 提示格式：239/239 个 G1J 生成输入以 `**Tool Call:**` 和 ` ```json` 锚点结尾；`Assistant: ```json` 为 0。
- 工作区：7 个初始文件内容哈希保持不变；没有越界修改。

结论：已排除 next-state 未更新、工具描述缺失、混合提示格式、空 HTTP 输出、工程外 Executor 和 Strong Planner 失败。当前可复核的 zero-State 能力边界是：Selector 即使持续收到动作结果与 repair gap，仍不能从目录枚举转向必要的文件读取；随后 Executor 的长 State 输出退化为非单一 JSON。该结果进入能力分母，`full_task_success=false`。

机器可读证据：

- `B01_S20260903_RESULT.json`
- `B01_S20260903_BASELINE_METRICS.json`
- `B01_S20260903_WORKSPACE_SHA256.json`
- `cases/PUBLIC-CANARY-B01-S20260903/audit.json`
