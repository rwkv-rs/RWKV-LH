# Round91 逐题人工因果分析

## 固定结果

- 数据集：`E2E-B01`、`E2E-B02`、`E2E-B03`、`E2E-H04`
- Agent completed：`1/4`
- External acceptance：`3/4`
- Strict E2E：`1/4`
- FP：`0`
- FN：`2`（`E2E-B03`、`E2E-H04`）
- 四题均产生非空终态回答，且四题终态回答均与 RWKV Final lane 的原始输出完全一致。

本文件只使用本轮冻结源码、模型原始调用、Controller 事件、Attempt 结果和运行结束后的外部验收作事后归因。外部验收未进入任何模型上下文，也没有用于运行时选择操作、参数或答案。

## E2E-B01

- 结果：Agent PASS / External PASS / Strict PASS。
- Goal lane 创建一个 `file_content_read` Task。
- Task lane 先调用 `read_file`，随后基于可见结果调用 `lh_task_done`。
- Goal lane 基于已完成 Task 调用 `lh_goal_done`，Final lane 返回非空回答。
- 本题证明原子 Task call、直接 Task 完成、Goal 收口和终态回答的最短链可以贯通。

## E2E-B02

- 结果：Agent FAIL / External FAIL / Strict FAIL。
- 第一次偏离：Goal lane 只创建“读取 input.txt”的一个 `file_content_read` Task，尚未创建写入和验证 `report.json` 的后续 Task。这不是立即致命；完成读取 Task 后，Goal lane仍可继续扩展下一批 Task。
- 正确环节：`T1-A1 read_file(input.txt)` 成功，已经满足该 Task 声明的结构证据类型。
- 放大起点：Action result 只给出通用的“完成或继续”提示，没有明确投影“现有 Task-owned 证据合同已经满足”。RWKV 随后多做 `read_json(input.txt)`，真实返回 `JSONDecodeError`。
- 结构放大：一次较晚的失败把 Task 标成 `FAILED`；failure recovery 强调失败操作和换操作，却没有明确说明更早的成功读取仍是权威证据，也禁止 failure recovery 中直接选择 `lh_task_done`。
- 循环：RWKV 反复选择同一个 `read_json`。unchanged-action 抑制阻止重复执行，但无法让 RWKV 看清已有证据仍可用于 Task 收口。
- 格式放大：一次 correction 使用带 `metadata/payload/recovery/task` 注释的 `function_args` 调用；旧转换层拒绝了这一具有完整显式语义的等价调用。另一些输出缺少显式 operation，必须继续拒绝，不能由 Controller 推断。
- 终态：blocked；RWKV Final 如实返回非空失败说明。
- 根因类别：Task 证据状态投影不完整 + failure recovery 错误抹平既有成功证据；Goal 欠分解是模型行为，但原本可在 Task 收口后继续修复。

## E2E-B03

- 结果：Agent FAIL / External PASS / Strict FAIL，属于 FN。
- Goal lane 创建读取、更新、验证三个 Task，证据类型分别为 `file_content_read`、`workspace_mutation`、`file_content_read`。
- `T1` 先成功读取 `config.json`，随后提前执行 `patch_json`，再按 completion rejection 补一次成功 `read_json`，最终显式调用 `lh_task_done`。虽然操作跨越了 Goal lane 原有 Task 划分，但工作区更新正确，Task lane 也有真实读取证据。
- `T2` 再执行相同 `patch_json`，此时目标值已存在。外部目标已经满足。
- 第一次协议偏离：RWKV 用
  `function=lh_task_done + top-level task_id + operation_arguments`
  表达 Task 完成。所有语义字段由 RWKV 明确给出，但旧转换层没有接入这个常见等价外壳。
- 后续格式放大：RWKV 多次用 `function_args` 承载完整的 `task_id/operation/operation_args`，也被旧转换层拒绝。
- 状态放大：Action result 没有直接投影“workspace_mutation 已存在、但最新 mutation 后仍缺独立只读观察”这一协议事实，RWKV继续选择相同 patch，而不是自行选择读取或完成。
- 终态：unchanged-action loop 后 blocked；Final lane 仍返回非空且承认部分完成。
- 根因类别：等价调用外壳接入缺口 + Task completion readiness 投影缺口。外部正确不是 Controller 自动完成的授权；仍需 RWKV 显式收口。

## E2E-H04

- 结果：Agent FAIL / External PASS / Strict FAIL，属于 FN。
- Goal lane 创建一个 `file_content_read` Task；RWKV 成功写入 `safe/result.txt`。
- 第一次 `lh_task_done` 被正确拒绝，因为声明的 `file_content_read` 证据尚未存在。
- RWKV 随后成功 `read_file(safe/result.txt)`，此时 Task 已同时拥有真实写入结果和独立文件内容读取，结构完成前置条件已经齐全，且外部验收已通过。
- 第一次行为偏离：RWKV 没有完成 Task，而是额外调用 `read_json` 读取纯文本文件，真实失败。
- 结构放大：较晚失败使 Task 进入 `FAILED`，failure recovery 未明确保留早先成功读取的完成资格，并禁止从 failure recovery 显式 `lh_task_done`。
- 格式放大：其后多个带完整显式操作的 `function_args` 调用被旧转换层拒绝；canonical correction 又在 read_json/write_file 间循环。
- 终态：unchanged-action loop 后 blocked；RWKV Final 明确说明文件已存在但运行 blocked，回答非空且未经 Controller 改写。
- 根因类别：失败状态覆盖成功证据 + completion readiness 未投影 + `function_args` 等价外壳接入缺口。

## 跨题共因与整改边界

1. `B02/H04` 都在已有成功读取后多做一次 `read_json`，随后失败状态掩盖了更早的有效 Task-owned 证据。
2. `B03/H04` 都出现完整显式语义的 `function_args` 调用被协议层拒绝；这是转换层接入问题，不是模型语义错误。
3. `B02/B03/H04` 都缺少紧凑、明确、确定性的 completion-readiness 投影。Controller 可以展示结构证据是否存在，但不能解释自然语言 `done_when`，也不能替 RWKV 调用 `lh_task_done`。
4. 转换层只可搬运 RWKV 已显式提供的 function、task_id、operation 和 operation arguments；缺 operation 的 `mode + operation_arguments` 输出继续拒绝，严禁根据历史调用补出 `read_json` 或其他操作。
5. 外部验收只用于事后 Strict/FP/FN 统计；`B03/H04` 的外部通过不能在运行时触发自动完成。

下一轮的预注册改动应同时覆盖：保留失败前成功证据、允许 RWKV 在 failure recovery 中显式完成、投影结构 completion readiness、接入 `function_args` 和完整显式的扁平 direct Task operation。验证仍使用相同四题，先看 Strict、FP/FN 和原始终态回答，再扩大全集。
