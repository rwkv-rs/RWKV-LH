# AtomExecutionContract 全链路闭环消融 V1 结果

| 指标 | A legacy view | B contract progress |
|---|---:|---:|
| strict pass | 0 | 0 |
| external pass | 0 | 0 |
| agent completed | 0 | 0 |
| 过早 final 拒绝 | 0 | 0 |
| contract-advancing 成功动作 | 61 | 136 |
| mutate atom | 39 | 57 |
| 完整写根覆盖率 | 0.333333 | 0.666667 |
| transaction integrity error | 39 | 30 |
| Selector ABSTAIN | 35 | 8 |
| 合同漂移 | 176 | 404 |
| 原始输出事件 | 735 | 979 |

- A 有效：`False`；B 有效：`False`。
- 闭环有效：`False`。
- State tuning 决策：`invalid_experiment_no_training_decision`。
- 所有比率、阈值和判定均来自运行前冻结的预注册；未修改 RWKV 原始输出。
