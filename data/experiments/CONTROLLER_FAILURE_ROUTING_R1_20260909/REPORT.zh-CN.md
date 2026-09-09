# Controller 链路分析与误路由修复

日期：2026-09-09。基线提交：`ba087cd8f0c1122351ae80e69303d7836463f595`。本轮 ID：`CONTROLLER_FAILURE_ROUTING_R1_20260909`。

## Agent 级与角色级结果

本轮没有新增完整 RWKV Agent 评测。最近完整 R7 仍为 A/B 各 Strict **0/12**、completed **0/12**、mutation **0**，均在第一条成功目录观察之后终止于 `strong_planner_unavailable` / `fixed_plan_exhausted`。不能把本轮 mock 回归的完成结果登记为 Agent 改善，也不能把旧 R7 重评分成新代码的结果。

角色级没有新增正式合格数据或训练候选，实际 optimizer steps 为 **0**。前轮逐角色训练授权继续有效；owner 本轮追加优先级是先分析连接并形成通用设计，保留五角色，不按任务穷举兼容。2.9B 源权重已只读核验，部署与训练后端验证仍未完成，见相邻 `SELECTOR_STAGE_R1_20260909/MODEL_REDEPLOY_STATUS.json`。

## 结论与计数边界

本轮确认 **7 类连接问题**，其中第 1 类的 **3 条误转 Planner 分支已修复**，其余 6 类已定位但尚未完成统一整改。这不是全仓库剩余工程问题的总数。另发现旧 GoalPlanPatch 重放入口尚在，单独列为清理缺口。

没有依据据此替换五角色。问题集中在角色输入、事实投影、反馈归属和事务边界。只删除错误的重规划入口，可以解除一个过早终止点，但不能称为整个链路已经闭环。

### LINK-01 [P1] 执行/协议失败被升级为计划修复：本轮已修三条分支

基线 `_pending_controller_repair_feedback` 会把两次工具失败、两次 Executor provenance 拒绝、一次无效 Step Auditor 输出包装成 Planner 修复请求，并在正常 Executor 重试之前调用 Planner。这些事件没有证明原步骤或依赖关系失效。若 Planner 不可用，任务直接中断；若 Planner 返回补丁，原本可继续的步骤被强制换版本。

改动删除该投影、两个次数阈值、Controller 调用分支、GoalPlanRequest 专用字段、对应提示词与缓存处理。没有保留兼容 stub。工具失败继续当前步骤；参数错误保留既有一次同工具重试及之后的正常选择机制；持久失败仍在实际五次相同失败预算处阻塞。Step Auditor 输出无效不再调用 Planner，但其后续错误归属仍存在 LINK-04，不将其一并称为已解决。

先改期望再改实现：`red.log` 四个用例失败；同组 `green.log` 四个通过。增加短暂工具失败后恢复的连续/中断两种验证。真实 Harness 文件读取和修改保持同一计划版本，Planner 只有初始一次调用。持续失败真实结束为 `identical_failure_budget_exhausted`，不会伪装完成。

### LINK-02 [P1] Step Auditor → Selector 的语义反馈缺失

`stateful_goal_loop._latest_step_repair_gaps` 可以读取当前 step revision 的已接受缺口，但仅传入 Executor 的 `build_execution_state`。`_selector_current_progress` 与 `selector_intent_v4.PROGRESS_FIELDS` 没有审计反馈字段。Selector 看得到动作次数、最后一次工具结果、root 覆盖和目标列表，看不到当前步骤为什么仍未完成。

探针在现有目录观察 REPAIR 回归中，记录到 `available_accepted_gaps=[phase_evidence_unproved:observe]`，实际下一次 Selector progress 未包含该代码。测试依靠预排的 `read_file` 选择继续，并没有证明 Selector 收到了可据以改变选择的信息。Executor 也只有 gap 代码，缺少对应条件原文的统一交接，不能普遍依靠代码或摘要猜测语义。

