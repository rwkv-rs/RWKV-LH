# RWKV-LH × ECRA Contract Graph v2 route Canary protocol R9

状态：运行前冻结；沿用 R8 的数据、7 个 case、顺序、模型、并发、预算、expected、指标和门槛。

R9 只登记 R8 原始 trace 发现的三个全局工程修复：

1. `semantic_review` 与 `command_succeeded` 可以描述无文件 target 的公开 action/result 关系；具名
   `command_succeeded.expected` 可绑定任意已执行 operation，而非只绑定 shell command；
2. initial Contract Plan 的 structured-output schema 固定 `new_obligations.minItems=1`、
   `new_nodes.minItems=2`；finalizer-only replacement 固定一个 node；
3. `failed_or_unavailable_case_count` 统计所有 `run_status != completed` 的 case。

不修改 Goal wrapper、RWKV prompt、工具顺序、数据集、case expected 或阈值。R9 仍失败时不得运行
route120；模型选择错误进入 state-tuning 数据，不得以 Controller case 特判修复。

输出目录固定为 `variant_b_contract_graph_r9`，命令与 R8 相同，仅替换输出目录。

