# Round99 B02 tool-applicability preregistration

- 固定 `E2E-B02`、endpoint、模型、sampling、外部验收、Strict、`max-transitions=200`、`concurrency=1`。
- 相对 Round98：unchanged-action rejection携带统一 completion/objective/subject/workspace-state；read_json明确不适用于已由read_file观察为plain/key=value的内容；write_json明确可从可见依赖值创建完整JSON，值仍全由RWKV给出。
- Controller不选operation、不计算业务值、不生成JSON、不读取外部验收。
- controller `f11506ad6dbd6cffa5f0c3669480db5fb379ab6bb5eda449a79d959423bb0573`
- harness `78289e1c1f9aab5cc16047ec0826bcd42256eeb899ade5cc304537b3c13201cf`
- 离线 `96 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B02 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round99_b02_tool_applicability \
  --max-transitions 200 --concurrency 1
```

检查每个RWKV operation/value、真实Attempt、report.json、Strict/FP/FN和Final raw equality。运行中不改源码或口径。
