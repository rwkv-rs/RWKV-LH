# Round19 标准答案后逐环节归因

## 边界

Post-run only. This joins frozen external acceptance/reference observations to the already frozen lifecycle analysis. It never participates in RWKV generation, witness selection, proof, completion, or final-output delivery. Mutation attribution is an explicit inference from matching action-selected target paths and external-check paths.

## 总体结果

- External 正确/错误：21 / 69。
- Strict / Completed / FP / FN：0 / 0 / 0 / 21。
- 所有 21 个 External 正确案例都被 controller completion 边界阻断。

## 正确案例为什么没有完成

| 环节 | External 正确题到达数 | External 错误题到达数 |
|---|---:|---:|
| run_created | 21 | 60 |
| goal_parsed | 21 | 60 |
| plan_saved | 21 | 56 |
| action_returned | 21 | 56 |
| task_completed | 21 | 51 |
| witness_selection_started | 10 | 23 |
| witness_selection_compiled | 7 | 16 |
| criterion_assertions_evaluated | 7 | 14 |
| witness_binding_evaluated | 7 | 14 |
| criterion_evidence_persisted | 0 | 0 |
| run_completed | 0 | 0 |

21 个正确案例中只有到达独立证据并覆盖全部 Goal criterion 的案例才有资格完成。本轮没有任何案例走到 run_completed；这说明当前主要 FN 不是产物执行失败，而是 witness/证明/义务恢复漏斗。

## 错误案例从哪里开始

下表是后验归因入口。`rwkv_producer_mutation` 只在冻结的 RWKV action_selected 对外部检查目标执行可直接判定为错误的 write_json 时记入；其余按生命周期终态层归类。

| 归因层 | 题数 |
|---|---:|
| rwkv_action_or_recovery | 28 |
| rwkv_producer_mutation | 22 |
| controller_completion_false_negative | 21 |
| goal_protocol | 9 |
| obligation_recovery | 4 |
| planning_protocol | 4 |
| runtime_or_recovery | 2 |

## 来源独立性规则

规则共在 8 题拒绝 49 次：External 正确题为 E2E-B01；External 错误题为 E2E-B17, E2E-B18, E2E-B25, E2E-LH02, E2E-M05, E2E-M15, E2E-M25。

危险的模型写入同目标证明通过为 0；只读同目标证明通过 11 条。B01 的产物已经正确，但 RWKV 仍选择非独立的模型写入来源，属于正确产物上的证据/完成假阴性；其余 7 题产物本身错误，拒绝避免了假阳性。

## 正确值被后续覆盖

可直接从 write_json 与 json_equals 目标比对确认的案例：E2E-B02, E2E-B17, E2E-B18, E2E-LH02, E2E-M07, E2E-M21。B17 中 RWKV 先写 Ada/Zoe=2，随后覆盖为 Alice/Bob/Charlie=3；后续只读和证据重试放大了该生产错误。

## 逐题证据

完整 90 题的 failed check、匹配目标写操作、首个错误写入、到达环节、终态根因、证明/证据次数、来源拒绝和 obligation 放大量见 `poststandard_stage_attribution.json`。
