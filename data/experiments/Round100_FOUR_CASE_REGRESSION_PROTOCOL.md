# Round100 four-case regression preregistration

- 固定用例：B01/B02/B03/H04；endpoint、模型、sampling、Strict与外部验收不变。
- `max-transitions=200`，`concurrency=1`。
- 源码冻结：schema `49eebf20...d29763`，model `3790da4e...d5042`，model_io `a50ed2ac...a533`，controller `f11506ad...0573`，harness `78289e1c...01cf`，task_graph `517cd37e...b1f45`，runner `2df02384...d6960`。
- 离线回归 `96 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round100_four_case_regression \
  --max-transitions 200 --concurrency 1
```

四题逐调用检查；记录Strict/FP/FN与Final raw equality。运行中不修改源码或口径。
