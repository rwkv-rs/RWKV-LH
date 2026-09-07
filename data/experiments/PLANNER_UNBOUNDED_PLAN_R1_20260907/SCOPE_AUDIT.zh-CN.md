# Planner 计划数量限制：剩余路径只读审计

日期：2026-09-07。来源：owner 授权取消 Planner 步数要求后的独立代码审计。本文不包含模型运行、训练或能力评分。审计期间主代理正在修改当前计划协议与测试，本文源码 SHA 记录读取时的快照，不代替主代理最终冻结清单。

## 结论

在排除主代理负责的 `rwkv_lh/supervisor_openai.py` 与 `rwkv_lh/goal_loop_protocol.py` 后，未发现当前 `stateful_goal` 的计划接收、计划持久化调用、阶段检查输入构造或界面重建另有步骤数、阶段数、累计未完成步骤数上限，亦未发现把计划静默截成前五步或前 32 步的路径。因此，在本审计范围内没有必须追加的生产修改。

仓库中确有旧静态 `SupervisorPlan.steps` 的 32 项限制、旧并行 atom 流程的阶段预算，以及当前 Controller 的执行预算和事实投影预算。下面分别说明它们的调用边界；不能把这些命中直接认定为当前 Planner 计划数量拦截，也不能依据本次授权删除执行安全预算。

## 范围与方法

- 范围仅为 `rwkv_lh/`、`scripts/`、`tests/`、`docs/` 与根 README；按 `*.py`、`*.md`、`*.js` 搜索，随后读取相关调用上下文。
- 检索 `GoalPlanPatch`、`GoalPlanRequest`、`RollingGoalPlan`、`add_steps` / `replace_steps`、`add_stages` / `replace_stages`、`frontier`、`horizon`、`maxItems`、数量/阶段/步数关键词、`[:5]`、`[:32]`、`slice` 与 `max/min/limit/cap` 等组合。
- 两个主代理负责的生产模块不在本次独立审查范围；涉及这些模块的行为必须由本轮主代理整改与回归记录证明。
- 没有读取 Holdout、confirmation、`data/acceptance/` 或任何私有验收程序；没有打开 SQLite；没有远端操作、Git 命令、模型调用或测试执行；没有修改生产、测试、配置或旧实验。

## 当前路径的完整性

| 路径与读取时行号 | 实际行为 | 审计判断 |
| --- | --- | --- |
| `rwkv_lh/product_runtime.py:66` | 产品入口只接受 `stateful_goal`。 | 当前产品架构入口明确。 |
| `scripts/run_rwkv_e2e_benchmark.py:1937`、`:2019`、`:2026` | `stateful_goal` 强制 `goal_stages`，创建 `OpenAIGoalSupervisorClient`，策略对象以 static 模式配置。 | 不把旧静态计划 / 并行 atom 协议当作本次当前计划接收入口。 |
| `rwkv_lh/stateful_goal_loop.py:1463`–`:1470` | 返回补丁经 `GoalPlanPatch.from_dict(returned.to_dict())` 完整复建，再应用到隔离复制的候选 plan。 | 本层没有新增数量判断或数组切片；解析和 plan 应用内部由主代理审计。 |
| 同文件 `:1591`–`:1602` | 依赖闭包用待处理列表遍历，逐项检查所有 `add_steps` 与 `replace_steps`。 | 本层未截断依赖数或变更步骤数；目标契约检查仍覆盖完整补丁。 |
| 同文件 `:1939`–`:1948` | 遍历全部已完成阶段，寻找尚未检查的阶段边界。 | 没有只接受前若干阶段的数量条件。 |
| 同文件 `:1976`–`:1999` | `plan.stage_steps(stage)` 的全部步骤进入 `GoalStageReviewRequest.stage_steps`，同时携带各步骤 revision 与 accepted evidence refs。 | 本层阶段检查输入不截断步骤。请求类型内部由主代理审计。 |
| 同文件 `:2428`–`:2441`、`:2462` | 没有 frontier 且仍有未覆盖目标时继续请求补丁；有 frontier 时每次选 `plan.frontier[0]` 执行。 | 取首个可执行步骤是调度动作，不是删掉其余步骤或在第一步宣布完成。 |
| `rwkv_lh/goal_web_assets/app.js:237`–`:247` | 从全部已提交补丁重建 Map，完整处理 discard、replace、add 与嵌套 stage.steps。 | 未发现界面只展示前五个计划步骤的硬截断。 |

## 命中的限制及不应扩大的修改范围

1. **旧静态计划的 32 项限制**：`rwkv_lh/supervisor.py:195`–`:216` 的 `SupervisorPlan.create()` 对字符串列表 `steps` 设置 `max_items=32`。这是另一种静态 `SupervisorPlan` 类型，不是当前 `GoalPlanPatch`。上述当前入口和 controller 调用链没有经过该构造函数。本次为当前 Planner 取消步数要求不要求修改此处；若以后把旧静态入口重新纳入产品，则必须重新审查该入口，不能宣称整个仓库所有历史 API 已无限制。

