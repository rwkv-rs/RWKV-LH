# Round150：Compact Contract Schema B04 Smoke 预注册

日期：2026-08-22

## 目的

只验证 Round149 中止后、运行前确定的两项控制面整改：contract plan 独立 4000-token 预算，以及
不再由 GPT 重复 node_id/request clauses 的 compact response schema。数据、verifier、RWKV sampling、
full tool disclosure 和 B04 请求均不修改。

## 固定运行

- case：E2E-B04；concurrency=1；RWKV atom concurrency=4。
- GPT-5.4 请求串行；transport retry=3；semantic repair=2。
- strategy=`contract_graph`；max transitions=200；graph patch/review/atom budgets 与 Round149 相同。

## 通过门

1. 初始 Planner 返回并提交合法 patch，不以 HTTP 500、node/atom ID 或 request clause 错误终止。
2. 至少一个 RWKV work batch 执行；Reviewer 请求只含 result capsules，无 worker process 字段。
3. 逻辑 Planner 首次响应无需 semantic repair；物理 HTTP attempts 有明确审计。
4. strict PASS、Final byte-exact raw RWKV、GPT tool execution=0。

任一失败则不重启 13 题 canary，继续修复对应根因。
