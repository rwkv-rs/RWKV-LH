# Round20 标准答案解封前因果综合

## 分析边界

Generated after the frozen Round20 E2E-90 run and before standard-answer scoring. Inputs are limited to lifecycle, protocol, action, obligation, witness, proof, state, and suppression analysis. No external_passed, strict passed label, verifier observation, delivered answer, reference answer, or standard answer is read.

## 核心结论

The pre-registered gate fired 19 times in 12 cases, rejected every proposal as an indivisible RWKV decision, materialized no task from a rejected generation, and carried exact feedback into every eligible next replan. Four later RWKV proposals with distinct task semantics were accepted.

Compared with Round19, saved obligation replans fell by 21, appended tasks by 10, duplicate task instances by 18, repeated semantic proposals by 10, and events after the first saved replan by 289.

Whole-proposal atomicity also rejected 39 non-conflicting tasks that shared a mixed proposal with a conflicting task. Total model requests still rose by 23, model contract errors rose by 60, and 25 cases still exhausted the obligation budget. The gate reduces one recovery loop but does not fix producer correctness or weak-model protocol failures.

## 从后向前的阶段漏斗（Round19 → Round20）

- 系统终态完成：0 → 1。这里尚未判断答案是否正确。
- CriterionEvidence 持久化：5 → 6。
- 证明通过题：5 → 6；通过断言仍全部是只读同目标快照。
- binding 编译成功题：23 → 28。
- mode committed 题：30 → 37。
- selection started 题：33 → 41。

## 恢复放大效应

- saved replans：112 → 91 （-21）。
- appended tasks：461 → 451 （-10）。
- duplicate task instances：293 → 275（-18）。
- repeated semantic proposals：19 → 9（-10）。
- 总模型请求：2937 → 2960（+23）。

## 整案抑制审计

19 次抑制覆盖 12 题，共拒绝 77 个候选任务；38 个与冻结失败语义冲突，另有 39 个位于混合 proposal 中而随整案拒绝。全部审计不变量通过；控制器没有从 proposal 中筛选任务。

## 完整因果链

1. RWKV selects and executes producer actions, which can write the checked workspace target.
2. RWKV later selects or binds proof sources; circular model-written same-target lineage is rejected.
3. RWKV may propose a verifier task with exactly the failed task semantics while the workspace is unchanged.
4. Round20 rejects that complete proposal and returns the conflict fingerprint to the next RWKV replan.
5. Some replans become semantically distinct, but mixed proposals lose unrelated tasks and protocol errors continue.
6. Obligation budget exhaustion remains the largest terminal cause; completion correctness is intentionally unknown until scoring.

## 终态根因分布

| 根因 | 题数 |
|---|---:|
| action_argument_contract | 15 |
| action_choice_contract | 1 |
| action_recovery_budget_exhausted | 16 |
| goal_parse_contract | 5 |
| obligation_replan_budget_exhausted | 27 |
| obligation_replan_contract | 10 |
| planning_contract | 7 |
| recovery_analysis_contract | 1 |
| run_interrupted_other | 1 |
| unhandled_priority_type | 6 |
| witness_handle_binding_contract | 1 |

## 解封后首先验证的问题

Determine after standard scoring whether the single system-completed case is a true completion or a false positive, and attribute any incorrect artifact to its first RWKV producer action before changing recovery structure. If mixed-proposal loss is material, ask RWKV for one atomic obligation decision per response rather than letting the controller select tasks out of a list.
