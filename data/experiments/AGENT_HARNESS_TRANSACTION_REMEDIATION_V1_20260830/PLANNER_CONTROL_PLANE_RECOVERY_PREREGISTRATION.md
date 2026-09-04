# Planner 控制面恢复预注册（2026-08-30）

## 目的

在不改变冻结能力题、验收器、RWKV 模型、Selector、Executor state 或原始输出策略的前提下，修复 Agent Ladder V1 基线中 Planner 完整 contract-plan 请求大量 HTTP 500，以及 `reasoning_effort=none` 在重试时被错误提升为 `low` 的控制面问题。

## 冻结证据

- 基线结果：`run_current_s60_g3_g6_baseline_v1_r2/BASELINE_RESULT.json`，SHA-256 `8407949cb8a8b000b69b6edc5e65b171468f88bca009eda4218666c13bfaff51`。
- 基线逐题结果：`run_current_s60_g3_g6_baseline_v1_r2/results.json`，SHA-256 `ed3552eca4480182a2b82bb2872f282600e99f6fb2d56e2f888c54ddc3de072d`。
- 事务反事实审计：`BASELINE_COUNTERFACTUAL_AUDIT.json`，SHA-256 `d2fb2babddc3b7b2f4f872ab960223ed527d580bcf2388033d789c80746b1541`。
- `gpt-5.4-mini + reasoning_effort=none`，`AGENT-LADDER-L1-FIX01` 完整 schema 探针：SHA-256 `1a19f2928883bb400fb3a24bd6367f85f677786cc4b1c79576abab666d78b5ec`；1 次 HTTP、14,919.2 ms、5 obligations、4 nodes、严格单 JSON、语义拒绝 0。
- 同配置 `AGENT-LADDER-L4-TRACKER01` 完整 schema 探针：SHA-256 `b2ade299fd4b1f1de9c99986e38d2918dad7dad56d9c5ef176c5979f8a6d2cb9`；1 次 HTTP、27,176.0 ms、10 obligations、4 nodes、严格单 JSON、语义拒绝 0。
- 探针只保存响应形状与摘要，不保存请求正文、响应正文、凭据。

## 根因与固定整改

1. 当前主路由 `gpt-5.6-terra`、后备 `gpt-5.6-sol` 对真实完整 contract-plan schema 持续返回 HTTP 500；小 readiness 成功不能代表真实计划可用。
2. `gpt-5.4-mini` 在 `reasoning_effort=none` 下已跨简单/中型任务通过完整 schema 和本地语义校验；使用它作为 Planner/Reviewer 控制面恢复候选。
3. `_request_json_single` 只允许把 `{minimal, medium, high, xhigh}` 在 contract-plan 5xx 重试时降为 `low`；`none`、空值和 `low` 必须原样保留。不得对响应做前缀剥离、JSON 修复或其他归一化。
4. 候选配置固定为：
   - `SUPERVISOR_MODEL=gpt-5.4-mini`
   - `SUPERVISOR_FALLBACK_MODELS=`
   - `SUPERVISOR_REASONING_EFFORT=none`
   - `SUPERVISOR_CONTRACT_PLAN_REASONING_EFFORT=none`
   - `SUPERVISOR_CONTRACT_REVIEW_REASONING_EFFORT=none`
   - `SUPERVISOR_RETRY_ATTEMPTS=2`
   - `SUPERVISOR_MAX_CONTRACT_PLAN_TOKENS=4000`
   - `SUPERVISOR_MAX_CONTRACT_REVIEW_TOKENS=2400`
   - `SUPERVISOR_SEMANTIC_REPAIR_ATTEMPTS=2`
   - 请求继续串行；缺陷复测固定关闭 plan cache 以强制真实请求，通过后产品配置可恢复严格验证缓存。

## 固定缺陷复测

使用 Agent Ladder V1 冻结任务中的三个用例，顺序固定：

1. `AGENT-LADDER-L1-FIX01`：基线 Planner 500；验证真实计划恢复。
2. `AGENT-LADDER-L1-DATA01`：基线进入 RWKV、无真实 mutation 却完成；验证 mutation 提交门。
3. `AGENT-LADDER-L4-LEDGER01`：基线多写根只覆盖一部分；验证预算和全部写根覆盖。

运行架构与基线保持一致：2.9B S60 Hidden(mean+last)+h64 MLP Selector；13.3B Executor；G3 offline state；GPU0；progressive disclosure；strong model 只做 Planner/Reviewer；RWKV 每个 atom 保持单一 state；不允许修改、删除、重排、隐藏、截断或替换 RWKV 原始输出。产品 18070 必须全过程健康，实验端口固定 18075，经本地 29613 使用；Selector 固定本地 29621。

## 通过门槛

- Planner：3/3 不得出现 supervisor failure；所有返回继续满足严格单 JSON 和本地 schema/语义校验。
- 投影：所有新建 atom 必须为 capability projection v3；每个 mutator 的 `action_budget >= max(1, write_root_count)`。
- 事务：无成功 path mutation 不得提交 mutator；每个声明 write root 必须被成功 path mutation 覆盖；不满足时必须 fail closed，不能假完成。
- 状态与引擎：模型/state SHA 精确匹配，物理 GPU0，run 内 profile switch 为 0。
- 完整性：所有 audit 的原始 RWKV 输出策略保持 append-first，`raw_rwkv_outputs_modified=false`；冻结题、验收器、阈值和相似度算法不变。
- 回归：相关测试、扩展控制器测试、全量 pytest 全过；真实复测结束后产品 18070 健康且实验服务清理。

严格题通过数作为能力观测值记录，但不得为了提高该数修改上述门槛或冻结题。若 Planner 已恢复而 RWKV 仍失败，应归类为后续 Selector/Executor state tuning 缺口，不能由 Harness 伪造成功。
