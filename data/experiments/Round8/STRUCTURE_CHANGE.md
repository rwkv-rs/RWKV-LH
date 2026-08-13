# Round8 结构变更

Round8 实施 `copy_resistant_assertion_binding_contract.v1`，继续借鉴 Prime Agent 的模型边界协议工程：

- Phase A 的 operator/criterion/subject/producer 选择不变；
- Phase B 的 selected contract 从 JSON metadata 对象改为逐 claim 的非 JSON 固定行协议；
- 行协议只显示 ordinal、criterion、actual/expected operator 与 required argument names；
- 输出仍严格要求原 `long-horizon.assertion-binding.v1`，parser、字段、参数、transform 和 proof 均未放宽；
- 新增 `assertion_binding_contract_prepared` 审计事件，保存原 intents 和实际渲染合同；
- raw output、parsed payload、contract error、merged assertion、normalization/proof trace 完整保留。

运行时没有删除 extra fields、补 arguments、替换 operator/evidence、尝试候选或修改 final；未复制 Prime Agent
代码，也未引入 provider、subagent、RLM、TUI 或 MCP。