2. **旧并行 atom 阶段预算**：`rwkv_lh/supervisor.py:1376` 默认 `max_parallel_stages=16`，`:1424`–`:1428` 限定配置为 1–64；`rwkv_lh/controller.py:3340` 在并行执行阶段数量耗尽时记 `parallel_stage_budget_exhausted`。这控制旧并行执行流程，不参与当前 `stateful_goal` 的计划补丁接收。`max_parallel_atoms` 同样是并发执行边界。

3. **当前 Controller 执行与失败预算**：`rwkv_lh/stateful_goal_loop.py:2187` 的 `while transitions < self.max_transitions`、`:1418`–`:1432` 的语义修复尝试数，以及重复失败 / 无进展 / Final 拒绝预算，控制一次运行的开销、重试与终止。这些边界可能使大计划在一个运行预算内无法完成，但不会按计划包含多少步骤拒绝或裁剪补丁。本次应保留，并在后续冻结运行中明确执行预算。

4. **上下文投影预算**：同文件 `:84`–`:114` 的 `_recent_action_facts` 默认只投影最近 12 个动作；StageChecker 在 `:2014` 指定 8 个动作。`:1406`–`:1407` 与 `:2005`–`:2006` 的 workspace manifest 有 256 entries / 1800 tokens 预算。较大阶段仍传递全部步骤与 evidence refs，但详细动作事实可能只覆盖最近一部分。此项是大阶段的上下文充分性风险，不是 Planner 计划数量限制；本轮只取消计划数限制，不据此调整其他角色。

5. **其他切片命中**：`stateful_goal_loop.py` 中 `candidates[:32]` 与 observed evidence 的 `[:32]`、`observation_funnel.py` 的字典投影、`controller.py` 的证据引用切片，以及 `store.py:181` 的 `failures[:5]` 均非当前 Planner 的 steps/stages 数组。没有发现以这些切片裁剪当前计划的调用证据。

## 回归与文档核查边界

主代理新增的 `tests/test_goal_planner_plan_size.py` 在本次读取时覆盖 6 / 19 / 64 步的序列化、累计增长、批量替换与丢弃、完整阶段检查输入、多依赖、旧数量边界后继续执行，以及保留依赖和根路径拒绝。`tests/test_supervisor_openai.py` 已将五步正向提示词断言改成禁止旧五步文案。本审计只读取测试，不声明这些测试已经通过；实际红绿与全回归以主代理原始日志为准。

README、`docs/HANDOFF.zh-CN.md`、`docs/G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md` 在本次读取时已说明数量由任务决定，保留字段、依赖、根路径和证据约束。未发现另有当前文档要求最多五步。旧连接诊断按当时合同记录 19 步被拒的事实应保持不变，不用新合同回写或重评分旧输出。

## 读取时源码 SHA-256

```text
881da77a22e040e8126d534c97686b1a4a3cc5833e02304b2908e6d08031b18d  rwkv_lh/supervisor.py
5913ed83d1696058a3105708e0a94b58d8935a20418177701e1a433ff7f0acf0  rwkv_lh/controller.py
dfd87e18d3fe57454812a492ee8070f3cafeaeee71f2c661e689d907982d9245  rwkv_lh/stateful_goal_loop.py
5d995a19f834c03b38d73649796c6009cd8aad63f2e33e246b6c985e1df77095  rwkv_lh/model.py
c0d2219607b41901dd33adde18a9ce1cbae8e17164379eefec1420c8a456e6b3  rwkv_lh/product_runtime.py
44080b74103872883a154bdc36c5374c684d3395778887494a4639988d806047  rwkv_lh/goal_web_assets/app.js
8906ecd16c708901403a93c7ec1014c7cdf6f2c54afcccc1bc6fd4f20a056d41  scripts/run_rwkv_e2e_benchmark.py
```

## 连接诊断目录收尾确认

本审计没有改动 `data/experiments/LOCAL_13B_SUPERVISOR_CONNECTION_R1_20260907/`。本子任务在该目录没有待修改或待生成文件；以下已提交给主代理的独立报告再次只读核对 SHA 与此前一致，可纳入主代理整体冻结：

```text
60e730172790e63ef529651df499c10aa24bf21885c5f04467cd5204824f84f0  READONLY_CONNECTION_AUDIT.zh-CN.md
cf6a5eb894a32c30f6eb96d8f003b0dbacfd09a78def650e139ff1aaedbea129  READONLY_CONNECTION_AUDIT_SHA256SUMS
a52c5608dd9872047d2a9edc7d8f06e16c2fb3de587e80e8e476bc58e9249f27  STRUCTURED_OUTPUT_IMPORT_FAILURE_FOLLOWUP.zh-CN.md
0992f346ff4a093202ea69c28f3c933a5717dc97237c0d9b5bf89ddd4d2038b8  EXECUTOR_VS_PLANNER_GENERATION_BOUNDARY.zh-CN.md
```
