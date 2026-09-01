# R17 zero-State L2 relay 冷却后重跑预登记

日期：2026-09-02。全量回归 786 passed 后，R17 单独重跑 L2。固定数据、Prompt、G1J 权重、三路
`zero` profile、`concurrency=1`、`max_transitions=120`、指标与阈值不变。初始 Plan/StageReview 仅允许命中
durable-validated cache；新 repair 请求仍由 Strong Model 生成并经 Controller 完整验证后写缓存。

任何 HTTP 429/500 或本地/远端服务中断仍归类基础设施。结果写入
`run_g1j_zero_state_v7_compatibility_r17_l2_cooldown`。
