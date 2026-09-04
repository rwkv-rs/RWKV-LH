# RWKV-LH × ECRA Contract Graph v2 route canary protocol r3

状态：运行前冻结；沿用 r2 全部输入与评价口径

唯一整改：当 Harness 注册了网络能力时，Controller 从已提交的 atom operation
result 机械生成 `network_audit` capsule，使 Reviewer 能复核零网络、允许出站、
策略拒绝和后端未执行。该 capsule 不含查询参数，不由 RWKV 或 Strong Planner
生成，也不改变动作选择、参数或执行结果。

输出目录：`variant_b_contract_graph_r3`。其余命令参数与 `PROTOCOL.md` 相同。
