# R7 Goal 生命周期诊断

日期：2026-09-01。数据：Agent Ladder 固定五例。Executor/Auditor/Selector profile 均为
`zero`，`concurrency=1`，`max_transitions=120`。

R7 五例均进入真实模型链路，Strong Planner 没有 HTTP 429。Auditor boundary 没有出现旧 R6 的
3×12 重试放大；所有已打开 action Audit boundary 均有对应 resolution。L5 还产生了一次
`goal_stage_review_committed`，证明 Strong Stage Checker 已可达。

五例仍被 runner 判为 FAIL，直接对象不是 final answer，而是 `run_state.status=running`。每例末记录均为
`run_yielded`，字段明确为 `termination_permitted=false`、`continuation=controller_resume`、
`reason=strong_planner_semantic_invalid`。正式产品的 `rwkv_lh/web_worker.py` 会在 Goal 状态仍为
`running` 时继续调用 Controller；`scripts/run_rwkv_e2e_benchmark.py::run_case()` 只调用一次并立即验收，
错误地把可续跑 checkpoint 当成本轮 Goal 结果。

Planner 修订也存在真实质量残差。L1 的两次 rejected patch 都把已有未完成步骤
`fix-pricing-and-docs`、`verify-project` 再放入 `add_stages`；L2 第二次重用了已有 `run_verifier`；
L5 第二次尝试 discard `s2_implement_site` 并新增依赖已 discard 步骤的 `s2_implement_site_fix`。
这些错误由本地 validator 正确拒绝，不能放宽协议。但它们是 resumable planning checkpoint，不具备
Goal 终止权限。

R7 因 runner 生命周期不匹配，不能用 0/5 评价最终能力。原始 trace 保留不覆盖。
