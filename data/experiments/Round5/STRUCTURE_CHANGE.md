# Round5 结构变更

Round5 实施预注册的 `linear_typed_criterion_assertion.v1`，只改变 validation/criterion 的模型边界形态与
同一决定复用路径。

## 已实施

- run schema v4：CriterionClaim 增加 `claim_protocol` 与逐步 `normalization_trace`，兼容加载 v1/v2/v3。
- validation v3：RWKV 返回非递归 `source + selector + transforms` assertion；所有语义字段仍由 RWKV 给出。
- 透明 adapter：source 原样映射为 ref/literal，transforms 按原顺序包裹；raw、normalized、trace 与求值结果
  全部持久化。
- source-specific fail-closed：未知字段、与 source 不相容字段、联合枚举占位值均拒绝，不静默删除或 coercion。
- explicit `model_cross_check` 若存在则同一 semantic decision 同时携带 assertion；没有显式检查时仍只调用一次
  optional criterion validation。
- Task postcondition 与 Goal evidence 继续分离；semantic pass + proof fail 可以完成 Task，但不能生成 Goal
  evidence；semantic replan 不能被 proof 覆盖。
- final proof revalidation 按 claim protocol 重新执行相同 linear assertion，防止 workspace 变化后沿用旧证据。

## 未实施

- 没有从 Goal 文本、文件状态、hidden acceptance 或 Codex 标准答案推导 assertion。
- 没有删除 RWKV 多余字段、拆分联合字符串、补 path/selector/value，或从多个候选中选通过者。
- 没有修改工具集、Goal/plan/action/replan/final prompt、采样、并发、数据集或 final answer。
- 没有复制 Prime Agent 代码，也没有加入 provider、subagent、TUI、MCP 或通用 RLM 产品层。

## 实验结论

External 从 Round4 `7` 升至 `12`，总请求从 `802` 降至 `705`，但 Agent completed 仍为 0，故不是最佳
checkpoint。顶层 validation 有效 attempt 改善，但 `0/55` assertion 进入无损归一化；下一瓶颈是抽象
联合 schema 被弱 RWKV 当成输出模板，而不是 proof evaluator 本身。
