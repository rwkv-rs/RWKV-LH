# R14 zero-State 无效 case 重试预登记

日期：2026-09-02。R14 只重跑 R13 无效的 L1、L2、L5；代码、固定数据、Prompt、G1J 权重、三路
`zero` profile、`concurrency=1`、`max_transitions=120`、评价口径和阈值均与 R13 相同。

启动 gate：本地只能有一个 runner；带 ServerAlive 的 SSH 隧道必须同时监听 29713/29721；远端 G1J
13.3B 与 2.9B health 必须通过；Strong completion readiness 必须通过。GoalPlan/StageReview 通用缓存可命中
R13 已成功验证的完全相同请求，新请求仍调用 Strong Model。

HTTP 429/500、超时、隧道中断和 `*_unavailable` 单独归类基础设施；失败发生后的 trace 禁止进入 State
Tune 数据。结果写入独立目录 `run_g1j_zero_state_v7_compatibility_r14_invalid_retry`，不覆盖 R13。
