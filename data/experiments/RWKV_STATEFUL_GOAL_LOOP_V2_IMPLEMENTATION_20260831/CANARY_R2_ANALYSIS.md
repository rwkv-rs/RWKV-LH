# Stateful Goal Loop v2 Strong Planner canary R2 分析

- 固定结果：completed/external/strict=`0/3`；不得覆盖，也不得据此运行完整 Ladder。
- 计划协议结论：每例均有且只有一个 `contract_graph_patch_committed`；Strong 请求 phase 全部为 `contract_plan`，没有 Strong Reviewer。L5 的第二次请求是首次 Strong 语义响应被拒后的同 phase repair，不是 Reviewer。
- 因此，R2 没有出现 `ContractGraphPatch`/Strong Planner 格式失败；将本轮失败称为 PlanPatch 格式问题是不正确的。

## 因果分层

| case | Strong 请求 | patch | 13.3B 请求 | Top-K choice 拒绝 | choice 接受 | Harness action | Audit 拒绝 | 因果账本 protocol rejection |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L1-FIX01 | 1 | 1 | 12 | 12 | 0 | 0 | 0 | 12 |
| L4-LEDGER01 | 1 | 1 | 25 | 19 | 2 | 2 | 2 | 21 |
| L5-RWKV01 | 2 | 1 | 29 | 17 | 4 | 4 | 4 | 21 |

最早系统性偏离发生在 Strong patch 已提交以后：

1. 新增 Top-K 实现要求 13.3B 输出 `select_tool(params.name)`，但现有 Executor state 自然输出实际候选调用，例如 `{"function":"list_directory","params":{"path":"."}}` 或 `{"function":"current_time"}`。这些输出在 operation 语义上可判定，但被错误的 meta wrapper 拒绝。
2. 重复拒绝污染了 Selector/Executor 后续状态，候选逐渐退化到 `current_time/file_digest/date_diff` 等无关操作。
3. L4/L5 偶尔跨过 choice 并执行 action 后，新 Audit Fork 没有公开独立 audit schema，却要求 Executor profile 猜裸 Audit body；其输出回落到旧工具/selector call 或无限重复 evidence，4/4、2/2 全部格式拒绝。
4. `results.json` 中 action/protocol rejection 的 `0` 还是一个报表分支错误：Stateful 使用 `contract_graph` strategy 时被误按 parallel atom outcome 汇总。权威 causal ledger 明确记录了上表的 action 与 rejection；该报表错误不改变 0/3 判定。

## 整改边界

- 保留 Strong Planner 和现有 `ContractGraphPatch`，不新增 RWKV PlanPatch。
- Top-K choice 只提取 13.3B 在冻结候选内明确生成的 operation；schema 公开前生成的参数全部丢弃，随后公开唯一 schema 并重新生成参数。该选择不授权执行。
- Audit Fork 公开唯一 `audit_decision` 闭合 schema；模型只生成 verdict、step、完成布尔值、证据 refs、gaps 和 reason，audit id/schema version 由 kernel 绑定。
- R2 的 Ladder 原始错误只能登记为 holdout failure cluster，不得直接导出训练；训练行必须来自不相交项目 family 的干净 replay，并通过 Harness/pytest/公开 verifier。
- 报表在 Stateful 模式直接读取唯一主 State，不再读取空的 parallel outcomes。

## R2 结论

R2 证明的是新接线中的 13.3B operation-choice 与 Audit 协议不兼容，不是 Strong Planner 退化，也不是 `ContractGraphPatch` 格式不匹配。修复后必须登记新输出目录、新 Planner cache 和新实现哈希，再运行同一固定三例 R3。
