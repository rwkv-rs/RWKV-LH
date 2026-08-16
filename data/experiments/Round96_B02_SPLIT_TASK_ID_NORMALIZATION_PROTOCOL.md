# Round96 B02 split-task-id normalization preregistration

- 固定 `E2E-B02`、模型、endpoint、sampling、外部验收、Strict 口径、`max-transitions=200`、`concurrency=1`。
- 相对 Round95 唯一改动：简单转换层把 RWKV 已显式给出的 top-level `task_id` 搬入 `lh_task_call.params`；operation 和 operation_args 必须已在 params。冲突 task_id、缺 operation 或缺 args 继续拒绝。
- normalizer version：`model-call-envelope.v5`。
- 冻结 `model_io.py`：`e9bcd814078a7656d76365d185edee0926c650debfc43557fed3ed3a0520e58b`。
- controller 沿用 Round95：`320a2f73eaec49332c3d7bd79b4422fe60e144f69ea7cd1284f761c880d76c2d`。
- 离线回归：`94 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B02 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round96_b02_split_task_id_normalization \
  --max-transitions 200 --concurrency 1
```

检查 raw/normalized trace、T2真实 Attempt、report.json 外部验收、FP/FN和 Final raw equality。运行中不改源码或口径。
