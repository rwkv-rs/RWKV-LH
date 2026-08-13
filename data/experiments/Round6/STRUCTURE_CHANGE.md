# Round6 结构变更

Round6 实施 `progressive_disclosure_read_operator_assertion.v1`，借鉴 Prime Agent/G1i 的模型边界与渐进披露：

- validation v4 Phase A 只要求 RWKV 选择具体 read operator，不同时填写全部 source/selector 参数；
- Phase B 只显示所选 operator 的 required argument keys，由 RWKV 填入 arguments/transforms；
- 运行时按 intent 顺序一一合并，不删除字段、不补参数、不拆联合值、不选候选；
- read operator 到 ProofExpr 是登记式 exact 映射，所有 operator/参数/transform 都由 RWKV 选择；
- semantic replan 不进入 binding；semantic pass + binding/proof fail 仍保持 Task semantic pass，但不生成 Goal
  evidence；
- raw Phase A、raw Phase B、combined assertion、normalization trace、proof refs 与最终重放完整保留；
- request temperature 新增 strict `criterion_assertion_binding=0.03`，其他采样、工具、计划、恢复和 final 不变。

未复制 Prime Agent 代码，未引入 provider/subagent/RLM/TUI/MCP；未读取 hidden acceptance 或标准答案生成
operator、argument、transform、expected 或 final answer。
