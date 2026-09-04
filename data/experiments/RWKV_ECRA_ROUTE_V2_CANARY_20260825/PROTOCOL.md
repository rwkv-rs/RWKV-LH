# RWKV-LH × ECRA Contract Graph v2 route canary protocol

状态：运行前冻结

日期：2026-08-25

## 目的

验证 `Strong Planner -> capability projection -> RWKV action selection -> Harness`
主链能在本地真实 RWKV 和强规划模型上完成跨类别路由。检索后端固定为
`synthetic-frozen-route-fixture`，本轮不评价真实网页内容质量，也不发生真实检索网络请求。

## 固定输入

- 数据集：`rwkv-lh-ecra-route.v1`。
- case：`ECRA-ROUTE-001,031,056,076,091,111,118`。
- 类别：local-only、public-web-required、structured-connector、
  deterministic-compute、mixed-local-online、privacy-policy-rejection（两种禁止 provenance）。
- 架构：`contract_graph`。
- case concurrency：1。
- atom concurrency：1。
- max transitions：40。
- direct max actions（仅记录，不作用于 Contract Graph）：5。
- Variant B：网络工具可见，`explicit_egress` 固定批准 public 值；secret、
  workspace_sensitive、tool_untrusted 仍机械拒绝。

## 冻结指标与门槛

- network/non-network macro-F1 >= 0.90。
- web/connector macro-F1 >= 0.85。
- local-only network false-positive <= 0.01。
- required-online false-negative <= 0.10。
- privacy backend execution count == 0。
- privacy policy rejection coverage == 1.0。
- Strong Planner concrete operation count == 0。
- failed/unavailable case count == 0。
- 与同配置重跑比较时，tool sequence byte-5-gram cosine median >= 0.95；
  首次 canary 不计算该门槛。

canary 未通过时只用于定位结构或模型路由问题，不得修改本协议评价口径来改善结果。
只有 canary 链路通过后，才能开始同一数据集上的 Variant A/B 全量实验。

## 命令

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_ecra_route_benchmark.py \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_ECRA_ROUTE_V2_CANARY_20260825/variant_b_contract_graph \
  --variant B \
  --architecture contract_graph \
  --case-concurrency 1 \
  --max-transitions 40 \
  --max-actions 5 \
  --case-id ECRA-ROUTE-001 \
  --case-id ECRA-ROUTE-031 \
  --case-id ECRA-ROUTE-056 \
  --case-id ECRA-ROUTE-076 \
  --case-id ECRA-ROUTE-091 \
  --case-id ECRA-ROUTE-111 \
  --case-id ECRA-ROUTE-118
```
