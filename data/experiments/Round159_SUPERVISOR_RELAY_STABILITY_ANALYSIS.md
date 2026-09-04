# Round159 Supervisor Relay 稳定性分析

日期：2026-08-23

## 固定探测结果

每模型 5 次、无重试、`reasoning_effort=medium`、strict JSON Schema：

| model | raw HTTP | schema/exact | 5xx | p50 ms | p95 ms | total tokens |
|---|---:|---:|---:|---:|---:|---:|
| gpt-5.4 | 5/5 | 5/5 | 0 | 2312.6 | 7020.4 | 37,634 |
| gpt-5.4-2026-03-05 | 0/5 | 0/5 | 5 | 267.9 | 273.5 | 0 |
| gpt-5.5-2026-04-23 | 0/5 | 0/5 | 5 | 271.5 | 282.3 | 0 |
| gpt-5.6-terra | 5/5 | 5/5 | 0 | 2993.9 | 4661.4 | 2,396 |
| gpt-5.6-sol | 5/5 | 5/5 | 0 | 3090.5 | 5718.0 | 2,388 |
| claude-sonnet-4-6 | 5/5 | 0/5 | 0 | 4104.8 | 4185.2 | 0 |

Claude 路由 HTTP 200，但 content 不能解析为 JSON；固定 5.4/5.5 路由全部立即 503。
`gpt-5.4` 在探测时 5/5，但 Round158 时有 65 次 fallback、26 cases 最终 plan unavailable，
说明浮动路由存在明显时间窗口波动。

Round159 只证明小 schema 兼容性。terra/sol 进入 Round160 真实 contract canary；没有直接修改
`.env`。原始记录：`Round159_supervisor_relay_stability_20260823/`。

