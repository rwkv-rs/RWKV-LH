# R13 zero-State 工程根因整改重跑预登记

日期：2026-09-02。R13 使用与 R12 相同的固定 Agent Capability Ladder L1-L5、G1J 权重、Prompt、
`concurrency=1`、`max_transitions=120`、评价口径与阈值；Selector、Executor、Auditor 继续使用
`profile_id=zero`，没有加载任何已有 State。

相对 R12 只允许以下三项通用工程改动：

1. `write_roots=[]` 的只读 Goal step 机械排除 workspace mutation 工具；
2. action Audit 的八条证据投影保留当前边界及覆盖 step read/write roots 的最新成功 Harness 事实，避免
   被无关重复动作挤出；
3. 对结构有效的 Strong GoalPlan/StageReview 使用内容寻址缓存，键包含模型、Prompt、schema、请求材料、
   plan、事实和 workspace manifest，只排除 per-run identity；新请求仍必须调用 Strong Model。

预期首先改善调用效率和阶段推进：相较 R12 的 L1-L3，动作数、Auditor 调用数、协议拒绝和
`current_time` 重复应下降。任何 HTTP 429/500、超时或 `*_unavailable` 仍单独归类基础设施，零次 RWKV
调用的 case 不计入模型能力分数且禁止进入 State Tune 数据。结果写入独立目录
`run_g1j_zero_state_v7_compatibility_r13`；运行后不得修改评价口径。
