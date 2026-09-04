# Round93 B02 completion-decision canary preregistration

- 固定用例：`E2E-B02`。
- 模型、endpoint、sampling、外部验收和 Strict 口径不变。
- `max-transitions=200`，`concurrency=1`。
- 相对 Round92 唯一改动：同一份确定性 completion-readiness 投影在 action、failure、operation rejection、protocol rejection 和 recovery capsule 中连续存在；投影紧邻携带 RWKV 原始 `task_done_when` 和条件式调用说明。Controller 不解释 `done_when`、不自动完成、不选择操作。
- 冻结 controller：`4fdc284f2130c67096b36cd58f18dfa8846de9f18e86ed0bb59e6cdb559b26a3`。
- 其余源码 hash 沿用 Round92；离线回归 `92 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B02 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round93_b02_completion_decision_canary \
  --max-transitions 200 --concurrency 1
```

逐调用检查：首次成功 read 后的选择、失败后的选择、是否显式 `lh_task_done`、Goal 是否继续扩展、report.json 是否真实产生、Final 是否非空且等于 RWKV 原始输出。运行中不修改任何源码或口径。
