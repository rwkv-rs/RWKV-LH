# R9 zero-State Goal 菜单门预登记

> 执行后状态：基础设施无效中止。R8 子进程残留导致短时并发，详见
> `R9_INVALID_CONCURRENT_OBSERVER.md`。R9 不进入能力统计或训练数据。

日期：2026-09-01。沿用固定五例、G1J 2.9B Selector、G1J 13.3B Executor/Auditor、三路 zero
profile、`concurrency=1`、`max_transitions=120` 和全部既有验收口径。

在 R8 两项已测试工程修复之上，只增加一个授权修复：plan 未完成时传入明确的 Harness action
allowset，按 run retrieval policy 过滤并强制排除 `final_answer`；plan 完成时仍只允许
`final_answer`。不得改 Selector logits、Prompt、Evidence Kernel、Planner、State 或验收阈值。

固定 gate：

- action Audit repair 后下一次 Selector payload 不含 `final_answer`，且 Planner 不被调用；
- 未完成 frontier 的每个 Selector payload 均不含 `final_answer`；
- 完成 plan 后 payload 的 eligible labels 只含 `final_answer`；
- 全量回归通过；新目录运行，不覆盖 R7/R8。
