# R12 zero-State 混合有效诊断

日期：2026-09-02。R12 使用预登记的固定五例、`concurrency=1`、`max_transitions=120` 和三路
`zero` profile。L1-L3 完整进入 G1J RWKV 链路且无 Strong Model 基础设施失败，可作为整改前的有效诊断
基线；L4-L5 在首次 `goal_plan` 被 HTTP 429 截断，零次 RWKV 调用，必须单独标记基础设施无效。

有效三例结果：

- L1：59 actions、207 model requests、41 protocol rejections，120 transitions 后仍为 `running`；
- L2：46 actions、157 model requests、33 protocol rejections，完成过一个阶段并调用一次 Strong Stage
  Checker，但 120 transitions 后仍为 `running`；
- L3：58 actions、221 model requests、41 protocol rejections，120 transitions 后仍为 `running`。

最早可复核的全链路缺陷在 L1：Strong Planner 的首个 step 为只读检查，`write_roots=[]`，但 Controller
仍向 Selector 暴露工作区写工具；Selector 在只读所需文件尚未全部观察时选出 `write_file`，Executor 随即
修改 `pricing.py`。之后 Auditor 多次用不覆盖 `verify_project.py` 的证据声称 step 完成，内核正确拒绝。
当累计动作超过八条，原来的 latest-eight Audit 投影又把早期相关证据挤出窗口，Selector/Auditor 进入大量
`current_time` 与 repair 循环。

因此 R12 同时证明三类问题：

1. 工程问题：只读 step 缺少机械写权限门；Audit 窗口没有保留覆盖 step roots 的证据；
2. Selector 能力问题：持久轨迹中反复选择与当前工程 step 无关的 `current_time`；
3. Auditor 能力问题：六字段协议、证据引用和 step-complete 判断不稳定。

L1-L3 可用于生成分角色纠错候选，但必须先修复工程根因；L4-L5 不得进入任何 State Tune 数据。R12
不是最终 zero-State 能力分数，整改后必须以同一数据、参数和评价口径重跑完整五例。
