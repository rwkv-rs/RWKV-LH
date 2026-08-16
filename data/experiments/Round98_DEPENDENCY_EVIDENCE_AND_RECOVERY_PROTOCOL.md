# Round98 dependency-evidence and recovery preregistration

- 固定用例：`E2E-B02`、`E2E-B03`。
- endpoint、模型、sampling、外部验收、Strict 口径不变；`max-transitions=200`，`concurrency=1`。
- 登记差异：
  1. 精确 subject/类型相同的已 committed 依赖闭包 Attempt 可用于当前 Task结构证据；无依赖、未完成依赖或 subject不同不可复用。
  2. completion/recovery 紧邻携带 Task objective、done_when、evidence kind/subject。
  3. 接入 `top-level operation + operation_arguments(actual args)` 显式 flattened 外壳。
- Controller不解析 Task文本、不映射 subject、不选择 operation、不读取外部验收。
- 冻结 model_io `a50ed2ac82207df906b9c24dd21018de9fa6afa0fd2a421b58a143d806b8a533`。
- 冻结 controller `5b29c23b10baaadfb025f3228e260a77d8547f9d86af45d225433b7f8087562d`。
- 离线回归 `96 passed`。

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B02 --case E2E-B03 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round98_dependency_evidence_and_recovery \
  --max-transitions 200 --concurrency 1
```

逐调用检查依赖证据来源、subject、实际写入、FP/FN、Strict 与 Final raw equality。运行中不改源码或口径。
