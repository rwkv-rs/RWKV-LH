# Round11 预注册：Persistent Unresolved-Obligation Lifecycle

预注册日期：2026-08-12（任何 Round11 RWKV 请求之前）

## 固定依据

Round1--Round10 固定 90 题的 900 个题轮审计中，359 个最早终止于完整 `satisfies_criteria` 覆盖硬门；
Round10 单轮仍有 30/90。当前 `LongHorizonModel.plan()` 先接受结构合法基础计划，随后同步调用第二个
`goal_obligation_planning`，并对合并图执行 `require_coverage=True`。Round7 引入该补全请求后，覆盖硬门从
Round6 的 49 降到 24，但模型请求从 657 增到 1148；Round8--Round10 又分别有 27、32、30 个覆盖硬门终止。

- Round10 results SHA-256：`5863d7644b921f4f95e6b53fd4a66d2559c01469f95e7053003a227fc59715a6`
- 十轮反向因果 JSON SHA-256：`9be6e346e530da1f5f6afaf527748c01a6b45060f66d5f3a66ea4f3a0615eec6`
- Round10 canonical G1i JSON SHA-256：`cb89dc5402017c165c48f6846450f84a8033fcdb2fdee58502fa050a7bb86884`
- Codex reference SHA-256：`947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`

## 唯一结构变量

实施 `persistent_unresolved_obligation_lifecycle.v1`：

1. 结构合法的 RWKV 基础计划立即持久化并进入执行，不因 required criterion 未全部出现在
   `satisfies_criteria` 而同步拒绝，也不在初始 planning 内调用 supplemental planner。
2. 未被 VERIFIED CriterionEvidence 覆盖的 required criterion 以原始 ID、原始描述和 immutable Goal digest
   保存为 `GoalObligationState`；Controller 不生成任务、producer、expected、proof 或 criterion 文本。
3. 全部 active required tasks 完成但 Goal evidence 仍缺失时，从权威 RunState 确定性生成 StateCapsule：
   unresolved criteria 原文、plan generation、active task 状态/依赖/output refs、artifact hash、已有 evidence、
   workspace manifest。capsule 及 SHA-256 完整写入事件。
4. RWKV 在该 capsule 上提出一个增量 `obligation_replan`，只追加结构化任务；可以依赖 active completed tasks，
   不得修改已完成历史。每次追加仍由后续独立 RWKV action/proof 请求决定具体动作与证明。
5. Controller 只验证 schema、ID、DAG、existing dependency 已完成、criterion ID 属于 immutable Goal，且新增图至少
   显式关联一个当前 unresolved criterion。它不得自动选择、复制或补全 criterion，也不得根据 hidden acceptance
   选择任务。
6. goal-level recovery budget 固定为 3 次。每次请求、correction、raw/parsed/normalized payload、capsule、状态变化、
   新任务映射与 remaining budget 全量审计；耗尽后 fail-closed 为 `unresolved_goal_obligations`。

这一个变量同时替换“同步完整覆盖拒绝”和其专用 supplemental planner；两者是同一旧生命周期的 gate 与 recovery，
不是两个独立能力改动。

## 明确不改

- Goal parse 的 1--5 criterion 上限不改；1--16 条扩展留给独立轮次。
- 初始 task decomposition prompt/schema、action catalog、G1i parser/normalizer、Phase A/B assertion、proof operators、
  verifier、sampling、failure recovery、final answer、E2E 数据、并发与 transition 上限不改。
- 不根据 hidden acceptance、Codex reference、相似度或历史正确答案生成/筛选任务。
- 不修改 RWKV action、claim、proof 参数或最终输出；final 仍必须 byte-exact raw RWKV。

## 固定数据与运行

- 数据：RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；Codex reference 仅 post-run 使用。
- 模型：`rwkv7-g1i-13.3b-20260805-ctx16384`，`vllm-rwkv-rapid`。
- 并发：8；max transitions：200；sampling 继承 Round10。
- 运行前/后：完整产品测试、LH-Control-30；正式运行必须 90/90 case、90/90 causal artifacts。

## 预注册诊断与晋级门槛

结构变量成立需要：

- Round10 的 `plan_missing_direct_criterion_claims=30` 降为 0；结构合法基础计划均出现 `plan_saved`。
- 新增 `goal_obligation_state_created/updated`、`goal_obligation_capsule_prepared`、
  `goal_obligation_replan_started/saved/blocked` 审计，state timeline 可恢复一致。
- 至少一题真实触发“先执行基础计划，再由 RWKV追加 obligation task”；若只是换成另一个执行前补全请求则实验失败。
- 初始 planning 的 `goal_obligation_planning` 请求为 0；新增请求只允许发生在 active required tasks 已完成之后。
- Offline 全过、Control 30/30、因果链 90/90、raw final byte equality 全过。

正式主指标比较仍使用 External、Strict、Completed、FP/FN、请求数与预登记 byte-5gram similarity。Round11 不得上传，
除非同时满足：FP=0、External≥15、Strict>7、Completed>0，并且完整门禁通过；否则当前可回档最佳仍为用户批准的
Round2 checkpoint `b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
