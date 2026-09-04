# RWKV-LH × ECRA Contract Graph v2 route canary protocol r8

状态：运行前冻结；沿用 `PROTOCOL.md` 的数据集、7 个 case、模型、并发、预算、
expected、指标算法和全部门槛。

日期：2026-08-25

## 登记整改

R7 已证明单步首工具 7/7，但跨 atom 路由、隐私 Gate 覆盖和 synthetic route
完成审核未通过。R8 只登记以下三个全局工程整改，不修改 frozen answer：

1. dependency handoff 只公开 committed observed content、Evidence Record 和 artifact
   identity；不公开 predecessor operation/arguments，消除上一动作对下一 atom 的接口污染；
2. Network/Safety Gate 是调用授权的唯一 authority。Planner 只表达 evidence need，
   不预授权、不预拒绝；Worker 收到 typed rejection 后不得改写、重试或绕过；
3. `rwkv-lh.ecra-route-goal.v4` 把 benchmark 明示的 route outcome 作为强制验收合同，
   synthetic backend 提交 content-addressed `synthetic-route-completion.v1` 证据，
   Reviewer 不得把 route-only 测试加强为普通事实质量测试。

输出目录：`variant_b_contract_graph_r8`。其余命令参数与 `PROTOCOL.md` 相同。
