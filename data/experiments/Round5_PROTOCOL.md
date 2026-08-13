# Round5 预注册：RWKV 线性 Typed Assertion 协议边界

预注册日期：2026-08-12（任何 Round5 RWKV-E2E-90 请求之前）

## 1. Round4 因果依据

Round4 External `7/90`、Strict `0/90`、Agent completed `0/90`。26 题进入 validation，84 次
criterion evaluation 中 RWKV pass 34 次，但 proof pass 为 `0/84`；55 条实际 claim 全部 REJECTED。
主要公开模型输出问题是自创 comparison/op、subject/producer 越权、expected 指向 workspace，以及把 selector
写成递归 expression op。这表明独立证据边界应保留，但“semantic decision + 自由递归 DSL”不适合当前
RWKV。

Round4 还有 132 个 validation 请求而 claim evaluation 只有 84 次。显式 `model_cross_check` 已经调用同一
RWKV 后，criterion lane 又重复调用一次；这违反一个模块一个职责，也增加弱模型协议暴露面。

## 2. 唯一结构变量

实施 `linear_typed_criterion_assertion.v1`：只改 validation/criterion 的模型边界协议形态和同一决定的内部
复用，不改变证据语义。

### 2.1 RWKV validation v3

RWKV 返回 `long-horizon.validation.v3`：`decision=pass|replan`、reason 和每个 declared criterion 恰好一条
`criterion_assertion`。每条 assertion 仍由 RWKV 明确选择：

- criterion、subject_task_id、producer_task_id、comparison；
- actual 的 source/path/task/artifact/memory、selector 和线性 transforms；
- expected 的 Goal literal 或 direct dependency ref、selector 和线性 transforms；
- Goal literal 的逐字 quote 和 typed JSON value。

值表达式统一为非递归结构：

```json
{
  "source": "workspace|action_result|dependency_artifact|dependency_memory|goal_literal",
  "path": "workspace-relative path",
  "task_id": "direct dependency when needed",
  "artifact_id": "registered artifact when needed",
  "memory_id": "registered memory when needed",
  "selector": {
    "kind": "text|json|json_pointer|directory_file_set|sha256|path_exists|output_text|output_json",
    "pointer": "RFC6901 pointer when needed",
    "recursive": true,
    "path_type": "any|file|directory"
  },
  "goal_quote": "exact quote when source=goal_literal",
  "value": "typed JSON when source=goal_literal",
  "transforms": [
    {"op": "count|sum|group_sum|object_set|sort|sha256"}
  ]
}
```

只允许 `comparison=exact_equals`。`path_exists` 求值为 bool，因此 existence 仍以 exact equality 对 Goal
literal bool 求值，不增加自然语言规则。

### 2.2 透明边界适配

Controller 将 RWKV 的单一线性 assertion 一一转换为现有 bounded `ProofExpr`：source/selector 不变地成为
`ref` 或 `literal`，transforms 按 RWKV 给出的顺序逐层包裹。适配器不得添加 path、pointer、value、quote、
task/artifact/memory id、transform、criterion、subject、producer 或 comparison。

raw assertion、normalized ProofExpr、每一步转换和最终求值均持久化；未知字段或 enum fail closed。不会从
多个 assertion 中选择能通过的一条，也不会根据 Goal 文本推断 selector/transform/expected。

### 2.3 单次语义决定

- 如果 Task 显式 required `model_cross_check`，该同一次 validation v3 的 semantic decision 仍决定 Task
  verifier，同时其 assertion 进入 criterion proof；不再追加第二次 criterion cross-check。
- 如果 Task 没有显式 `model_cross_check`，deterministic required postconditions 通过后只调用一次 optional
  criterion validation v3。
- semantic replan 仍不能被 proof 覆盖；semantic pass 但 proof 无效时 Task postcondition可以完成，但没有
  Goal evidence。

本轮不增加 proof rejection 后的模型 correction call；validation JSON contract 原有的最多一次协议纠正保留。
因此可以单独测量线性 typed 形态与重复调用消除的作用。

## 3. 明确不改

- 不改 Goal parse 1–5 criteria、plan direct-claim coverage、task/action/replan/final prompts；
- 不改工具目录、G1i 外壳、参数 schema、采样、并发 8、200 transitions 或 recovery budget；
- 不新增 Goal obligation recovery、criteria 容量、StateCapsule、Repo Map、recurrent state、subagent/provider；
- 不用 hidden acceptance、Codex 标准答案、题号或 action expected 参数生成 assertion；
- 不修改、筛选或替换 RWKV final answer。

## 4. 必测

1. linear ref/literal 与 transform 顺序无损归一，raw/normalized 均可审计；
2. unknown source/selector/transform/field、workspace expected、越权 dependency、同源两侧继续拒绝；
3. `path_exists` 只执行 RWKV 选择的 path/type 并与 RWKV Goal literal bool exact compare；
4. 重复/缺失 assertion 整批拒绝，不挑选；RWKV replan 不执行 proof；
5. explicit `model_cross_check` + satisfies criteria 每次 attempt 只产生一个 validation semantic request；
6. final re-evaluation、v2/v3 history migration、raw final byte equality继续通过；
7. 完整离线、LH-Control-30、E2E-90 与历史恢复全过。

## 5. 固定指标与上传门槛

- 固定模型、E2E-90、Basic/Medium/Hard 各 30、标准答案 SHA-256
  `947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`、hidden acceptance、
  `utf8-byte-ngram-cosine.v1` 与 Round4 相同。
- 完整报告 External、Strict、Agent completed、FP/FN、validation requests、assertion coverage/pass/rejection、
  prompt/output tokens 和非干预。
- Round4 不是可接受安全基线，不能把其全阻断 FP=0 设为优化目标；恢复的安全门槛仍是最近非空完成轮
  Round3 的 FP≤9。方向目标 FP=0，但必须同时有真实 completion。
- 新 GitHub 最佳回档要求 External > 当前最佳 8、FP≤9、Strict/非干预/因果链/Control/离线全部通过。
  未达到则保留本地完整数据，不上传为最佳点。

## 6. 反作弊

允许：像单工具协议一样让 RWKV 选择 typed assertion，程序透明归一并执行 exact computation。

禁止：根据 Goal 自然语言、题号、hidden check 或标准答案替 RWKV选择 assertion kind、path、selector、
transform 或 expected；补缺失字段；尝试多个候选后选能过者；把 proof rejection 改成 pass；对 RWKV 最终
输出增删改查。
