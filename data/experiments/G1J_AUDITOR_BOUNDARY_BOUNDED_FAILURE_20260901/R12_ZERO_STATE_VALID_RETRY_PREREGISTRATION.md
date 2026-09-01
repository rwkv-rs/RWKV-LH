# R12 zero-State 固定五例重试预登记

日期：2026-09-02。目标是在 Strong Model relay 恢复后获得可评价的 zero-State G1J 基线。R12 只重跑
R10/R11 的固定五例，不改变代码、数据、Prompt、权重、评价口径或阈值。

固定条件：

- Strong Model：`gpt-5.4-mini`，只承担 Planner 与 Stage Checker；
- Selector：G1J 2.9B，`profile_id=zero`；
- Executor：G1J 13.3B，`profile_id=zero`；
- Auditor：G1J 13.3B 独立 role/session，`profile_id=zero`；
- `concurrency=1`、`max_transitions=120`；
- 固定 Agent Capability Ladder L1-L5 五例；
- GPU 0/3，禁止使用 GPU 1/2；
- 启动前只允许一个 benchmark runner，三路 RWKV health 必须通过；
- Strong Model readiness 必须满足 catalog、model 和实际 completion 全部可用。

HTTP 429/500、超时或 `*_unavailable` 仍归类为基础设施无效终点；未发生 RWKV 调用的 case 不计入
RWKV 能力分数，也不得进入 State Tune 数据。发生模型调用后，所有失败按最早可证实 trace 层归因，禁止
为改善结果修改指标、Prompt 或用例。结果写入独立目录
`run_g1j_zero_state_v7_compatibility_r12`。
