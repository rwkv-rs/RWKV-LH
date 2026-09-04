# Selector Eligibility Ablation V1 预注册

## 固定来源

- 真实 Harness：`run_s66_g3_g6_post_lean_contract_v1/results.json`。
- SHA256：`196cf691f1c6babe213dd05f7ed8e9c7aa4e149b5e26903f49327d13b3921778`。
- 数据：10 题全部 atom SQLite 中已提交或拒绝的 S66 原始 25 维 logits，及父图中 Controller 已提交的 `allowed_operations`、`minimum_actions`。
- 不重新调用模型，不改动来源 logits、selected_operation、状态或 RWKV 输出。

## 根因假设

在线 Selector 对固定 25 类做全局 argmax，但每个 atom 的 Scoped Harness 只暴露 Controller 投影的操作子集；此外在 `minimum_actions` 未满足前，Controller 必然拒绝 `final_answer`。固定全菜单因此允许 Selector 选择结构上不可执行的类，并把该错误误传给重型 Executor/协议重试。

## 固定反事实 arms

1. `A_global`：现状，25 类全局 argmax。
2. `B_atom_allowset`：只在 `allowed_operations + final_answer + ABSTAIN` 内取原始 logits argmax。
3. `C_atom_allowset_phase_gate`：只在 `allowed_operations + ABSTAIN` 内取 argmax；仅当此前成功/失败 direct action 总数达到 `minimum_actions` 时加入 `final_answer`。

所有 arm 使用同一条原始 logits、相同 tie-break（类序较早者优先），不重新归一化，不改公式。

## 固定指标

- `selected_outside_atom_allowset`：选择既不在 atom allowset，也不是 `final_answer/ABSTAIN`。
- `premature_final_answer`：达到 `minimum_actions` 前选择 final。
- `structurally_ineligible`：上述两项并集。
- ABSTAIN 率、各类选择分布、相对 A 的选择变化数。
- 逐题和全 10 题均报告；不得依据结果改评价口径。

## 决策阈值

- 只有 C 在不改变原始 logits 的前提下，将 `structurally_ineligible` 从非零降到严格 0，才进入版本化在线协议实现。
- ABSTAIN 保留为 fail-closed 类，不因本次消融强制改写为某工具。
- 本消融不声称反事实工具语义正确；它只验证 Controller 已知的执行资格边界。
