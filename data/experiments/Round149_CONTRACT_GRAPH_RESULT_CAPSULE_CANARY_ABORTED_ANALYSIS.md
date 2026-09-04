# Round149 Contract Graph Canary：传输期中止分析

日期：2026-08-22

状态：**INVALID / ABORTED，不计质量分，不与 baseline 比较**。

## 中止原因

固定 13 题启动后，B04、H09 均在初始 `contract_plan`、任何 RWKV action 之前耗尽 3 次 transport
retry，并以 HTTP 500 中断。为避免其余 case 继续重复同一高成本请求，主进程被人工停止；因此其余
running/KeyboardInterrupt 状态不是模型质量结果。

原始目录：`data/experiments/Round149_contract_graph_result_capsule_canary_20260822/`。

## 可复核发现

- B04、H09：各 1 个逻辑 Planner request，最终 HTTP 500，无 patch、batch、RWKV outcome。
- M10：Planner 首次响应因非 verbatim clause 被本地拒绝，第二次响应成功；随后 RWKV writer 的精确
  result 为 transient failure，但 worker natural-language candidate 错称第二次写入成功。result capsule
  没有传 candidate，而是把 `success=false`、`InjectedTransientToolFailure` 交给 Reviewer；Reviewer
  未接受并触发 correction Planner。这证明结果隔离边界按设计工作。
- B09：首次响应的 node_id 与 atom_id 不同，被本地不变量拒绝；修复调用在人工中止时尚未返回。

## 根因与运行前整改

1. 新架构首次响应输出整张图，继续沿用旧 stage 的 1800-token 上限过小；复杂 B04/H09 更容易在
   服务端生成期表现为 500。为 contract plan 单独设置 4000 tokens，review 设置 2400 tokens。
2. Provider 被要求重复输出 `node_id == atom_id` 和完整 immutable request clauses，增加输出 token，
   且制造无业务价值的语义修复。新 schema 只输出 atom_id；node_id、obligation request_clause 和
   atom request_clauses 由本地从 immutable request 确定性注入，持久化不变量保持不变。
3. 审计新增每次物理 HTTP attempt 事件和 failed-call attempt 数，后续同时报告逻辑 GPT 调用与真实
   HTTP 调用，不能用逻辑调用掩盖 transport retry 成本。

先运行固定 B04 单题 transport/schema smoke；通过后才重新预注册 13 题 canary。
