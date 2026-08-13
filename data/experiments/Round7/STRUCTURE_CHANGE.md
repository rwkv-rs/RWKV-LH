# Round7 结构变更

Round7 实施 `rwkv_goal_obligation_expansion.v1`，借鉴 Prime Agent 的显式状态与模型边界协议工程：

- initial plan 在 schema、TaskGraph、criterion scope 合法时先被保留，不因 coverage 不完整重写整个计划；
- Controller 只计算 required Goal criterion id 与 RWKV `satisfies_criteria` 声明的集合差；
- ledger 非空时，由同一 RWKV 返回 supplemental tasks，程序不自动分配 criterion、不修改 base task；
- supplemental task 可引用 base/new local id，combined graph 再执行完整 scope、coverage、cycle 与 materialization
  校验；
- raw initial plan、ledger、raw supplemental response、combined local graph 与最终 global task graph完整保留；
- obligation assignment 不生成 CriterionClaim/CriterionEvidence，也不绕过 action、semantic validation 或 proof；
- request type `goal_obligation_planning` 固定使用 task decomposition 的 temperature `0.18`。

未复制 Prime Agent 代码，未引入 provider/subagent/RLM/TUI/MCP；未读取 hidden acceptance 或标准答案生成 task、
criterion、action、proof 或 final answer。
