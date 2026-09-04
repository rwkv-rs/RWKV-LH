# Round150 Compact Contract Schema B04 分析

日期：2026-08-23

## 结论

Round150 **FAIL**。B04 在任何 RWKV request/action 前中断：1 个逻辑 `contract_plan`，3 个物理 HTTP
attempt，均在上游返回 HTTP 500。compact clause/node-id 注入和 4000-token 上限没有单独消除失败，
因此不启动 13 题 canary。

原始目录：`data/experiments/Round150_compact_contract_schema_B04_20260822/`。

## 新证据

- 运行约 93 秒，符合 3 次约 30 秒的上游生成/网关边界，而不是本地立即 schema validation。
- run 中 `model_requests=0`、`action_count=0`；失败发生在 Planner transport，不能归因于 RWKV。
- Round149 的 M10 简单整图曾成功返回，而复杂 B04/H09 连续失败；整图输出复杂度/推理时长仍是主假设。

## 下一项固定整改

进一步把 contract Planner wire schema 压为最小节点：只返回 atom id、role、objective、dependency、
roots、单 operation 和 action budget。exclusive、request clauses、completion checks、constraints 均由
本地 immutable obligations 与 operation catalog 确定性派生。contract schema 名升级至 v2，避免第三方
gateway 对同名 grammar 的不透明缓存。

同时增加可选 `SUPERVISOR_REASONING_EFFORT`。根据官方 OpenAI reasoning 指南，降低 reasoning effort
会减少思考量和推理 token；Round151 对第三方 Chat Completions 兼容层显式试用 `low`。若字段不支持，
必须以明确 transport/protocol 错误失败，不自动换模型。
