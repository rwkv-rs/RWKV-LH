# Round143：Single-Operation Atom Graph v4 Canary 预注册

## 目的

验证一个 atom 只允许一种 operation kind 后，GPT 能否把任务拆成可并行/可依赖的真正原子操作，并由 RWKV 独立生成参数、执行和 Final。

## 固定配置

- 用例：`E2E-B04`、`E2E-M16`、`E2E-LH06`
- Planner/Reviewer：在线 `gpt-5.4`
- Worker：当前本地 RWKV
- 架构：`strong-supervisor-parallel-rwkv-atoms.v4`
- case concurrency：1；stage 内 RWKV concurrency：最多 4
- stage 上限：8
- atom transition 硬上限：40；顶层 transition 上限：200
- atom action budget：read-only 1–4；mutation 固定 1
- tool disclosure：单一 committed operation + final_answer
- semantic repair：1
- 运行中不改代码、fixture、参数、阈值或评价器

## v3→v4 唯一变更

1. 每 atom 恰好一个 allowed operation name；
2. mutation atom 恰好一个 write_root 且 action_budget=1；
3. material mutation 与 verification 必须拆开；
4. Planner采用用户蕴含的最短 canonical JSON key；
5. 初始 scout 禁止把 bind_evidence 当作业务读取替代品。

## 成功门

1. external pass `3/3`。
2. 至少 `2/3` 存在 2+ work atoms 同 stage 且 RWKV时间真实重叠。
3. failed/interrupted atom、ScopeViolation、InputBudgetError、supervisor stage failure均为0。
4. 每题 stages与 GPT stage returned 均不超过8；semantic repair不超过2。
5. 每 atom action_count ≤ committed action_budget；mutation atom action_count 必须为1。
6. 父 workspace业务修改只能来自 completed RWKV atom snapshot merge，controller 不生成业务参数或内容。
7. 顶层输出逐字来自最新 completed finalizer RWKV Final。
8. failed/interrupted snapshot（若出现）不得提交声明写域。

任一门失败，不进入 Full90。

