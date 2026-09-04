# Round94 B02 Goal correction transaction preregistration

- 固定用例、endpoint、模型、sampling、外部验收与 Strict 口径：`E2E-B02`，全部沿用 Round93。
- `max-transitions=200`，`concurrency=1`。
- 唯一结构改动：Goal runtime 已接受的 semantic function 在后续结构纠错中锁定；`lh_tasks` 结构失败只能纠正为 `lh_tasks`。`after` 契约明确允许已显示既有 Task ref或同批更早 local key，并拒绝 Attempt/artifact ref。
- 不映射、不删除、不补充依赖；纠正后的完整 Task proposal 仍由 RWKV产生。
- 冻结 `model_io.py`：`884a4defe27b73714a56074a4dd77890be7c66d89db07b5e0bf330b83054737e`。
- 冻结 `controller.py`：`d4432c5dbfb51ecbe8ef8ccc95f64aee6d086e050518110aadde4a938d1206c0`。
- 离线回归：`93 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B02 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round94_b02_goal_correction_transaction \
  --max-transitions 200 --concurrency 1
```

逐调用检查：Goal 第二批 Task 原始决定、错误依赖、correction function 是否保持、Task 是否真实执行、report.json 外部验收、FP/FN、Final 非空与 raw equality。运行中不修改源码或口径。
