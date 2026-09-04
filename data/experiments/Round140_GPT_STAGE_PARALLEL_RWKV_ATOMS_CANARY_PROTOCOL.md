# Round140：兼容 Stage Schema 后的并行 RWKV 原子 Canary 预注册

## 目的

在不改变 Round139 架构、任务、指标和阈值的前提下，仅验证 provider-facing stage schema 兼容性整改后，GPT 阶段规划、并行 RWKV 执行、只读 finalizer 和 exact-candidate acceptance 的完整闭环。

## 固定配置

- Planner/Reviewer：在线 `gpt-5.4`
- Worker：当前本地 RWKV，full tool disclosure
- 架构：`strong-supervisor-parallel-rwkv-atoms.v1`
- 用例顺序：`E2E-B04`、`E2E-M16`、`E2E-LH06`
- case concurrency：1
- stage 上限：12
- stage 内 atom 上限：4
- 单 atom transition 上限：40
- 顶层 transition 上限：200
- semantic repair：1
- 运行中不修改代码、fixture、阈值或评价器

## 预注册成功门

1. 三题 external pass 必须为 `3/3`。
2. 至少 `2/3` 用例产生一个含两个及以上 work atoms 的已提交 stage，并在模型调用时间线上实际重叠。
3. 作用域违规、stage 协议失败和 atom 执行失败均为 0。
4. 每题 GPT stage 调用不超过 12。
5. 每个 work atom 的 action 数不超过 40。
6. 顶层输出必须逐字来自已完成 finalizer atom 的原始 RWKV `Final`，controller 不改写。

任一门失败，不进入 Full90；保留完整 trace 并做系统根因分析。

## 唯一允许的 Round139→Round140 变更

删除 provider-facing JSON Schema 中上游不支持的 `allOf/if/then/else`。全部互斥与权限规则继续由本地 `SupervisorStage.create()` 强制校验。

