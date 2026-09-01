# G1J Goal Loop v2 真实能力与 Trace 审计结果

日期：2026-09-01。实验按照本目录 `PREREGISTRATION.md` 的固定 5 任务、固定顺序、固定参数和固定验收执行。

## 结论

当前项目能够启动真实 Strong Planner、G1J 2.9B Selector、G1J 13.3B Executor/Auditor 和工具 Harness，
但还不能完成最简单的闭环任务。固定 5 例结果为：Agent 完成 `0/5`、外部验收 `0/5`、Strict E2E
`0/5`；能力上限低于 L1。

系统并非完全没有开始工作：Strong Planner 的初始嵌套计划 `5/5` 提交成功，6 次 RWKV 工具动作
`6/6` 通过格式解析并真实执行成功，所有任务至少执行了一次动作。但是没有一例进入文件写入、验证、
最终回答或 Strong Stage Checker，因此当前证据只能证明“会开始”，不能证明“能做好一个简单项目”。

本轮没有载入任何既有或训练后的 State profile。Executor 和 Selector 均使用全零 profile identity；
Executor 只保留任务内自然产生的原生 recurrent State。运行固定使用远端 GPU 0（13.3B）和 GPU 3
（2.9B），没有使用 GPU 1/2。

## 产品入口与受控运行的边界

按当前 `.env.local` 原样执行时，最早失败发生在任何模型调用之前：配置仍指向旧 G1I/V7 与失效的
本地端口，preflight 收到 `ConnectionResetError(104)`。这是 deployment/configuration 问题。

最新产品协议是 Selector V8 frontier-only，但仓库目前没有 G1J V8 匹配 Head。为继续审计其余链路，
本轮受控运行使用 G1J zero-State + 旧 S60/V7 匹配 Head，并在运行名中强制标注
`v7_compatibility_r4`。该运行可以定位链路缺陷，但不能冒充 V8 最新产品 gate 通过。

13.3B 推理服务的 `/v1/capabilities` 已真实证明 native State `create/resume/fork/commit/rollback/`
`export/import` 均可用，协议为 `rwkv-lh.native-state.v1`，上下文上限 16384。`vllm-rwkv` 的基本
State API 满足当前要求；本轮失败不在 State 引擎能力。

## 固定能力结果

| 任务 | 层级 | 动作 | 最后一个真实动作 | 终止点 |
|---|---|---:|---|---|
| L1 FIX01 | tier1 | 1 | `list_directory` | Planner correction 依赖已被丢弃/未知 step |
| L2 CLI01 | tier2 | 1 | `list_directory` | Planner 把已有 step id 再放入 `add_stages` |
| L3 WEB01 | tier3 | 2 | 两次 `list_directory` | Planner 同时 replace/discard 同一 step |
| L4 LEDGER01 | tier4 | 1 | 错选 `date_diff` | Planner 把已有 `implement_app` 再加入 |
| L5 RWKV01 | tier5 | 1 | `web_search` | Planner 同时 replace/discard 同一 step |

Strong Planner 总调用 11 次：5 次初始计划全部通过；6 次动作后 correction 中只有 L3 的第一次
correction 提交成功，其余 `5/6` 都通过 JSON Schema 但违反 rolling plan 语义。Strong Stage Checker
调用次数为 0。

RWKV 总生成 24 次，其中 6 次 Executor action 全部解析并执行成功；18 次 Auditor 生成中 14 次解析
成功、4 次格式/截断失败。Evidence Kernel 共拒绝 12 个 Auditor 判定，L5 在重试耗尽后产生 2 个
protocol rejection。最终 6 个动作边界都只得到 `repair`，没有任何 plan step 被证据完成。

## 最早可直接证实的共同终止失败

最早的共同终止层是 **Strong Planner 的非初始 GoalPlanPatch 语义校验**，不是 JSON 或嵌套格式。

第一条可回查记录：

- 文件：`run_g1j_zero_state_v7_compatibility_r4/cases/AGENT-LADDER-L1-FIX01/event_log.json`
- 记录：event `20` / causal event `CE-000020`
- 对象：`strong_planner_call_failed.data.error`
- 字段：`type="ValueError"`
- 字段：`message="Goal PlanPatch leaves active steps dependent on discarded or unknown steps: ['read-readme-context', 'read-spec-and-implementation']"`

