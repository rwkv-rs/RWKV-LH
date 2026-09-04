# Stateful Goal Loop v2 Strong Planner canary R3 结果

- 实际运行：2026-09-01（Asia/Shanghai）。
- 固定结果：completed/external/strict=`0/3`；能力门失败，完整 Ladder 未运行。
- 三例最终状态均为 `running`，slice 原因为 `protocol_rejection_budget_exhausted`；没有把预算或错误改写成 Goal terminal failure。

## 固定计数

| case | Strong 请求 | patch | 13.3B 请求 | choice 接受/拒绝 | action | audit 接受/拒绝 | protocol rejection |
|---|---:|---:|---:|---:|---:|---:|---:|
| L1-FIX01 | 1 | 1 | 25 | 1/22 | 1 | 0/1 | 23 |
| L4-LEDGER01 | 2 | 1 | 47 | 13/10 | 11 | 0/11 | 23 |
| L5-RWKV01 | 2 | 1 | 32 | 9/10 | 4 | 0/4 | 19 |

`results.json.action_count` 与 causal ledger 已分别一致为 `1/11/4`，证明 R2 的空 parallel-outcome 报表错误已修复。

## 架构门

- 每例 `contract_graph_patch_committed=1`；没有 RWKV GoalPlanPatch。
- Strong trace 只有 `contract_plan`；没有 `contract_graph_review_committed`，没有 Strong Reviewer。
- 没有 atom worker outcome；所有 action 都在同一权威 13.3B action State 上推进。
- Audit 使用临时 fork，未 merge WKV；但 16 次 Audit `0/16` 通过，故没有 plan step 可被关闭。
- 只有 RWKV Final + pre-final ready audit 可完成 Goal 的门没有被绕过。

## R2→R3 因果对比

Top-K operation choice 的接线修复有效：action 从 R2 的 `0/2/4` 变为 R3 的 `1/11/4`，L4 能执行 file digest、目录、搜索和读取，L5 能执行目录与 web search。说明 Strong patch→frontier→Selector Top-K→13.3B operation→schema→Harness 已真实跨过。

剩余主阻塞是 Audit：

1. 5 次输出已经正确调用 `audit_decision`，但附带模型生成的 `audit_id/schema_version/repair` 等 kernel-owned 或未注册字段。
2. 多数 observation boundary 错误使用 `ready_for_final`；即使机械删除多余字段，也会被“非 pre-final 禁止 ready_for_final”语义门拒绝。
3. 部分 evidence 使用文件名而不是输入中给出的 Action/Artifact/Revision id，不能通过 Evidence Kernel。
4. 其余输出回到裸旧 audit body、重复字段或长度截断。

因此不能通过放宽 parser 或删除字段来宣称解决；需要同边界的 RWKV audit correction/retry，并将不相交项目 family 的错误→正确轨迹纳入 13.3B state-tuning 数据。

## 发布结论

架构责任已纠正，Strong Planner 不是本轮失败点；但模型能力门仍为 0/3，当前版本不得标记为完成或正式可用。correction corpus 未达 `2000/480`，不得启动正式 tuning。
