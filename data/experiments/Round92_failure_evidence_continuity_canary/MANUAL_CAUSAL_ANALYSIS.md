# Round92 逐题人工因果分析

## 固定结果

- Agent completed：`3/4`
- External acceptance：`3/4`
- Strict E2E：`3/4`
- FP：`0`
- FN：`0`
- 四题终态回答均非空，并与各自 RWKV Final lane 原始输出一致。

## E2E-B01

- Strict PASS，保持 Round91 的最短成功链。
- RWKV 写入后首次过早完成被拒绝，随后自行选择 `read_file`，再显式完成 Task 和 Goal。
- completion readiness 没有绕过 RWKV；Task 仍由第二次 `lh_task_done` 收口。

## E2E-B02

- Strict FAIL / External FAIL。
- Goal lane 仍只创建读取 input.txt 的首个 Task；这是可恢复的渐进分解，前提是该 Task 能完成后返回 Goal lane继续扩展。
- `read_file` 成功后，action result 明确包含 `completion_protocol_ready=true`、`structural_evidence_satisfied=true` 和完整文本内容。
- 第一次剩余偏离仍来自 RWKV：它没有选择 Task 完成，而是显式选择 `read_json(input.txt)`，该操作真实触发 `JSONDecodeError`。
- failure event 也说明先前成功观察继续有效，但第一次重复抑制之后的 `task_operation_rejected` 和新建 recovery capsule 没有继续携带 completion readiness，也没有把 Task 的 `done_when` 紧邻放在完成决策旁。此后 RWKV 固定重复 `read_json`。
- `function_args` 完整语义外壳已被新转换层接入；另一个缺少显式 `operation` 的 flattened 输出继续正确拒绝。不能从历史调用替它补 `read_json` 或 `lh_task_done`。
- 根因：RWKV 首次操作选择错误；协议在 rejection/rebuild 后丢失完成决策状态，放大为稳定循环。

## E2E-B03

- Strict PASS；Round91 的 FN 已消除。
- `function_args`、canonical wrapper、flattened wrapper 和 direct flattened `lh_task_done` 均按显式字段归一化。
- 每个 mutation 后仍要求 RWKV 自行补只读观察；三个 Task 均由 RWKV 显式完成，Goal 和 Final 正常收口。
- 尝试数由 Round91 的 4 次增加到 6 次，是模型本轮具体路径差异；质量判定通过，未使用外部验收驱动运行时完成。

## E2E-H04

- Strict PASS；Round91 的 FN 已消除。
- 写入后第一次完成被正确拒绝；RWKV自行选择 `read_file`，readiness 投影明确后选择 `lh_task_done`。
- 未再出现多余 `read_json`，说明跨失败证据连续性和紧凑 readiness 对同类链路有效。

## 下一处通用整改

统一所有 Task lane 反馈的完成决策投影：紧邻展示 RWKV 原始 `done_when`、结构协议 readiness、缺口和条件式调用形状；`action_result`、`failure_observed`、`task_operation_rejected`、`task_protocol_rejected`、recovery capsule 不再各自丢字段。Controller 仍不得解释 `done_when`，不得自动完成，也不得根据外部验收选择任何操作。
