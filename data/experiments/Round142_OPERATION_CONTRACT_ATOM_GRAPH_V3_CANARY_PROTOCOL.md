# Round142：Operation Contract 原子图 v3 Canary 预注册

## 目的

验证 GPT Planner 输出“阶段 + 原子 + 允许操作集合 + action budget”，多个 RWKV只负责操作参数、执行、观察和 Final 的 v3 架构，是否消除 Round141 的工具漂移、长循环和 handoff 输入超限。

## 固定用例与配置

- 用例：`E2E-B04`、`E2E-M16`、`E2E-LH06`
- 实际顺序：固定 suite catalog 顺序
- Planner/Reviewer：在线 `gpt-5.4`
- Worker：当前本地 RWKV
- 架构：`strong-supervisor-parallel-rwkv-atoms.v3`
- case concurrency：1
- stage 内 RWKV concurrency：最多 4
- stage 上限：8
- 全局单 atom transition 硬上限：40
- 每 atom action budget：由 committed stage 给出，范围 1–8
- 顶层 transition 上限：200
- tool disclosure：full，但仅展示 atom.allowed_operations + final_answer
- semantic repair：1
- 运行中不修改代码、fixture、参数、阈值或评价器

## v2→v3 唯一变更

1. atom 增加 `allowed_operations`（1–6 个真实 Harness operation names）；
2. atom 增加 `action_budget`（1–8）；达到预算后只允许 RWKV `final_answer`；
3. Stage request 附带 operation catalog，provider schema 动态枚举真实操作；
4. 本地校验 operation 与 read/write/exclusive scope 相容；
5. dependency handoff 删除完整 action history，只保留 bounded candidate 和最小 artifact facts；
6. Planner允许选择操作种类与明确用户蕴含的 output shape，但仍不得生成参数或执行工具。

不允许用例 id、fixture 内容、隐藏目标答案或特判。

## 预注册成功门

1. external pass：`3/3`。
2. 至少 `2/3` 有一个 2 个以上 work atom 的 committed stage，且 RWKV执行时间真实重叠。
3. failed/interrupted atom：0；ScopeViolation：0；InputBudgetError：0；supervisor stage failure：0。
4. 每题 committed stage 不超过 8；GPT stage returned 不超过 8；semantic repair 不超过 2。
5. 每个 atom 的 action_count 不得超过其 committed `action_budget`。
6. B04 的 byte-preserving copy atom 必须只通过公开工具执行与证据完成，不允许 controller 复制或改写业务文件。
7. 顶层输出逐字来自最新 completed finalizer 的原始 RWKV Final，controller 不改写。
8. failed/interrupted snapshot（若出现）不得把声明写域提交到父 workspace；该安全门独立检查。

任一门失败，不进入 Full90，保留全部 trace 并登记系统根因。

