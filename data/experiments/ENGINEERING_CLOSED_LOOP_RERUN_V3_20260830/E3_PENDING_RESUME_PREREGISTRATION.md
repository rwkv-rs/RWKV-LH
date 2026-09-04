# E3 生产 pending-resume 闭环预注册

登记时间：2026-08-30（Asia/Shanghai），在 E3 任何模型调用之前冻结。

## 目的与单一改变量

E2 full 在 10 个真实 Ladder 用例中保留了 1 个未解决的
`supervisor_call_pending`。事件证据表明，Controller 已正确持久化可恢复边界，正式
proactive worker 也只会按 `unresolved_supervisor_pending` 投影恢复；缺口是一次性 E2E
benchmark 在第一次可恢复中断后就结束，没有复现产品调度的 resume 语义。

E3 只增加 benchmark 内显式、有限的生产等价恢复：每个用例最多 2 次，只在当前状态为
`interrupted` 且存在尚未 resolved/consumed 的 supervisor pending 时重新进入 Controller。
历史已解决 pending、证据停滞、预算耗尽和其他终止原因均不得触发。Planner、Reviewer、
2.9B Selector、13.3B Executor、提示词、工具菜单、状态、采样、并发和阈值保持不变。

## 固定范围与顺序

- canary：只运行 `AGENT-LADDER-L2-REPAIR01`；
- full：固定 Ladder10 原顺序与原 acceptance；
- canary 通过工程门后才允许 full；
- canary/full 输出分别为 `run_e3_pending_resume_canary_v1` 和
  `run_e3_pending_resume_full_v1`，存在即拒绝覆盖；
- 物理 GPU0；远端实验 Executor `18075`、本地 tunnel `29613`、本地 Selector
  `29621`；产品 `18070` 必须全程健康；并发 3、每次 Controller re-entry
  `max_transitions=300`；
- Selector：`S66-M1 + zero state`，只选择 operation；
- Executor：13.3B G3/G6 固定按任务绑定，run 内禁止 profile switch；
- RWKV 原始输出 append-first，严禁修改、删除、隐藏、截断、重排、修复或替换。

## 固定工程门

1. case、arm、执行 freeze、Planner/Selector/Executor 身份完全一致；
2. raw generation 与 runner 计数相等且 SHA/字节数/原文零漂移；
3. selection→decision→action→outcome、contract digest、child action 投影零漂移；
4. finalizer 依赖覆盖、final-presentation 验收、exclusive 隔离、来源判定、child action
   幂等和 State Router child 投影继续通过既有 7/7 故障矩阵；
5. 终态当前未解决 supervisor pending 为 0；已解决 pending 不得重新引入；
6. 如真实运行出现 pending，则必须存在同 `pending_id` 的 resolution，且恢复次数不超过 2；
7. 产品 18070 保留，实验 18075/29621 释放，凭据值不落盘；
8. strict/external/completed 与 Ladder ceiling 只作能力诊断，不替代工程门。

canary 未通过时不得启动 full。full 未通过时保留失败证据并修复根因，不改变评价口径。

## 数据隔离与后续训练

沿用 `rwkv_agent_capability_ladder_v1` 固定 holdout，任务 SHA-256
`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`，acceptance
SHA-256 `f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
E3 结束前不以该 holdout 优化任何 state。后续约 2K state 数据必须使用不同实体与路径，
并按已登记 `byte-5gram-cosine-v1` 保持最大相似度严格小于 0.95。
