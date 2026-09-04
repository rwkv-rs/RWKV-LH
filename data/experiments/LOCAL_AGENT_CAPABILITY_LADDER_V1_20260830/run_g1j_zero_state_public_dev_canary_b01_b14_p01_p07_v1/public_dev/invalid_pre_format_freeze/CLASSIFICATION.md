# B01 预格式冻结运行分类

这三个 seed 的 B01 记录均产生于 G1J 输出协议冻结之前，运行状态仍为 `running`，且旧 runner 曾把一次协议拒绝误当作停止。它们不满足 Goal 模型“只有合法 `final_answer` 候选经过终局审计后才停止”的语义，也包含已复现的 Executor 空可见输出问题。

统一分类：`INVALID_EARLY_STOP_NOT_GOAL_SEMANTICS_AND_PRE_FORMAT_FREEZE`。

这些记录只保留用于根因审计，不计入 zero-State Agent 能力基线。原文件未删除，按 seed 原样移动到本目录。
