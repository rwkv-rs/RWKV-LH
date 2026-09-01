# R15 Strong Planner 限流无效结果

日期：2026-09-02。R15 的 L1、L2、L5 均在首次 `goal_plan` 返回 HTTP 429；每例
`model_requests=0`、`action_count=0`，没有进入 RWKV，因此 R15 完全属于基础设施无效运行，不形成能力
分数，也不得进入 State Tune 数据。

随后对旧缓存做证据迁移：隔离的 22 条 GoalPlan 响应中，仅 9 条能经 `GoalPlanPatch.from_model_value` 重建后
与 R13/R14 durable trace 的 `goal_plan_patch_committed.data.patch` 全对象逐字段相等，已恢复活动缓存；其余 13
条继续隔离。迁移不修改响应、不创建 case 特判，也不恢复任何仅出现在 rejected trace 的 patch。
