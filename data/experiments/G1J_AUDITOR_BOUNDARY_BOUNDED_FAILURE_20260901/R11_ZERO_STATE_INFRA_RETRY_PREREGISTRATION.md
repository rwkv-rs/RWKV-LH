# R11 zero-State 基础设施重试预登记

日期：2026-09-02。R11 仅重跑 R10 五个基础设施中断 case，数据、代码、G1J 权重、三路 zero profile、
`concurrency=1`、`max_transitions=120`、Prompt 和验收口径全部不变。启动 gate：Strong Model readiness
必须满足 `available=true`、`catalog_available=true`、`model_present=true`、
`completion_available=true`；本地只能有一个 benchmark runner。

HTTP 429/500、服务超时和 `*_unavailable` 仍归类为基础设施，禁止转成 RWKV 缺陷样本。R11 使用新目录，
不覆盖 R10。
