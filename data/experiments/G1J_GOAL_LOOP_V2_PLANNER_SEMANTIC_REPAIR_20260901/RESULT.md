# GoalPlanPatch 有界语义修复与 R5/R6 trace 审计结果

日期：2026-09-01。分支：`chase/rwkv-goal-loop-v2-cleanup`。

## 结论

本次已修复一个可直接证实的控制面错误：Strong Planner correction 只要触发
`GoalPlanPatch` 本地语义校验错误，就会被误记为服务不可用并立即中断。现在 Controller 会登记
`strong_planner_patch_rejected`，把精确 validator error、当前合法 plan 和可用时的 rejected patch
放在 Planner 输入尾部，只允许同一 Planner 重修一次；第二次仍错才以
`strong_planner_semantic_invalid` 有界 yield。Transport/HTTP 错误仍单独归类为
`strong_planner_unavailable`。

这项修复解决了旧 R4 的一个 Stage Checker 不可达入口，但真实 R6 又暴露出更早的独立阻断：
RWKV Auditor 输出协议不稳定，且 Controller 在一次 Auditor 内部三次重试耗尽后会重新打开同一审核
边界，导致审核循环挤占后续动作。当前不能把 0/5 直接归因于 2.9B Selector，也没有证据支持立刻做
Selector State Tuning。

## 可复核 trace

### 旧 R4：Planner correction 工程错误

`AGENT-LADDER-L1-FIX01`：

- `CE-000003`：初始 `goal_plan_patch_committed`。
- `CE-000020`：`strong_planner_call_failed`，具体对象为 correction `GoalPlanPatch`，错误字段为依赖关系：
  `Goal PlanPatch leaves active steps dependent on discarded or unknown steps:
  ['read-readme-context', 'read-spec-and-implementation']`。
- `CE-000021`：下游仅继承该分类，以 `strong_planner_unavailable` yield；没有独立的新错误。

旧实现把本地 `ValueError` 和 HTTP/Transport 混为一类，也没有把 validator error 回传 Planner。这是
Stage Checker 调用为零的一条直接工程原因。

### R5：基础设施无效轮次

R5 五例均在第一个 `goal_plan` 请求收到 HTTP 429：每例 `model_requests=0`、`actions=0`、
`supervisor_request_count=1`。因此 R5 只能证明 Planner relay 限流，不能评价 Selector、Executor、
Auditor、Stage Checker 或 State。

### R6：一例有效链路、四例基础设施无效

R6 使用 R5 retry manifest。L2--L5 仍在首个 `goal_plan` 请求收到 HTTP 429，继续判为基础设施无效。
L1 进入真实链路：

- `CE-000003`：Strong Planner 初始三阶段计划合法提交。
- 第一个 Selector 选择 `list_directory`；动作成功。该选择低效，但没有破坏状态或协议。
- `CE-000015`：Auditor 第一次输出 `function/params` 外壳，但 `params` 缺少 `verdict` 与 `step_id`，被
  六字段协议拒绝。
- `CE-000020`：Auditor 第二次给出 kernel-valid `repair`，指出只有目录列表、未读取
  `pricing.py`/`verify_project.py`。
- `CE-000023`：Strong Planner correction 合法提交；本次没有触发 semantic repair 分支。
- 第二个 Selector 正确选择 `read_file`，Executor 正确读取 `pricing.py`。
- 此后 Auditor 在 `decision`、`tool_calls`、`function/arguments` 等互不一致的外壳间波动。个别输出还
  试图在缺少 `verify_project.py` 成功读取证据时完成 step，Evidence Kernel 以
  `completed plan step lacks successful observation evidence for
  read_roots=['verify_project.py']` 正确拒绝。
- 一次审核边界内部最多三次生成；耗尽后外层 Controller 没有终结该边界，而是继续重复调用，最终
  `goal_audit_recorded=38`、`goal_audit_rejected=37`、`protocol_rejection_recorded=12`，但只有两个
  Harness actions。
- `CE-000153`：`protocol_rejection_budget_exhausted` yield。没有任何
  `goal_stage_review_committed`，所以 Strong Stage Checker 调用仍为 0。

