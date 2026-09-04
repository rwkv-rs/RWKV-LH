# Planner / Controller / Selector / Executor / Auditor 职责边界补充记录

日期：2026-09-04（Asia/Shanghai）

## 触发问题

完整 trace 显示 Step Auditor 在缺少 Planner 声明的读取或写入覆盖时仍尝试完成步骤。需要确认这不是单个 prompt 问题，而是各组件职责是否混淆。

## 冻结输入

- 原始 trace：`LOCAL_AGENT_CAPABILITY_LADDER_V1_20260830/run_g1j_zero_state_public_dev_canary_b01_b14_p01_p07_v1` 中 B01-B14、P01-P06，共 20 个 case。
- 20 个 `event_log.json` 合并 SHA-256：`cd25fe362f7dd3736d6553f4af694d0b92dc46c92713a1e4b5f893a61ca30ed6`。
- 分类脚本：`temp/analyze_g1j_step_audit_rejections_20260904.py`，SHA-256 `90e93eee1fc2969597a18a26004a00810ea9d4c3c84233671474ceee575a7933`。
- 分类输出：`STEP_AUDIT_REJECTIONS.json`，SHA-256 `6fbcfec7fda747fea298a42a677f35827aa306de0fac6f404780af1aa6945342`。

## 全量分类

242 次 Step Auditor 拒绝全部归类，无 `other`：

- 缺成功读取覆盖：160；
- 缺成功写入覆盖：14；
- Audit 输出合同不合法：25；
- `repair` 与 `step_complete=true` 冲突：4；
- 引用失败 Action：16；
- JSON 解析失败：23。

其中 174/242（71.9008%）是 Controller 根据成功 Action 的真实参数即可在模型调用前确定的 read/write root 缺口。旧 evidence record 又没有 Action 参数，所以 Auditor 无法可靠推导路径覆盖。根因是职责顺序错误，不是单纯 Auditor 模型能力不足。

## 固定职责

1. Planner 只声明 step、dependency、`success_evidence`、`read_roots`、`write_roots` 和 operation allowset；这些字段是需求，不是完成事实。
2. Selector 只为当前 step revision 选择一个 eligible tool；同一步内持续局部 WKV，跨 step/revision 和 Final 时重置。
3. Executor 每个新 action clean start，只填写已选工具参数；输入事实限于当前 step 和已声明直接依赖。
4. Harness 是参数、执行结果、副作用、Artifact 和错误的事实权威。
5. Controller Mechanical Evidence Gate 用当前 revision 的成功 Action 精确参数校验 read/write roots。未覆盖时记录确定性 gap，保持步骤未完成，不调用 Auditor。
6. Step Auditor 只在机械覆盖齐全后判断自然语言 `success_evidence`；输入 evidence record 包含 Action 参数。
7. Evidence Kernel 再校验引用、成功状态、step revision、operation allowset、root 覆盖和完成权限。
8. Stage Checker 只检查整个已完成 stage 的一致性；Finalizer 只写 candidate；Final Auditor 才能批准终局。

## 状态边界

- 全局状态：append-only causal ledger，是唯一恢复与完成权威。
- Step 局部状态：`(step_id, step_revision)`、该 revision 的 Action、直接依赖的 accepted evidence、最新机械或语义 gap。
- Selector WKV：一个 step revision 一条局部链。
- Executor WKV：一个 selected action 一条 clean turn；同 handoff 最多一次参数修复。
- Step Auditor / Finalizer / Final Auditor WKV：一个边界一个 clean State，生成后不 merge。

## 实现与验证

- 新事件 `goal_step_evidence_gap_recorded` 持久化确定性覆盖缺口，并作为下一轮 `GoalFrontierStateV1.latest_audit_feedback`。
- `goal_audit_boundary_resolved.verdict=mechanical_repair` 明确 `step_completed=false`、`completion_authority=false`。
- Selector checkpoint 记录 `selector_state_scope_id`；scope 不同则不使用旧 parent。
- Executor `action_session_started` 记录 `causal_fact_scope=controller_step_and_dependencies` 和具体 Action IDs。
- transport 只恢复 raw token IDs 已证明存在的 stop suffix；真实 length 截断不修补，空围栏单独报错。
- 定向链路测试：116 passed。
- 全量测试：821 passed，1 个既有 Python 3.13 `multiprocessing.fork` DeprecationWarning。
- `compileall` 与 `git diff --check`：通过。

## 判定边界

职责和失控路径的工程整改通过。新 Selector Head 尚未训练，也未重跑固定 Ladder，因此这里不宣称 2.9B 选择能力或端到端成功率已经恢复。
