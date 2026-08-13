# Round13 预注册：Post-Action Catalog-Bound Witness Protocol

预注册日期：2026-08-13（任何 Round13 RWKV 请求之前）

## 固定依据

同一套冻结 Round12 核心在用户重启推理引擎后完成了新的 90 题控制运行。Goal-only
并发诊断的 120 个返回全部是可解析 JSON，且 concurrency 8 为 30/30 有效 Goal；完整控制
中 83/90 Goal 解析成功、80/90 保存计划、77/90 进入动作，但 0/90 完成。由此排除“当前
转发仍普遍截断 Goal”这一解释。

不读取 hidden acceptance 或 Codex reference 的反向 lifecycle 分析显示：

- `witness_intent_precommit_started` 到达 48 题，但仅 4 题成功 precommit；
- `witness_intent_contract` 是 47/90 的终止原因；
- 90 题共发生 99 次 precommit 请求，而真正到达 witness catalog 的仅 4 题；
- Round11 没有这个 pre-action gate；Round12 新增后，proof/evidence 漏斗没有改善，仍为
  `criterion_evidence_committed=0`、`run_completed=0`。

这说明主要放大器不是缺少更多校验，而是系统要求弱模型在看不到 action result 和真实 source
catalog 时，重复输出 Controller 已经知道的 task/criterion/ownership 字段，并提前猜测 source
kind。严格枚举和重复字段把动作与后续证据阶段一并阻断。

- Post-restart control results SHA-256：
  `344f7cbec46b87ba2820e4579fca2388ade890c9fbf5b6bbab14d297b8c7de51`
- Score-independent backward analysis SHA-256：
  `10f0f2a9febeb441fcb5f09f7596b9d98974027d8e92ef77eb1b122b67e1eaee`
- 90 题 post-run standard comparison SHA-256：
  `a3bb2c820a0ea6410244d8efdfa07b8ccefe20b571fd09269e7781b6d032a2fb`

## 唯一结构变量

用 `post_action_catalog_bound_witness.v2` 替换 Round12 的
`rwkv_witness_intent_lifecycle.v1`：

1. action selection 和 action execution 之前不再调用 witness precommit，也不因 witness JSON
   阻止 RWKV 已选择的 action。动作的 raw result、workspace/artifact 变化先按原有路径持久化。
2. 对 `satisfies_criteria` 的每个 ID，Controller 只从 RWKV 已保存的 TaskGraph 逐字投影稳定
   `intent_id/task_id/criterion_id` skeleton；它不生成 criterion、producer、expected value、source、
   proof 或答案。
3. 动作之后，运行时不使用 criterion 文本、acceptance、reference 或相似度，完整枚举当前作用域
   的 action/workspace/direct-dependency 原始 source 与所有类型合法 transform，并记录 catalog digest。
4. RWKV 在同一个 post-action 语义请求中看到真实 action result、deterministic verifier、完整 raw
   source 目录。它为每个 skeleton 明确选择 actual source 和 expected source；若 expected 来自 Goal，
   则由 RWKV 同时提交原 Goal 的精确 quote 与 typed JSON value。source kind、owner 和读算子只由
   RWKV 选择的 opaque ID 逐字展开，不要求 RWKV 再抄枚举字符串。
5. 运行时把该选择编译为持久 WitnessIntent，再按已选 raw source 渐进披露派生 WH handle；RWKV
   继续逐字选择最终 actual/expected handle。系统不得搜索替代 ID、交换两侧、选择相等值或修改
   transform。ProofEngine 与独立来源、hash、typed exact equality、provenance 检查保持不变。
6. schema/scope/ID 不合法时 fail closed，但错误只终止证据请求，不撤销已落盘 action。proof 失败
   继续使用 task-local binding revision，不重跑已成功 action；所有 raw/parsed/normalized/compiled
   payload、catalog、digest、proof input/output 和状态变化完整记录。

这是一个变量：把“看不到观察时猜七字段 precommit”改成“观察与目录存在后，由 RWKV 选择 opaque
source/handle”的单一消息边界与状态生命周期。它借鉴 Prime Agent 的边界适配、状态协议和渐进披露，
但不引入 provider、多模型、subagent、Python kernel 或通用 RLM 产品形态。

## 不作弊边界

- Task/criterion 仅来自先前 RWKV TaskGraph；Controller 只投影已有 ID，不能补 criterion 或任务。
- actual/expected source、Goal literal、semantic pass/replan 和最终 handle 均由 RWKV 选择。
- catalog 必须完整按结构枚举，不能按 criterion、标准答案、hidden acceptance、相似度或历史通过率
  过滤、排序、推荐候选。
- ID 展开只能恢复被选 source 自带的 kind/owner/operator，不能纠正别名、试探其他候选或用规则替
  RWKV 决定。
- 不修改 workspace 来让 proof 通过；不增删改查 RWKV final，交付仍必须是 raw bytes exact。
- 标准答案和 hidden acceptance 只在完整 90 题全部终止后比较。

## 明确不改

- Goal 1--5 criterion 上限、Goal parse、初始计划、obligation replan、recovery、action catalog/G1i、
  sampling、并发 8、max transitions 200、数据、验收和相似度算法不改。
- 本轮不修 `priority='high'`、Goal criterion 容量、G1i envelope、obligation replan schema 或任何
  action 参数问题；它们保留为后续独立变量。
- 不增加 verifier、completion budget 或模型；不降低 ProofEngine 的独立证据要求。

## 固定运行与验证

- RWKV-E2E-90 v1，Basic/Medium/Hard 各 30；模型
  `rwkv7-g1i-13.3b-20260805-ctx16384`，endpoint `127.0.0.1:29610/v1`。
- 运行前后完整产品测试、LH-Control-30；正式生成前冻结源码/data manifest 和 protocol hash。
- 必须保存 90/90 prompt/raw/parsed/normalized/event/state/workspace；先做 score-independent backward
  causality，再读取 frozen reference 和 acceptance。

## 预注册诊断门

- claimed task 的事件顺序必须为 `action_selected < attempt_started < action_returned <
  witness_source_catalog_prepared < witness_selection_started < witness_catalog_prepared <
  witness_selection_compiled`；前一个 catalog 是不含 criterion 语义的完整 source discovery，后一个只
  增加 RWKV 已选择的 Goal literal，不得出现 Round12 pre-action precommit gate。
- 进入 evidence 的任务必须 100% 使用 catalog 中真实 WS/WH ID；Controller 编译前后 ID、kind、owner、
  operator 可逐字追溯。
- `invalid expected witness source kind` 和七字段 precommit schema 拒绝必须归零；这两类字段不再由
  RWKV 输出。
- 至少一条 proof passed、一条 VERIFIED CriterionEvidence 和一题真实 Completed；否则结构诊断失败。
- FP 恢复为硬门：必须为 0。Offline 全过、Control 30/30、因果链 90/90、所有需要 final 的 case
  raw byte equality 全过。

## GitHub 晋级门

只有同时满足以下条件才提交并推送：FP=0、Strict >7、Completed >7、External 不低于当前正式可回档
最佳、全量回归和审计通过。否则保存 Round13 全部本地数据与因果分析，结论为 `do_not_upload`，远端
继续停在 Round2 checkpoint `b5aa2b2d64036f41aab3ccdc20b2cbfb718e5dbe`。