随后 event `21` / `CE-000021` 才产生 `run_yielded(reason="strong_planner_unavailable")`。后者继承前一错误，
但把“模型已成功返回、语义校验失败”误标为“Planner 不可用”，这是新的错误分类问题。

其余四例的直接证据：

- L2 event `23`：`add_stages` 重用现有 ID `implement_cli_and_readme`、`implement_notes_store`、
  `run_verification`。
- L3 event `48`：`replace_stages` 与 `discard_step_ids` 包含同一 step。
- L4 event `20`：`add_stages` 重用现有 ID `implement_app`。
- L5 event `43`：`replace_stages` 与 `discard_step_ids` 包含同一 step。

每个初始 patch 都已经由 `goal_plan_patch_committed` 证明嵌套 schema 可解析。每个 correction 的
`supervisor_request_returned` 也有输出 SHA-256；初始/correction 的 `input_sha256` 与
`output_sha256` 全部不同，排除了旧 plan 缓存复用。具体失败对象是 PlanPatch 的状态语义字段，而非
JSON envelope。

## 根因分层

### 工程问题

1. `OpenAICompatibleSupervisor.plan_goal_patch()` 只调用一次 `_request_json()` 并做 schema 构造；完整
   plan-state 校验直到 `StatefulGoalLoopController._issue_strong_plan_patch()` 的
   `plan.apply_goal_patch(patch)` 才执行。该异常被直接转为 yield，没有把 validator error 与当前合法
   plan 回传 Planner。虽然配置有 `semantic_repair_attempts=2`，GoalPlanPatch 路径实际上没有使用它。
2. 当前 `.env.local` 仍是 G1I/V7 和失效端口；最新 V8 又缺少 G1J 匹配 Head，产品默认配置不可运行。
3. zero-State Selector 启动原先强制绑定 G1I trained-State manifest，导致 G1J 权重在模型输出前因
   `model_artifact mismatch` 失败。已做最小 fail-closed 修复：无 manifest 只允许三个 identity 字段
   精确为 zero；相关测试 `20 passed`。
4. 结果报告把 5 个已 yield 的任务写成 `status="running"`、`failure=""`，且
   `supervisor_failure.failed=false`。这不是上游语义错误的简单继承，而是独立的可观测性错误。
5. 13.3B 服务首次启动约 10 分钟，主要耗时在 26.5GB NAS 权重身份 hash 与模型加载，影响部署性能，
   但不是本轮 E2E 失败原因。

### 模型/Head 质量问题

1. Strong Planner correction 语义有效率仅 `1/6`。模型看到了不同的更新输入，也返回了不同输出，仍
   反复混用 add/replace/discard。工程修复环缺失放大了该问题，但原始语义错误首先由 Planner 产生。
2. 2.9B Selector 在 L4 event `6` 对当前 `inspect_verifier` step 选择 `date_diff`，confidence
   `0.540489`；13.3B 被迫填写 `2025-11-17` 到 `2025-11-17`。该工具选择是直接模型/Head 错误，参数
   错误主要继承了上游错误工具约束。L2/L3 还以 `list_directory` 代替实际 `read_file`，导致无法完成
   read evidence。
3. 13.3B Auditor 在 L5 对同一证据先多次错误判为 `continue`，最终又声称“没有 BlinkDL-specific
   GitHub URL”。实际 `A00001.result.metadata.external_evidence.records` 包含 5 条 BlinkDL GitHub
   记录，包括 `BlinkDL/RWKV-LM`、`BlinkDL` 用户页、`BlinkDL/ChatRWKV` 和 `BlinkDL/nanoRWKV`。
   这是独立的 Auditor 事实 grounding 错误；Evidence Kernel 阻止了错误 completion，但代价是大量重试。
4. 旧 S60/V7 配对开发集上，G1J+匹配 Head 相对 G1I+匹配 Head 修复 10 条、回归 29 条、共同错误
   29 条，accuracy `0.984831 -> 0.977441`，净回归 19 条，主要在 S39。该结论不是裸权重比较，也
   不能代表尚未训练匹配 Head 的 V8。

