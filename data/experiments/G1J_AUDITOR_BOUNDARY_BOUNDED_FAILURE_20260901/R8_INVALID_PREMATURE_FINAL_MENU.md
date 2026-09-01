# R8 工程无效中止记录

日期：2026-09-01。R8 在第一例运行中主动中止，输出目录原样保留，不进入模型能力或 State Tune 数据。
首次 Ctrl-C 只关闭了 PTY，`uv/python` 子进程继续运行；发现后已按精确 PID 发送 SIGTERM。R8 的任何
追加记录仍属于同一无效轮次。

中止时 L1 durable state 为 `status=running`、`revision=591`、4 个 Harness actions、36 个
`exact_tool_selection_staged`、36 个 audit boundaries 和 31 个 `goal_final_rejected`。重建 rolling plan
仍有四个未完成步骤，`completed_evidence={}`，因此这些 pre-final 候选都不具备合法入口。

最早工程错误对象为 `StatefulGoalLoopController.run()` 构造 active frontier 菜单时的
`eligible_operations=None`：当 Planner 没有显式填写 `allowed_operations`，`LongHorizonModel` 将 `None`
解释为默认全菜单，并依据旧的通用最小动作规则重新加入 `final_answer`。这绕过了 Goal plan 的完成门，
导致 2.9B Selector 在未完成步骤上被授权选择 final。下游 Auditor 正确拒绝多数候选，但只能形成循环。

最小修复：未完成 plan 始终传明确的、按 retrieval policy 过滤且不含 `final_answer` 的 Harness action
allowset；只有 `plan.complete` 时菜单才严格等于 `("final_answer",)`。R9 使用新目录重跑。
