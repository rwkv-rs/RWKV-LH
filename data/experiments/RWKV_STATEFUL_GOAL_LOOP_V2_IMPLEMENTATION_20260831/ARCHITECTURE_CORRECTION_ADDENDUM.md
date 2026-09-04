# Stateful Goal Loop v2 架构勘误

- 登记时间：2026-08-31（Asia/Shanghai）
- 原因：实施者错误地把较早的纯 RWKV 默认路径当成当前产品架构，忽略了 `ca1c4c8` 之后已经加入并验证的 Strong Planner。
- 证据时间线：`1d0db99` 为纯 RWKV/R126 恢复；`ca1c4c8` 引入 bounded strong-model supervisor；当前 HEAD `6835285` 已包含 `ContractGraphPatch` Strong Planner、Reviewer 与 RWKV atom 执行路径。

## 对首轮 canary 的处置

`CANARY_PREREGISTRATION.md` 和 `run_stateful_goal_v2_s60_g3_g6_canary_v1/` 保持不可覆盖。该轮关闭 Strong Planner，并新增一套由 13.3B 生成的重复 `GoalPlanPatch`，不代表用户指定的最新架构，因此：

- 0/3 结果保留为失败实验事实；
- 不用于判断现有 Strong Planner 的 PlanPatch 格式或能力；
- 其中 PlanPatch 格式失败不得导出为 13.3B state-tuning 正标签；
- 只有与 Planner 无关且可在正确拓扑中独立重现、经干净 verifier 通过的错误，才可进入纠错数据候选。

## 更正后的权威职责

1. Strong Model 继续作为 Planner，唯一计划协议为现有 `rwkv-lh.contract-graph-planner.v2` / `ContractGraphPatch`；不新增第二套 RWKV PlanPatch schema。
2. Strong Planner 只产生 obligation、依赖、scope、完成检查和增量 correction patch，不选择/执行工具，不填参数，不宣布完成。
3. 所有 Strong Planner work nodes 投影到同一条 13.3B 主 State，按 ready frontier 串行执行；不再为每个 node 创建独立 RWKV atom State。
4. 2.9B 只提供当前 frontier allowset 内的 Top-K；13.3B 选择 operation 并生成参数。
5. 审核由同 profile 的 13.3B Audit Fork 完成；Strong Reviewer 不属于主闭环。审核 WKV 不合并，只有 Evidence Kernel 验证后的结构化 delta 可回到主 State。
6. 只有 13.3B 的原始 `final_answer` 且 RWKV Audit 为 `ready_for_final` 才能完成 Goal。

## State-tuning 勘误

13.3B 不训练 Strong Planner PlanPatch。固定 train/dev 总量仍为 `2000/480`，重新分配为：

- operation + arguments：`900/220`；
- observation → repair：`450/110`；
- audit：`450/110`；
- continue/final：`200/40`。

每条正标签仍必须保留失败输出，在不同项目 family 的干净快照重放，并由 Harness、pytest 或公开确定性 verifier 通过。Strong Model 不能充当标签真值。

