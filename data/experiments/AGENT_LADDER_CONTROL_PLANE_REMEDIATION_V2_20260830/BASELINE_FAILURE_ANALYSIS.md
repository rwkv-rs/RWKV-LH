# S66 Agent Ladder 基线失败分析

- 固定用例：10
- 进入 Executor：3/10
- Planner 本地语义失败：6
- Planner 传输失败：2
- 实际 Selector 调用：28
- RWKV generation：61
- RWKV 原始输出完整性：True
- Selector handoff/原始 logits 契约：True

逐题分类只来自结构化事件、操作名、参数路径后缀和事务错误；报告未复制任何 RWKV 原始输出。