### 基础设施问题

受控 R4 中 11 次 Strong Planner 请求均成功返回，G1J 两个服务健康，6 次工具动作均执行成功；R4
的终止不是 HTTP、GPU、NAS、JSON transport 或 native State API 故障。之前诊断运行出现的 Planner
429/500、远端代码版本漂移和工作目录导入旧模块均已排除，不计入 R4 模型质量。

## 下游是继承还是独立产生错误

- `run_yielded` 继承 Planner patch 失败，但新增了错误的 `strong_planner_unavailable` 分类。
- `REPORT/results/audit` 继承未完成事实，但新增了 `running + empty failure` 的报告错误。
- L4 的 13.3B 日期参数主要继承 2.9B 错选 `date_diff`，不单独证明 13.3B 缺乏日期能力。
- L5 Auditor 对实际 BlinkDL records 的互相矛盾判定是新的独立模型错误。
- Stage Checker、写文件、命令验证和最终回答都未执行，不能把这些下游阶段判为成功或失败。

## 只允许改一个地方时的最小修复

只改 `StatefulGoalLoopController._issue_strong_plan_patch()` 与 Supervisor 的 GoalPlanPatch 调用边界：
当 `plan.apply_goal_patch()` 抛出状态语义错误时，不 yield，也不改 schema；在固定最多 1 次的 bounded
repair 中把 **当前合法 active plan + 原 patch + 精确 validator error** 回传同一 Strong Planner，
要求只修复 add/replace/discard 关系，再重新做同一原子校验。失败后才 yield，并记录
`strong_planner_semantic_invalid`。

这一个修复直接覆盖本轮 5 个共同终止点，同时保留“强模型是 Planner”和已有真实 replace/discard
机制，不要求 RWKV 承担规划，也不增加新的角色或状态机。

第二优先级才是训练 G1J V8 frontier-only 匹配 Head；不能继续用 V7 compatibility Head 评价最新产品。

## 是否进入 State Tuning

现在不应进入 State Tuning。共同终止原因在 Strong Planner correction 与工程 repair 边界；2.9B 的
线上错误又运行在已知职责错位的 V7 输入。应先完成 Planner 语义修复环和 V8 匹配 Head，再用同一固定
数据复测。只有角色正确、链路畅通后仍稳定复现的 RWKV 错误，才转换为“错误输入/输出 -> 人工验证的
正确输出”样本。

当前已经可以保留两类候选纠错样本，但暂不训练：

- Selector：L4 `inspect_verifier -> date_diff`，正确操作应由固定标签/人工复核后登记；
- Auditor：L5 的 5 条真实 BlinkDL records 与错误 verdict/reason，正确 verdict 必须按完整 success
  evidence 再人工标注。

## 是否需要完整 raw trace

确认最早终止层、错误字段、是否为 JSON 格式问题、是否缓存复用，都不需要更完整 raw trace；当前
`event_log.json`、`audit.json` 和 supervisor input/output SHA 已足够。

要逐字段还原 5 个被拒绝的 Strong Planner correction 对象，则需要 raw response；当前 trace 只保留
output SHA 和 validator 派生出的冲突 ID，没有持久化 Planner 原始 JSON。这是 instrumentation 缺口，
下一轮应在脱敏后保留 `goal_plan` raw response，才能人工检查全部 add/replace/discard 内容。

## 回查入口

- 固定协议：`PREREGISTRATION.md`
- 原样配置与 zero-State 启动失败：`ENGINEERING_UNBLOCK_ADDENDUM.md`
- 真实 R4 汇总：`run_g1j_zero_state_v7_compatibility_r4/REPORT.md`
- 每例完整 causal trace：`run_g1j_zero_state_v7_compatibility_r4/cases/<TASK>/event_log.json`
- 每例模型、动作和 supervisor 摘要：`run_g1j_zero_state_v7_compatibility_r4/cases/<TASK>/audit.json`
- G1I/G1J 配对：`../G1J_VS_G1I_ROLE_COMPARISON_20260901/RESULT.md`
