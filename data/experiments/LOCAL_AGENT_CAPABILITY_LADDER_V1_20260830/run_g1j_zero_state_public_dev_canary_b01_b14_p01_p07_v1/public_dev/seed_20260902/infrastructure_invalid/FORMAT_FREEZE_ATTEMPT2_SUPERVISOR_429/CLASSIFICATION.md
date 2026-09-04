# FORMAT_FREEZE_ATTEMPT2_SUPERVISOR_429

- 时间：2026-09-02（Asia/Shanghai）
- 用例：B01
- seed：20260902
- 分类：`INFRASTRUCTURE_INVALID_SUPERVISOR_RATE_LIMIT`
- 能力计分：不计分

格式冻结后使用完全相同的 B01、seed、Strong Planner 模型与参数再次运行。第一次 `goal_plan` 请求返回 HTTP 429；`model_requests=0`、`action_count=0`、`protocol_rejection_count=0`。因此 Executor、Auditor、Finalizer 和任何工具均未被调用，这次尝试不能表示 zero-State Agent 能力。

本目录由固定结果路径可恢复移动而来，没有删除证据。未更换 Planner、未修改采样参数、未触发隐藏重试、未训练 Head 或 StateTune。
