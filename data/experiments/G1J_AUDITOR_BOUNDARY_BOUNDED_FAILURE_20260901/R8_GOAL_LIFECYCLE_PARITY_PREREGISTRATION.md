# R8 Goal 生命周期一致性预登记

> 执行后状态：工程无效中止。运行中发现未完成 frontier 的 `eligible_operations=None` 错误放行
> `final_answer`；详见 `R8_INVALID_PREMATURE_FINAL_MENU.md`。R8 不进入能力统计或训练数据。

日期：2026-09-01。输入固定为 R7 同一 Agent Ladder 五例、同一 G1J 权重、zero profile、
`concurrency=1`、`max_transitions=120` 和既有验收口径。

## 两个已由 R7 trace 分离的工程改动

1. E2E runner 在 `stateful_goal=true` 且 Controller 返回 `RunStatus.RUNNING` 时，按照
`run_yielded.continuation=controller_resume` 继续调用同一 durable run。每次 Controller 返回的
`transitions` 从同一个 `max_transitions` 总观测预算扣除；零 transition checkpoint 也至少扣一，禁止
测试端无限循环。`*_unavailable` 和 `*_failure` 基础设施边界不在 benchmark 内密集重试，仍按外部无效
轮次记录。

2. action Audit 的 `verdict=repair` 按 Auditor prompt 的既有定义解释为“当前步骤证据不足”：步骤保持
未完成，审核 decision 已进入 Executor State，Controller 直接继续同一步，不调用 Planner。只有
Strong Stage Checker 的 `verdict=repair` 才触发 Planner 修改计划。该改动不改变 GoalPlanPatch、
RWKV Auditor schema、Evidence Kernel、Prompt Template、角色、模型或 State profile。

## 固定 gate

- 单元回归构造第一次返回 `RUNNING + run_yielded + termination_permitted=false`、第二次返回经过审核的
  `COMPLETED`；runner helper 必须调用一次 resume 并保留第二次输出。
- 总 transitions 不得超过固定预算；零 transition 也必须有界。
- unavailable/failure checkpoint 不在 benchmark 内自动重试。
- action Audit repair 后 Planner request count 不增加，Selector/Executor 必须继续同一步；Stage Checker
  repair 仍会触发一次 Planner patch，并保留一次本地语义修正能力。
- 全量测试和静态检查通过。
- R8 使用新输出目录，不覆盖 R7；分别报告 Planner、Selector、Executor、Auditor、Stage Checker、
  Evidence Kernel、基础设施和最终验收，不以 0/5 总分替代 trace 分类。
