# Round11 结构变更

## 预注册单变量

Round11 的唯一 E2E 变量是 `persistent_unresolved_obligation_lifecycle.v1`：

- 结构合法的 RWKV 基础计划立即执行，不再因未一次覆盖全部
  `satisfies_criteria` 而同步拒绝。
- 系统只将 Immutable Goal 中尚无 VERIFIED evidence 的 criterion ID 持久化到
  `GoalObligationState`；不生成 criterion、producer、任务或答案。
- 只有当所有 active required task 都完成而 required evidence 仍缺失时，才从 SQLite
  权威状态确定性生成 capsule，由 RWKV 提出增量任务。
- Controller 只检查 schema、ID 唯一性、DAG、已完成依赖、criterion ID 存在性与对
  unresolved 集合的显式关联；不修改 RWKV 任务语义。
- 最多三代 replan；每代保存完整 capsule、digest、raw response、parsed/normalized
  payload、ID mapping 与状态变化。
- `long-horizon.run.v5` 增加持久义务状态，v4 迁移不猜测历史义务。

Goal 1--5 容量、action/proof/binding 协议、sampling、hidden acceptance、Codex 标准答案、
90 题数据集、并发 8 和 200 transitions 上限均保持不变。

## 实测结论

- 初始 direct-claim coverage 终止从 Round10 的 30 题降为 `0`，初始
  `goal_obligation_planning` 请求为 `0`。
- External 从 15/90 升到 18/90，但 Completed/Strict 仍为 0/0，FP=0。
- 232 次 assertion evaluation 中 proof pass 为 0；82 条 claim 全部被拒绝，最终
  VERIFIED evidence 为 0。
- 48 题进入 obligation replan，95 次 replan 启动、190 次模型请求、追加
  197 个任务。全轮总请求从 983 增到 2175，prompt token 从 2,092,687 增到
  5,460,587。

因此，这个变量是“解除早停、暴露更深瓶颈”，不是可上传的更优架构。

## 不作弊边界

- RWKV 决定基础任务和每次追加任务；系统不从 criterion 文本生成任务。
- 系统不使用 hidden acceptance、Codex 答案或相似度筛选任务、claim、proof 或最终输出。
- 透明 normalizer 只执行白名单外壳展开和 schema 验证，不补字段、参数或答案。
- 本轮没有 completed case，因而没有可被 Controller 改写的最终答案。

