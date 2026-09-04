# Lean Planner 后真实 Harness 全量分析

- 固定集：10 题；严格通过 0/10。
- 进入 13.3B Executor：10/10（旧基线 3/10）。
- 实际 Selector 调用：252；S66 身份与原始 logits 交接完整：True。
- RWKV 原始 generation：374；逐字节/摘要/长度/postprocessed 完整：True。
- 首个失败层：{"planner_correction_graph_semantics": 4, "review_replan_or_completion": 1, "selector_executor_mutation_trajectory": 5}。
- 4 题共同根因是 correction graph 复用已有节点 ID；其余题已越过 Planner，失败位于 Selector→Executor schema/轨迹、事务或完成边界。
- 原运行和 RWKV 原始输出均未改动；本报告不复制原始生成文本。
