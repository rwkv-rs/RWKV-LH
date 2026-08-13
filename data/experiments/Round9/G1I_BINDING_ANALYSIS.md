# Round9 Single-Claim G1i Binding 专项分析

本分析只在 90 题结束后读取 hidden acceptance 与 Codex reference。

Round9 External `15/90`、Strict `0/90`、Agent completed `0/90`、FP `0*`、FN `15`。17 题触发 33 个
single-claim scope，共 66 次 response、180,488 local prompt token；0 次通过标准 G1i 归一，0 proof claim、
0 CriterionEvidence。

- 63/66 输出 `{bind_criterion_assertion: ...}`，被拒绝为未知顶层字段。
- 其余 3 次分别输出裸 binding/locator 字段、裸 `path`、`tool_name/input_args/result` 变体。
- 6 个触发 Phase B 的案例外部正确，但都没有 evidence 或 completion。

因此 Round9 反驳“只套用单工具表就足以复用 action lane 成功”。action lane 同时明确要求 canonical
`{name, arguments}` 外层；Round9 的任务正文只说调用工具，弱 RWKV稳定采用工具名作顶层 key。不能在 parser
事后接受该新形态，因为那会把本轮观测到的错误注册成成功。下一轮只能预注册并复用 action lane 的精确 canonical
framing，同时保持同一个 G1i normalizer 和 proof 边界。

机器明细见 `g1i_binding_analysis.json`。
