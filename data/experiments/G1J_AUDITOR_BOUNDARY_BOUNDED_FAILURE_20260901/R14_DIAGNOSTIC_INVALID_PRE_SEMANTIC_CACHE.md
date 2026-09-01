# R14 诊断结果：GoalPlan 缓存提交边界无效

日期：2026-09-02。R14 的 L1、L2 完整进入 RWKV，L5 在第二次 `goal_plan` HTTP 429 中断；但 R14
运行后确认当时的 GoalPlan 缓存只经过 Supervisor JSON/字段解析，未等待 Controller 对当前 rolling plan 的
step ids、依赖、replace/discard 和完成状态做完整语义验证，因此 R14 不能作为最终 zero-State 基线。

- L1：29 actions、138 model requests、64 protocol rejections，完成 1 个阶段；相较 R12 动作从 59 降至
  29，但有 1 次跨同级 stage dependency PlanPatch 拒绝；
- L2：52 actions、183 model requests、33 protocol rejections，完成 2 个阶段；出现 27 次 PlanPatch 语义
  拒绝，其中 14 次重复 replace 已完成 step、9 次重复使用现有/废弃 id，证明无效响应被缓存重放；
- L5：1 个 `web_search` action 和 1 次 Stage Review 后，repair `goal_plan` 返回 HTTP 429。

整改：GoalPlan 缓存改为两阶段提交。模型响应先保存在内存候选；Controller 成功把 patch 应用于重建的 durable
plan 后才写缓存，任何语义拒绝立即丢弃候选。旧实现写入的 22 个 GoalPlan cache 文件已从活动缓存移动到
`temp/invalid_goal_plan_cache_pre_two_phase_20260902/`，可恢复；ContractPlan 和 StageReview 缓存未改动。

R14 的 RWKV trace 仍可用于问题定位，但因为上游无效 patch 重放改变了轨迹，不进入最终能力聚合，也不直接
进入 State Tune 数据。
