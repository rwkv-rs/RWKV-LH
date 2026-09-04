# RWKV-LH × ECRA Contract Graph v2 route canary protocol r5

状态：运行前冻结；沿用 r4 全部输入与评价口径

唯一整改：`network_audit.workspace_revision` 由 audit 内容摘要生成，不再包含
全局 causal-event 数。相同 atom operation results 必须产生相同 capsule evidence ID，
使刚提交的 Review 能在下一调度循环被消费并释放 finalizer。

输出目录：`variant_b_contract_graph_r5`。其余命令参数与 `PROTOCOL.md` 相同。
