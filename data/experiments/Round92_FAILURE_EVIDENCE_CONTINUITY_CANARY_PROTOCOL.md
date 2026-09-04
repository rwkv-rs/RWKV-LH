# Round92 failure-evidence continuity canary preregistration

## 固定条件

- 数据集：与 Round91 相同的 `E2E-B01`、`E2E-B02`、`E2E-B03`、`E2E-H04`。
- Endpoint、模型、sampling、外部验收、Strict 判分口径均不变。
- `max-transitions=200`，`concurrency=1`。
- 运行开始后不修改源码、用例、阈值或判分口径。

## 本轮唯一登记改动

1. Task action/failure 投影增加确定性的 `completion_readiness`：只报告声明的结构证据类型是否已有 Task-owned 成功观察、最新 mutation 后是否已有独立只读观察、collection workset 是否完成。自然语言 `done_when` 仍由 RWKV 判断。
2. 一次较晚的 operation failure 不删除较早的成功 Attempt。若上述结构前置条件已满足，RWKV 可以在 failure recovery 中显式选择 `lh_task_done`；Controller 不自动完成。
3. 简单格式转换层接入 `function_args` 参数容器，以及所有语义字段均由 RWKV 显式给出的扁平 direct Task operation。原始 payload 和非语义注释完整审计；缺少 operation/task_id/operation arguments 时仍拒绝。

## 冻结摘要

- `rwkv_lh/schema.py`: `2c270ef7ef149d8a40bdded5e6d763763aeedc6d378aa083d277164641d6b200`
- `rwkv_lh/model.py`: `14f34955f0dcbf047a1a4d98cef9663a3cae06353ead3fa19f14940bb4dc6456`
- `rwkv_lh/model_io.py`: `00ef66f28cc0a086a378cdfd2ca5d210df0fe248bfedecdecfbf12b1c9e73de6`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- `rwkv_lh/controller.py`: `04492b3a17342bb62b3b0120fc83282aad0ab268ce29f49137a9d1fd605d198b`
- `rwkv_lh/harness.py`: `691e610af6d4a3dbcc558bfdd97570933b736c5ce98240d5c8985423063a2021`
- `rwkv_lh/task_graph.py`: `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner: `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- 离线回归：`91 passed`。

## 运行命令

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round92_failure_evidence_continuity_canary \
  --max-transitions 200 --concurrency 1
```

## 事后检查

- 逐调用定位每题第一次偏离，不只读取聚合报告。
- 固定记录 Strict / Agent / External、FP/FN、模型请求数。
- 检查四题终态回答非空，且答案与 RWKV Final lane 原始输出完全一致。
- 检查 Controller 未根据外部验收或自然语言 `done_when` 自动选择 `lh_task_done`。
- 检查 `function_args` 只搬运已有显式语义字段，raw/normalized payload 均可追溯。
