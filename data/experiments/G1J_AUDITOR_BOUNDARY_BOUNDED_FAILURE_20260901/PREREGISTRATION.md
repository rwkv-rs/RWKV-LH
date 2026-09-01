# RWKV Auditor 单边界有界失败预登记

日期：2026-09-01。基线 commit：`968f9e3f4b40f91c6f1570a2f72a455facf8ca3e`。

## 根因与固定范围

R6 `AGENT-LADDER-L1-FIX01` 的同一个 pending Goal Audit boundary 在
`LongHorizonModel.audit_goal_boundary()` 内部三次协议重试耗尽后抛出 `ModelProtocolError`；
`StatefulGoalLoopController` 将它计作一次普通协议错误并立即重新进入同一 pending boundary，最终形成
3 次内部生成 × 12 次外层重入。Goal 模式只有经过 RWKV Auditor 接受的 `final_answer`
可以完成任务，Auditor 自身的协议失败既不能完成步骤，也不能成为 Goal 终止条件。修复只改变这个调度错误：

1. 仍保留 Auditor 内部最多三次生成及精确 prior rejection feedback；
2. 一轮耗尽后登记一次 `protocol_rejection_recorded`，并将当前 durable audit boundary
   机械 resolve 为 `protocol_invalid`；该记录必须明确 `step_completed=false`、
   `kernel_validated=false`，不得生成审核结论或证据；
3. action boundary 失败后继续同一未完成 plan step，允许 Executor 采取下一个有用动作；不得重新执行
   Selector 已选动作，不得重新审核同一 boundary；
4. pre-final boundary 失败时拒绝本次 `final_answer` 候选并继续 Goal；只有之后通过
   `ready_for_final` Audit 的新候选才可产生 `run_completed`；
5. 不改变六字段 schema、Evidence Kernel、Prompt Template、角色、模型、State profile 或 State Tuning；
6. 非 Auditor 的 Selector/Executor 协议拒绝仍使用现有全局预算。

## 固定验证

- 一个 action 后连续三个无效 Auditor 输出：只打开一个 audit boundary，只消费三次 Auditor 生成，
  只登记一次外层 protocol rejection，将该 boundary 机械 resolve 为 `protocol_invalid`，步骤保持未完成；
  同一次 Goal run 必须继续产生下一动作，不得重入失败 boundary。
- 下一动作的合法审核可以引用该步骤累计的 Harness 证据并完成步骤；Stage Checker 必须可达。
- 一个 `final_answer` 候选后连续三个无效 Auditor 输出：候选被记录为拒绝，Goal 不完成；新的
  `final_answer` 候选只有经过合法 `ready_for_final` 审核后才完成任务。
- 现有 Auditor role-pure、Evidence Kernel、Planner semantic repair、Stage Checker 回归全部通过。
- 全量测试、`git diff --check`、`compileall` 通过。

## 真实验证 gate

如 Strong Planner relay readiness 可用，复用 Agent Ladder 固定五例、G1J 2.9B/13.3B、zero profile、
V7 compatibility、`concurrency=1`。本修复 gate 不要求模型格式变好，只要求任何单个 Auditor boundary
不再重复内部重试波，且 Auditor 格式失败不会错误终止 Goal。格式和证据判断残差原样记录，作为后续
Auditor 专属 State Tune 候选；HTTP 429 与工程重试事件不得进入训练数据。
