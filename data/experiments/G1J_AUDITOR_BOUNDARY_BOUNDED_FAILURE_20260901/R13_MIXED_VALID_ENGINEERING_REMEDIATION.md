# R13 工程整改后混合有效结果

日期：2026-09-02。R13 保持固定参数与三路 `zero` profile。L3、L4 完整进入 RWKV 且无 Strong Model
或本地推理基础设施失败；L1、L2 首个 `goal_plan` HTTP 429，零次 RWKV 调用；L5 进入 RWKV 后本地 SSH
隧道断开，因此需分别处理。

有效结果：

- L3：58 actions、206 model requests、35 protocol rejections；只读权限门把 R12 的 41 次
  `patch_json` 降到 0，但 Selector 连续选择 `list_directory` 62 次，120 transitions 后仍未完成；
- L4：60 actions、178 model requests、4 protocol rejections；Selector 选择 `current_time` 39 次，且没有
  `read_file`，120 transitions 后仍未完成。

工程整改的因果效果可确认：只读 step 的越权 workspace mutation 已消失，L3 Auditor rejected 从 140 降到
118、protocol rejections 从 41 降到 35。剩余最早失败层是 Selector 的持续轨迹工具切换，而非格式：L4
只有 4 次协议拒绝但仍因无关工具耗尽预算。

L5 在隧道中断前有 2 个 `web_search` actions、2 个有效 Audit、1 次 Strong Stage Review；Stage Checker 返回
repair，Strong Planner 前两轮 correction patch 分别因 add/replace id 冲突和复用现有 id 被本地语义校验
拒绝，后续提交新 patch。此后本地 29713 隧道消失，连续 8 次 `Connection refused`，以
`model_transport_unavailable` yield；该基础设施终点不能用于评价后续 RWKV 能力。

R14 仅重跑 R13 中无效的 L1、L2、L5；L3/L4 保留为同一代码版本的有效 zero-State 样本。所有无 RWKV
调用或隧道失败后的记录禁止进入 State Tune 数据。