这里最早的新独立失败是 Auditor 的具体六字段输出不稳定；其后 Controller 重复打开同一 pending
audit boundary 是新的工程放大错误。Stage Checker=0 只是继承“尚无 kernel-valid 完成 stage”的结果。

## 分类

| 层 | 证据 | 当前判断 |
| --- | --- | --- |
| Planner 工程 | R4 `CE-000020/21` | 已实现一次有界语义重修；不再误报 unavailable |
| Selector 模型 | R6 L1 两次选择为 `list_directory`、`read_file` | 首次低效、第二次正确；单例不足以证明 Selector 是当前根因 |
| Executor 模型 | 两个已执行动作均为合法 JSON 且 Harness 成功 | 当前有效样本未暴露参数格式根因 |
| Auditor 模型 | 38 次记录中 37 次被拒，多种错误外壳、缺字段、错误证据完成声明 | 明确的格式稳定性与证据判断缺陷 |
| Auditor 调度工程 | 内部 3 次失败被外层重复 12 轮 | 明确的边界重试放大错误，应先修 |
| Evidence Kernel | 拒绝缺少 `verify_project.py` 读取证据的完成声明 | 行为正确，不应放宽 |
| 基础设施 | R5 5/5、R6 4/5 首次 Planner 请求 HTTP 429 | 无效样本，禁止写入模型缺陷数据集 |
| 最终答案质量 | 所有运行均未产生 final candidate | 不可评价，不是答案措辞问题 |

## State 与 State Tuning 决策

需要区分两种 State：

1. RWKV 推理时的 recurrent runtime state，由原生 State API 创建、追加、回滚，是运行机制；
2. 可加载的 tuned initial State profile，是角色配置，可为 `zero`（不注入训练 State）或独立加载。

本轮 Executor、Selector、Auditor profile 均为 `zero`。未来允许每个角色/环节有自己的可选 profile，
也允许某一环节不加载 tuned State；不能把多个角色强制绑定到一个共享训练 State。

当前不应先做 Selector State Tune。顺序应为：

1. 先让 Auditor boundary 的失败在一次内部重试波后有界停止，禁止同一边界 3×12 放大；
2. 在不放宽六字段 schema 和 Evidence Kernel 的前提下，固定 Auditor Prompt Template 后重跑固定集；
3. 为 G1J 2.9B 生成与当前 V8 frontier 输入匹配的 Head，再评价 Selector 稳定残差；当前运行仍是
   `rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail` compatibility；
4. 只有同一角色在对齐协议后的全数据集上仍出现稳定、可聚类错误，才把“错误 trace -> 修正 trace”
   制作成该角色自己的 State Tuning 数据。

如果后续需要 State Tune，本轮可进入 Auditor 候选池的是“材料完全相同、错误外壳/错误完成声明 ->
严格六字段且证据绑定的正确 decision”；HTTP 429、Planner patch 校验错误和 Controller 重试放大不得
进入模型训练数据。

## 验证与固定资源

- 目标回归：`54 passed`。
- 最终全量回归：`778 passed, 1 warning in 103.38s`；warning 为既有 Python 3.13
  `multiprocessing` fork deprecation warning。
- Agent Ladder visible tasks SHA-256：
  `23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- hidden acceptance SHA-256：
  `f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- R5 `results.json` SHA-256：
  `76b02fb8984615093192d5fc484011142b32cba21c4fc7d77c4602ac83eb0a7d`。
- R6 `results.json` SHA-256：
  `626c7d3024479a856415d7dfddc5fd110c5097b8185c2da3c0a3b38160ff28b5`。
- R6 L1 `causal_ledger.json` SHA-256：
  `617e44a9453839148726b8a3714b26ce9c9f9674ed67ab16f417400fc2a72668`。

本次真实运行没有命中 Planner semantic rejection，因此预登记的真实 gate 尚不能声明通过；该分支已由
返回“含未知依赖的真实 patch”再修正的 Controller 回归覆盖，并且确实到达 Stage Checker。R5/R6
原始记录保留，用于后续在 Planner relay 恢复后按 retry manifest 继续，不覆盖原轮次。
