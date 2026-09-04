# Current direct-Harness Selector ECRA S23 v1

- 来源、摘要、生成命令、标签分布和历史基线见 `manifest.json`。
- 用途：按当前 `LongHorizonModel` 双 state 架构评估 2.9B Selector；不是 Planner 原子目标数据。
- 每个 continuation 只含 operation/success/outcome/complete/truncated 的紧凑投影；不含参数 schema、完整结果、Executor 文本。
- 标签：冻结 ECRA 期望序列及完成后的 `final_answer`；只有历史动作前缀正确时才构造后续决策点。
- `historical_selected_operation` 是同一决策位置的旧 13.3B 直接路由结果，用作保留基线，不被当作真值。
