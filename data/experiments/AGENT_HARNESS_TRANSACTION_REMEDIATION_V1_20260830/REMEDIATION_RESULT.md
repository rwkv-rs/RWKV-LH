# Agent Harness 事务与 Planner 控制面整改结果

日期：2026-08-30（Asia/Shanghai）

## 结论

本轮结构性 bug 整改通过。它没有提高或伪造 Agent Ladder 的严格分数，而是恢复了真实 Planner 请求，并把此前“没有写入/只写一部分却完成”的结果改成可审计的 fail-closed。剩余 0/3 严格失败已经落在当前轨迹下的 Selector/Executor 能力缺口，进入后续独立 state-tuning 消融。

## 已修复根因

1. capability projection 从 v2 升级为 v3；写入 atom 的最低动作数至少等于声明写根数，历史 v1/v2 仍可读取。
2. Executor prompt 按真实 `action_budget` 区分单操作与 bounded multi-operation，并在末端明确当前目标及全部写根覆盖要求。
3. mutator 没有成功 path mutation、或未覆盖任一声明写根时，事务不得提交；投影 atom 由依赖 verifier 继续验证，legacy 多操作 atom 保留 mutation 后 observation 约束。
4. Planner 合同要求每个互不重叠的写根有直接动作预算，`action_budget >= write_root_count`。
5. 完整 contract-plan 请求的旧 `gpt-5.6-terra → gpt-5.6-sol` 路由持续 HTTP 500；恢复为已跨简单/中型真实 schema 验证的 `gpt-5.4-mini + reasoning_effort=none`。
6. 修复 `reasoning_effort=none` 遇到 5xx 时被错误提升为 `low` 的重试逻辑；只有 `{minimal, medium, high, xhigh}` 可降到 `low`。没有添加响应前缀剥离、JSON 修复或其他输出归一化。

## 冻结执行

- 事务预注册：`PREREGISTRATION.md`，SHA-256 `92ec9726acd131b43f665962b9ddd5932c6b38d07b33634adbf24a558fe386b1`。
- Planner 恢复预注册：`PLANNER_CONTROL_PLANE_RECOVERY_PREREGISTRATION.md`，SHA-256 `8b43b275cbfe0719b76c0570f2f002668df128c088e284fdb7f5657fa527183b`。
- 执行冻结：`BUGFIX_CANARY_V1_EXECUTION_FREEZE.json`，SHA-256 `ac06e31abd6460b703a1f36b793f47d75aa6f24124123418a1b930ebbace625f`。
- 固定三题：`AGENT-LADDER-L1-FIX01`、`AGENT-LADDER-L1-DATA01`、`AGENT-LADDER-L4-LEDGER01`。
- 架构：S60 2.9B Hidden(mean+last)+h64 MLP Selector；13.3B Executor；G3 offline state；物理 GPU0；strong model 仅 Planner/Reviewer。

## 结果

- 结构门：通过。
- Planner supervisor failure：`0/3`；所有真实请求只使用 `gpt-5.4-mini`。
- capability projection：40 个去重 atom，`40/40` 为 `controller_capability_projection.v3`。
- 预算不可行：`0`。
- transaction integrity fail-closed：`10` 次。
- 已完成但无成功 mutation：`0`。
- 已完成但写根未全覆盖：`0`。
- RWKV raw generation：69 次；外层 raw、raw record、SHA-256、UTF-8 byte 数逐项一致，`postprocessed=false`。
- 模型/state SHA 精确匹配：通过；run 内 profile switch：`0`。
- 物理 GPU：0；产品 18070 全程保留且结束后健康；实验 18075 已释放。
- canary 报告：`run_bugfix_canary_v1/BUGFIX_CANARY_RESULT.json`，SHA-256 `b6134fb68b0143562a953095f8ab676f53ae3236e10f9c7250ee117104a63bc5`。
- 逐题结果 SHA-256：`8fed6f4a47a3d24f045d7471bbceb597d5c98b7ff038715b57b9520946d58ef0`。
- 严格/外部/Agent 完成：`0/3`、`0/3`、`0/3`。该值如实保留，不属于结构门通过条件。

全项目回归：`uv run pytest -s -q` → `635 passed, 1 warning in 138.21s`。warning 是既有 Python 3.13 多线程进程使用 `fork()` 的弃用提醒。`compileall` 和 `git diff --check` 通过；环境未安装 ruff，因此没有伪报 ruff 结果。

## 剩余能力缺口

- 2.9B Selector 在真实连续轨迹中会在未覆盖写根时过早选择 `final_answer`，或把 mutation 目标路由到 `list_directory`。
- 13.3B Executor 即使收到 bounded multi-operation 与全部写根约束，也常在完成一个根后提前 Final。
- 示例包括只写 `summary.json` 未写 `README.md`，或只写 `index.html` 未写 `styles.css`。Harness 已正确拒绝提交。
- 不通过动态隐藏 `final_answer`、改写 RWKV 文本或替模型补动作来掩盖。下一步用不同实体、不同路径的独立 train/dev 数据做 2.9B 与 13.3B 分离 state-tuning，并以冻结真实轨迹和 Agent Ladder 做 holdout。