影响：模型可能重复选择机械上已经成功、语义上却不足的操作；在相同不完整输入上训练相互不同的选择目标，会把输入缺失误记为模型能力不足。应统一投影有来源和条件原文的反馈，再让各角色 builder 获取其职责需要的信息。

### LINK-03 [P1] Final Auditor → Finalizer 的拒绝反馈缺失

`model.finalize_goal_answer` 每次用目标、已完成步骤和事实重新 bootstrap。`finalizer_answer.build_prompt_source` 没有被拒绝候选或最终审计反馈。Controller 虽然记录 `goal_final_rejected`，但下一次 Finalizer 输入不会读取它。

探针实际捕获两次 Finalizer 的完整 prompt，SHA 完全相同；两次输出不同来自测试队列。当前模型温度为 0.1，不保证每次逐 token 相同，但无反馈重答没有获得针对拒绝原因修复的条件。应传递绑定候选版本的拒绝反馈，继续使用独立 Finalizer State。

### LINK-04 [P1] Auditor 自身格式错误被交给上游重做

`_resolve_protocol_invalid_audit_boundary` 将审计边界标记 resolved 并设置 `authorizes_new_action=true`。对 pre-final 还会把有效 Finalizer 候选登记为被拒绝，随后重新 Finalize。审计模型的格式错误没有形成“重试同一审计”的边界。

探针中的第一次 `read_file` 已成功，仅因 Step Auditor 输出 `{}`，又执行了第二次相同读取才得到有效审计。这里没有计划修复，但仍是错误归属。对副作用动作，同样的控制流允许再次执行；没有证据可以授权重复动作。应保持已提交动作与待审计边界，按既有预算重试责任角色，预算耗尽阻塞。不能靠重新执行工作来获得另一个审计机会。

### LINK-05 [P1] 最终执行证据缺口只能触发重答

Final Auditor 的合法 gap catalog 含 `goal_requirement_unproved:*`、`completed_step_criterion_unproved:*`、`evidence_unusable:*`，不只有回答措辞缺口。但 Controller 对所有非 ready 的最终审计都记录拒绝并 `continue`；plan 保持 complete，下一次仍调用 Finalizer。

探针从真实输入的 catalog 选择 `goal_requirement_unproved:*` 作为 scripted 审计输出，没有发明协议输入。运行仍只有一个计划补丁、一个既有动作，随后进入相同输入的 Finalizer。没有进入补充执行证据的工作路径。实际业务目标未满足时，仅重写回答无法补齐事实。

目标契约应显式区分回答修复与目标/证据修复，后者经既有 Planner 补丁增加必要工作；按模型选择的合法条件类型路由，不能在 Controller 猜测自由文本关键词。

### LINK-06 [P1] Stage Checker 的完整步骤与实际事实不一致

`_issue_strong_stage_review` 传递全部步骤和 accepted refs，却调用 `_recent_action_facts(max_actions=8)`，只提供最后八个动作的投影。`GoalStageReviewRequest` 还有最多十二条事实的独立校验。

探针执行现有 large-stage 回归：**19 个已完成步骤、19 个证据引用、实际仅 8 个动作事实**。原测试明确断言八条，因而全绿反而固定了这个盲区。Stage Checker 审查全部步骤时无法看到前十一项的事实，这会将传输缺失转成疑似阶段/计划缺口。应去除责任边界内事实的数量裁剪，并让实际上下文预算显式处理超限；不能把编号完整当作证据内容完整。

同一路径的 artifact/revision 引用解析还需要统一核对：当前 recent facts 的 `action_ids` 筛选直接比较 action id。该子路径本轮未完成独立动态复现，不与 19→8 的已证实数量问题混报。

### LINK-07 [P1] 不完整目标投影和内容推断被当作工具权限

两个变形探针证明同一类契约错误：

