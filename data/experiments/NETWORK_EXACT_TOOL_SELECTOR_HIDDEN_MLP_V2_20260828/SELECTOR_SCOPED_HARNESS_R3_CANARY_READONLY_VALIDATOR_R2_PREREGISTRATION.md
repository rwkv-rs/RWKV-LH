# Scoped Harness R3 canary 只读完整性复核 R2 预登记

## 原因

R1 已完成固定 B01/B02/B04 的全部生成，随后冻结的 V8 validator 在读取
`RUN_PROTOCOL.json` 时要求旧的无 Planner 架构字符串
`independent-selector-executor.v2-request-last`。本轮实际且预期的架构是
`strong-planner-reviewer-rwkv-contract-graph.v2`，所以 validator 在逐 case
原始输出检查前退出。R1 无效登记中的结果、协议和日志摘要全部冻结。

## 只读修正规则

1. 不启动 2.9B Selector、13.3B Executor、Planner 或任何 vLLM 服务；新增 RWKV 请求必须为 0。
2. 不修改 R1 的 `results.json`、`RUN_PROTOCOL.json`、audit、model trace、event log、
   causal ledger、Selector log 或 Executor log。
3. 新 wrapper 只在旧 validator 的内存视图中把已核验的 contract-graph architecture
   字符串投影成旧 validator 能识别的 legacy 字符串；不会写回该投影。
4. wrapper 必须另外对真实 `RUN_PROTOCOL.json` fail closed，要求：
   architecture 精确等于 `strong-planner-reviewer-rwkv-contract-graph.v2`；Supervisor
   enabled；mode 为 `contract_graph`；tool execution authority 为 false；
   RWKV output rewritten 为 false；hidden acceptance visible 为 false。
5. 其余模型、profile request delivery、S60 identity、25 logits、handoff、生成输入与原始生成
   一一对应关系继续使用冻结 V8/V7/base validator 原口径，不改变断言。
6. derived integrity 文件允许新增；任何原始证据摘要变化都必须失败。

## 固定门槛

- 3/3 固定 case 都存在，且每 case `model_requests > 0`；
- 3 份 audit 中 scoped-menu mismatch 为 0；
- frozen validator 完整通过，case count=3；
- generation inputs 等于 raw generations，且大于 0；
- committed + rejected Selector outputs 大于 0，每条 raw selection 有 25 logits，
  `postprocessed=false`；
- raw outputs modified/deleted 为 false；
- R1 六个冻结证据文件的 SHA-256 前后完全一致；
- 新增模型/Selector/Planner 请求为 0。

本轮只裁决 Harness 子集 bug 是否已越过，不把 B01/B02/B04 的严格成功率当作正式能力结论。
