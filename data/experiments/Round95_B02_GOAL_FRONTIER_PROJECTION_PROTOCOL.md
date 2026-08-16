# Round95 B02 Goal-frontier projection preregistration

- 固定 `E2E-B02`、模型、endpoint、sampling、外部验收、Strict 口径、`max-transitions=200`、`concurrency=1`。
- 相对 Round94 的唯一改动：
  - `task_results` 将当前 Task 前沿完成与 Goal 完成明确分离；
  - 每次紧邻重放 immutable Goal；
  - 移除已淘汰的旧 task_step rejection 投影；
  - `lh_tasks` 要求覆盖全部剩余工作；
  - `lh_goal_done` schema 明确 params `{}`，当前前沿完成不等于 Goal 完成。
- Controller 不解析 Goal clause、不自动建 Task、不自动完成、不读取外部验收。
- 冻结 `model_io.py`：`84aa954b0cc72b29fa1f66d3fff0c58bd02fc8b9150cb33a4e31e65e3547cb02`。
- 冻结 `controller.py`：`320a2f73eaec49332c3d7bd79b4422fe60e144f69ea7cd1284f761c880d76c2d`。
- 离线回归：`94 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B02 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round95_b02_goal_frontier_projection \
  --max-transitions 200 --concurrency 1
```

逐调用检查 Goal 回流、Task batch、真实 write/read、FP/FN、Final raw equality。运行中不改源码或口径。
