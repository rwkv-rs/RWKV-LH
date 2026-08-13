# Round20 未变化确定性证明恢复审计

## 边界

Score-independent audit over frozen Round20 lifecycle event logs only. No reference answer, external verifier result, delivered answer, acceptance label, or standard-answer comparison is read.

## 结果

- 整案抑制：`19` 次 / `12` 题。
- 被整案拒绝的候选任务：`77` 个，其中真正冲突任务 `38` 个。
- 抑制后仍成功保存的新重规划：`4` 次；其中语义已改变的为 `4` 次。
- 同一语义再次放行：`0` 次；其中工作区已变化 `0` 次。

## 预注册不变量

| 检查 | 结果 |
|---|---:|
| all_have_nonempty_workspace_digest | PASS |
| all_have_conflicts | PASS |
| all_conflicts_are_proposal_members | PASS |
| all_signatures_match_frozen_projection | PASS |
| all_reject_whole_proposal | PASS |
| no_same_generation_tasks_materialized | PASS |
| all_eligible_next_capsules_carry_exact_recovery_feedback | PASS |
| no_capsule_after_budget_exhaustion | PASS |
| same_semantic_reallowed_only_after_workspace_change | PASS |

## 每题触发次数

| 题目 | 抑制次数 |
|---|---:|
| E2E-B08 | 3 |
| E2E-B15 | 2 |
| E2E-B20 | 1 |
| E2E-B26 | 1 |
| E2E-B29 | 1 |
| E2E-H09 | 3 |
| E2E-M08 | 1 |
| E2E-M11 | 1 |
| E2E-M16 | 2 |
| E2E-M18 | 1 |
| E2E-M21 | 2 |
| E2E-M29 | 1 |

整案抑制只拒绝 RWKV 再次提交的同语义 proposal；控制器没有选取其中的部分任务，也没有生成替代任务、验收条件、参数、答案或最终输出。
