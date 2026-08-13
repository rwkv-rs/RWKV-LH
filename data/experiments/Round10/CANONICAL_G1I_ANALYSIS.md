# Round10 canonical G1i 因果分析

Round10 只在 criterion binding prompt 中明确 canonical `{name, arguments}` 外层，没有新增 parser、字段补全、候选选择或答案修改。结果是外壳到达率显著改善，但 Strict 仍为 `0/90`，证明瓶颈已经从外层 JSON 迁移到 assertion 参数与 evidence ownership。

## 结果

- External `15/90`，Strict `0/90`，Completed `0/90`，FP `0`，FN `15`。
- 15 个 case、33 个 claim scope 发起 51 次请求，得到 51 个响应，消耗 145987 prompt tokens。
- 50/51 个响应通过透明 `schema_validation_only`；其中 50 个 input/normalized payload byte-structure 等值且 transformations 为空。
- 36 次协议/合约错误：`{"model_contract_error: assertion transform contract is invalid": 23, "model_contract_error: action_output_json argument fields must be exactly []": 8, "model_contract_error: action_output_text argument fields must be exactly []": 2, "model_protocol_error: ValueError: G1i tool call has unknown fields: ['artifact_id', 'task_id']": 1, "model_contract_error: goal_literal argument fields must be exactly ['goal_quote', 'value']": 1, "model_contract_error: workspace_json argument fields must be exactly ['path']": 1}`。
- 87 个 assertion evaluation：binding valid 69、invalid 18；空 claim 74、单 claim 13。
- 18 个 binding-invalid evaluation 中，18 个记录为 `{"RWKV must emit exactly one assertion for each declared criterion": 18}`。
- 13 个单 claim 都达到 exact coverage，但 proof passed 为 0；claim proof 拒绝为 `{"ProofEvaluationError: proof ref is not a direct dependency": 9, "ProofEvaluationError: json_pointer must be empty or start with '/'": 4}`。
- VERIFIED CriterionEvidence 为 0。

## 与 Round9 的因果差异

Round9 是 66 个响应、0 个规范化调用、66 个外壳错误、0 claim。Round10 降到 51 个响应，规范化升到 50，协议/合约错误降到 36，并首次产生 13 个单 claim。这证明 canonical 外层提示是有效的协议边界改进；但所有 claim 都在确定性 proof 被拒，且 External/Strict 不变，所以它不是端到端改进检查点。

## 下一步含义

不应继续扩展外壳 coercion。下一步需要让 RWKV在计划/执行时保留 producer→consumer 的直接依赖和可用 JSON Pointer，并将精确机器错误返回给 RWKV recovery；Controller 仍只能验证引用存在性、依赖关系、hash 和 pointer 语法，不能替模型选择引用或修正参数。
