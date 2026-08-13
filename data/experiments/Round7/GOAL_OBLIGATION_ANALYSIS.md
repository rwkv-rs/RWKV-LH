# Round7 Goal Obligation Expansion 专项分析

本分析只在 90 题全部结束后读取 hidden acceptance 与冻结的 Codex reference；两者没有进入 initial plan、
obligation ledger、supplemental planning、action、proof 或任何 RWKV 请求。

## 结论

Goal obligation ledger 正确地把“结构计划已合法”和“required criterion 尚未被 RWKV 分配”拆成了两个状态，
但本轮实现没有形成可上传的完成改进：External `12/90`、Strict `0/90`、Agent completed `0/90`、FP
`0*`、FN `12`。相对 Round6，External 增加 6，但仍没有任何完成，且模型请求从 657 增至 1148。

## 逐层漏斗

- 76/90 形成了结构合法的 initial plan；14/90 仍在 initial plan schema/protocol 阶段阻断。
- 36/76 的 ledger 为空，40/76 存在 1–5 个 required obligation 缺口。
- 40 个非空 ledger 共触发 69 次 supplemental 请求；15 题接受扩图，25 题在一次 correction 后仍阻断。
- 15 个 accepted case 新增 44 个 supplemental task，其中 15 个标题、19 个描述与 base task 完全相同。
- accepted cohort 执行 94 个 action，产生 3 个 External pass；ledger-complete cohort 执行 196 个 action，
  产生另外 9 个 External pass。
- 15 个 accepted case 全部没有 Agent completion；3 个 External pass 是 E2E-B05、E2E-B15、E2E-M12，
  最终仍因 Goal evidence 缺失或后续协议阻断而失败。

## 因果判断

集合差 ledger 本身可以借鉴：它只投影 Immutable Goal 与 RWKV `satisfies_criteria` 的机械差集，没有给 task
分配 criterion，也没有生成答案。它使 15 个原本会在完整计划 coverage gate 被丢弃的任务图进入真实执行，
其中 3 个达到外部正确，证明显式剩余状态不是纯粹的空操作。

当前 supplemental task 生成方式不应继续原样扩张。RWKV 经常复制 base task 再添加
`satisfies_criteria`，导致 44 个新增 task 中出现大量 exact duplicate；这放大了 action、validation 和 proof
请求，却没有增加完成。仅 obligation lane 的 69 次返回请求就包含 252,486 个本地 prompt token；其中完整
action contract 对只输出结构 task 的 lane 也形成额外上下文压力。

Round7 同时暴露出更直接的下游瓶颈：criterion binding 中 53 次 contract error 是模型把输入侧的
`actual_read_op/expected_read_op/*_required_argument_keys` 元数据复制进输出 binding。此问题可以通过只改变模型
边界的合同呈现方式继续消融；不得在 parser 中删除多余字段或替 RWKV 选择 evidence/operator。

机器明细见 `goal_obligation_analysis.json`。
