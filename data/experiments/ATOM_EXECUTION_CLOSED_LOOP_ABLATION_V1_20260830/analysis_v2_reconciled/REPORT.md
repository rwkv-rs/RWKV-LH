# AtomExecutionContract 全链路闭环消融 V1 证据重连结果

V1 固定分析器错误地假设每个 consumed 非-final selection 都必须直接产生 ActionRecord；协议拒绝后的 retry 是一对多 decision 链，且旧 outcome 投影遗漏 decision id。这里仅从原始 per-atom SQLite 因果状态恢复 join，未改指标、阈值、模型输出或原 audit。

| 指标 | A legacy view | B contract progress |
|---|---:|---:|
| strict / external / completed | 0 / 0 / 0 | 0 / 0 / 0 |
| contract-advancing 成功动作 | 61 | 136 |
| successful mutation rate | 0.461538 | 0.859649 |
| 完整写根覆盖率 | 0.333333 | 0.666667 |
| transaction integrity error | 39 | 30 |
| raw generation | 735 | 979 |
| reconciled join failures | 176 | 404 |
| remaining contract drift | 0 | 0 |

- A/B 有效：`True` / `True`。
- 闭环有效：`False`。
- State tuning 决策：`construct_leakage_checked_approximately_2k_targeted_state_data`。
- `criteria_changed=false`; `raw_rwkv_output_mutated=false`; 原始 A/B 目录只读保留。
