# Round94 E2E-B02 人工因果分析

## 结果

- Agent PASS / External FAIL / Strict FAIL，仍为 FP。
- Final 非空且等于 RWKV 原始输出，但错误声称 report.json 已创建。

## 与 Round93 不同的真实链路

1. input.txt 读取 Task 正常完成。
2. Goal 回流事件仍包含 `all_required_tasks_complete=true`。该字段只表示当前已计划前沿完成，却容易被理解成整个不可变 Goal 已完成。
3. RWKV 首次 Goal 回答从 `lh_goal_done` 开始，并在 params 中递归复制大量 `observations_verify_passed_reason...` 字段，达到输出上限后 JSON 未闭合，原始长度约 17KB。
4. 因 JSON 整体无法解析，Controller 没有得到 `LaneDecision`，所以本轮新增的“已解析 function 锁定”没有触发；correction event 中 `required_next_function` 为空。
5. 下一次 RWKV 返回可解析 `lh_goal_done`，并自报 report_written/report_verified，但真实证据只有 input.txt 读取。当前 void completion validator忽略这些注释，Controller错误结束 Goal。

## 根因

- Goal progress 投影名称错误：Task frontier 完成被表达为 `all_required_tasks_complete`。
- Goal progress 只依赖早期 transcript 中的 immutable Goal，没有在完成决策旁紧邻重放完整目标。
- `lh_goal_done` 工具 schema 的 `additionalProperties=true` 鼓励弱模型复制和扩张证据注释，导致截断和协议恢复丢失原 function。
- 已完成 Task 的 Goal 投影仍携带较早被后续成功 commit 淘汰的 `task_step=false`，增加上下文矛盾。

## 下一步

- 改为 `current_task_frontier_complete`，明确 `goal_completion_not_implied`。
- 在每次 Goal completion decision 旁原样投影 immutable Goal。
- `lh_goal_done` schema 明确 params 必须 `{}`，raw audit仍保留历史/非规范输出。
- Goal 只投影权威 effect observations 和当前 Task commit，不把旧 protocol-rejected task_step当作当前事实。
