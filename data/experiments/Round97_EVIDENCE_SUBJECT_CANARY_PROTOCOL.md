# Round97 evidence-subject four-case canary preregistration

## 固定条件

- 用例：`E2E-B01`、`E2E-B02`、`E2E-B03`、`E2E-H04`。
- endpoint、模型、sampling、外部验收、Strict 口径不变。
- `max-transitions=200`，`concurrency=1`。

## 登记改动

- Goal Task proposal 新增必填 `evidence_subject`，完全由 RWKV选择。
- file/mutation/listing 使用精确 workspace-relative path；command/outcome 使用精确 operation name。
- Controller只匹配 Task-owned Attempt 的明确 action subject，不解析 objective/done_when，不映射、不补目标。
- 历史状态缺少该字段时可恢复；所有新模型提案必须显式提供。

## 冻结

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `3790da4eb8f691793104ffa1de11bff46738730519529b970960aba31c9d5042`
- model_io `c142e1b02cfc2e375fc91a0cc7be20d4c8563355f94f57f1b61a69a3089f6966`
- controller `9549ce201afbf64f11297d87acb6f7a1d2d4a26e909f88299bde27fa00322016`
- 离线回归 `95 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round97_evidence_subject_canary \
  --max-transitions 200 --concurrency 1
```

逐题检查 Task proposal、subject绑定、Attempt、FP/FN、Strict 和 Final raw equality。运行中不修改源码或口径。
