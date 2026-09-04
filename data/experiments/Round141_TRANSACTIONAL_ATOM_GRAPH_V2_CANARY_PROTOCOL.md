# Round141：事务化原子图 v2 Canary 预注册

## 目的

验证 `strong-supervisor-parallel-rwkv-atoms.v2` 是否解决 Round140 的任务身份、失败副作用、失败依赖、finalizer 漂移和工具权限问题，同时保持 GPT 只做低频阶段规划/复核、多个 RWKV 完成原子工作的目标架构。

## 固定用例与配置

- 用例集合：`E2E-B04`、`E2E-M16`、`E2E-LH06`
- 实际执行顺序由固定 suite catalog 决定
- Planner/Reviewer：在线 `gpt-5.4`
- Worker：当前本地 RWKV
- tool disclosure：full，但每个 atom 只展示其权限允许的子集
- 架构：`strong-supervisor-parallel-rwkv-atoms.v2`
- case concurrency：1
- stage 上限：12
- stage 内 atom 上限：4
- 单 atom transition 上限：40
- 顶层 transition 上限：200
- semantic repair：1
- 运行中不修改代码、fixture、参数、阈值或评价器

## v1→v2 固定变更

1. atom workspace snapshot + completed-only merge；
2. atom objective 进入子 RWKV active request；
3. completed dependency handoff 注入；
4. 动态依赖枚举；
5. finalizer 生命周期与 stale acceptance 校验；
6. atom 权限对应的工具子集；
7. Planner atomization/output-shape 指令。

不允许加入用例 id、fixture 内容或目标答案特判。

## 预注册成功门

1. external pass：`3/3`。
2. 至少 `2/3` 用例有一个含两个及以上 work atoms 的 committed stage，且 RWKV model execution 时间真实重叠。
3. failed/interrupted atom outcome：0；ScopeViolation：0；supervisor stage failure：0。
4. 每题 GPT stage returned 调用不超过 8；semantic repair 不超过 2 次。
5. 每个 work atom action_count 不超过 20；每个 finalizer action_count 不超过 12。
6. 顶层输出逐字来自最新 completed finalizer 的原始 RWKV `Final`，controller 不改写。
7. 若出现 failed/interrupted atom，其 snapshot 内写入不得出现在父 workspace；该条件即使其他门已失败也单独检查。

任一门失败，不进入 Full90，保留全 trace 并登记系统根因。

