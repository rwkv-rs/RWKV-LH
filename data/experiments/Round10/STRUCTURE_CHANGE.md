# Round10 结构变更

- 唯一变量是 criterion assertion Phase B 的 prompt framing：明确要求整个响应使用 canonical G1i
  `{name, arguments}`，且顶层只能有 `name`、`arguments` 两个键。
- 固定 tool name 仍为 `bind_criterion_assertion`；动态 arguments schema、Phase A intent、proof、evidence、
  completion、sampling 与恢复逻辑全部继承 Round9。
- 线上 G1i normalizer 没有增加新外壳、字段猜测、arguments 补全、候选投票或语义 coercion。
- raw output、parsed payload、normalized payload 和 transformations 全量进入逐题 audit；50 个成功 normalization
  全部为 `schema_validation_only`，input/normalized payload 等值，transformations 为空。

本轮没有修改、筛选或替换 RWKV 的动作参数、proof claim 与最终输出，也没有在生成阶段读取 hidden
acceptance 或 Codex 标准答案。