- 相同损坏 JSON 内容，`payload.json` 被识别为 candidate 并允许 `read_json`；只改名为 `payload.data` 就禁止该观察。真实解析可形成负面诊断证据，但选择入口按后缀改变可达性。
- 一个目录中实际存在可读文本，只因目标位于 256 条枚举投影之外，`_goal_step_operation_contract` 把 `read_file` 从该目录步骤的可选操作中移除。文件存在且类型兼容；摘要不完整造成了错误排除。

这不是再加几个后缀或提高到更大常数就能解决的问题。应以工具真实能力和授权范围为依据，区分确定不兼容与尚未观察；有限候选展示不能成为资源全集。测试应验证改名、重排和加入无关文件的不变量，不按任务逐项适配。

### 额外清理缺口：旧计划 schema 重放入口

`goal_loop_protocol` 仍声明并接收 GoalPlanPatch v1/v2/v3，`operation_contracts.infer_goal_step_phase` 仍为旧计划推断 phase。产品入口只有当前 Controller，不等于内部旧协议已清理完。后续统一契约实施时必须删除这些入口及旧字节码，并验证旧版/未知版本拒绝；本轮没有将这一项标为已清理。

## 统一设计及覆盖范围

设计在 `docs/CONTROLLER_ROLE_LINK_CONTRACT.zh-CN.md`：任务与权限、工具能力、证据、反馈、错误归属和 State 恢复六项契约。明确字段语义、责任和断言，未宣布新 wire schema 已实施。当前五角色不变，模型升级通过适配配置处理。

检查了产品入口、Planner/Stage Checker 请求、Selector 菜单与进度、Executor 参数重试及 provenance、Harness 结果/动作提交、Step/Final 审计、Finalizer、因果边界恢复、角色输入重建及当前关联测试。确认已有选择绑定、独立角色 State、目标范围和完成校验仍在。未声称完整任务分布已实测，未读取保护的 Holdout 或其验收内容。

当前作用域的因果链是：输入或事实丢失 → 角色无法据反馈修正或无法判断完成 → 重复动作/无反馈重答/误判阶段缺口 → 过早终止或无效 trace。StateTune 可以改善收到足够信息时的模型选择，但不能凭空还原从未进入输入的条件。首轮训练仍不以高 Agent 分数或后序角色出现为前提。

## 验证与保留边界

| 验证 | 结果 |
| --- | --- |
| 误路由回归，修改实现前 | 4 failed，61 deselected |
| 同一组回归，修改实现后 | 4 passed，61 deselected |
| Controller / 当前角色协议 / Supervisor 关联测试 | 136 passed |
| 完整 `tests/` | **1046 passed，0 skipped，185.31 秒** |
| 实际 RWKV 完整 Agent 新评测 | 未运行 |
| 正式角色数据、训练步骤 | 未新增，0 steps |

完整回归含所需 Torch / State 注入和浏览器检查，无跳过。只在 WSL 执行项目测试，远端探测未使用 Git。`WIRING_PROBE.json` 的模型输出是 scripted fixtures，输入由生产 builder 构造，Harness 有真实本地 I/O；这些探针不是训练样本或 Agent 能力验收。

临时脚本按规范在 `temp/`，路径和 SHA 记录于 `VALIDATION.json`。验证入口：`temp/audit_controller_link_contracts_20260909.py`；运行本轮对应 `tests/test_stateful_goal_loop.py` 中同名用例可复核控制路径。最终记录 SHA 见 `MANIFEST.sha256`，报告自身见 `REPORT.sha256`。

本轮完成的是链路分析、可复核的通用设计和三条误转 Planner 的局部控制流修复。**角色反馈、审计重试、最终证据修复、Stage 事实完整性和通用兼容尚未整体解决，不能标记完整链路整改完成。** 下一轮按统一契约先建立跨模块失败断言，再共同修复 builder、执行与 trace 重建；不继续叠加题型特判。
