# Round19 标准答案解封前因果综合

## 分析边界

Generated after the frozen E2E-90 run and before reference-answer scoring. Inputs are limited to lifecycle/protocol/action/obligation/witness/proof/state analysis artifacts. No external_passed, passed, verifier observation, final answer, reference answer, or standard answer is read.

## 结论

Round19 的窄化来源规则实现了预登记的安全作用：模型写入同一目标的证明通过数为 `0`；同时仍有 `11` 条只读同目标证明断言通过。因此它没有靠全面禁用同目标证据来筛答案。

但拒绝在 8 题中重复发生 `49` 次，其中 E2E-B01=6, E2E-B17=19, E2E-B18=6, E2E-B25=1, E2E-LH02=3, E2E-M05=5, E2E-M15=3, E2E-M25=6。证明层拒绝是正确的，后续恢复却多次回到相同语义来源，随后由 obligation replan 追加任务并消耗预算。这是新的放大点，而不是应该撤销来源独立性的理由。

## 从后向前的环节归因

1. 终态：0 题完成；5 题持久化过 CriterionEvidence。
2. 义务层：预算耗尽成为 28 题终态根因，较 Round18 增加 8 题。
3. 恢复层：证明反馈触发局部 revision 的案例从 17 增至 19；相同来源拒绝常被重复提交。
4. 证明层：49 次循环来源被正确拒绝；危险来源的证明通过为 0；只读同目标证明仍通过。
5. 绑定层：23 题编译成功、21 题进入证明，但只有 5 题得到持久证据。
6. 协议层：mode contract error 113 次、binding contract error 156 次，弱模型结构化输出仍是主要漏斗。
7. 动作/生产层：36 题经历 action/validation failure，15 题耗尽 action recovery；错误内容仍首先可能由 RWKV 生产动作产生。

## Round18 → Round19 放大量

- 总模型请求：2867 → 2937（+70）。
- obligation saved replans：102 → 112（+10）。
- appended tasks：431 → 461（+30）。
- duplicate task instances：250 → 293（+43）。
- 首次 replan 后事件：7970 → 8586（+616）。

## 下一项假设（未实现）

For deterministic workspace proofs only, cache an observation/proof-failure digest. If evidence, verifier, criterion, and failure fingerprint are unchanged, consume recovery budget without rerunning the same proof/RWKV cross-check and route recovery toward producer correction. External or time-varying observations must remain uncached.

该假设不生成答案、不替换 RWKV 证据选择，也不修改最终输出；它只避免在确定性证据完全未变化时重复执行相同失败路径。

## 终态根因分布

| 根因 | 题数 |
|---|---:|
| action_argument_contract | 15 |
| action_choice_contract | 1 |
| action_recovery_budget_exhausted | 15 |
| goal_parse_contract | 9 |
| obligation_replan_budget_exhausted | 28 |
| obligation_replan_contract | 10 |
| planning_contract | 4 |
| recovery_analysis_contract | 3 |
| run_interrupted_other | 1 |
| unhandled_priority_type | 4 |
