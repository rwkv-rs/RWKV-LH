# State Router 阶段 0

阶段 0 已完成固定 2k 数据、三方案真实消融和项目内本地推理入口。当前入选方案是：

```text
本地 /home/chase/GitHub/vllm-rwkv
  -> RWKV7ForCausalLM 最后一层 WKV state
  -> 4096 维冻结统计
  -> 仅在 train 拟合的 256 维 PCA
  -> 校准多头 MLP
  -> 路由建议 / State Profile / ABSTAIN
```

它仍是离线/手动调用边界，不接主 Harness、不裁剪工具菜单，也不改变 Network Gate 的授权结果。
阶段 1 Shadow 模式不属于本次实现。

## 固定边界

- 输入合同：`rwkv-lh.state-router-input.v1`；fresh/continuation 使用同一结构。
- 引擎：只从本地 `/home/chase/GitHub/vllm-rwkv` 导入，固定 clean commit
  `67f0c5996c50dca0ad779da545cb491527de988f`。
- 模型前向：本地 `vllm.model_executor.models.rwkv7.RWKV7ForCausalLM`、本地 CUDA ops 和
  标准权重加载；不使用远端服务，也不使用 RWKV-FLA/Transformers 模型前向。
- tokenizer：本地引擎 `RWKVTokenizer`；BOS/EOS/PAD=0、左截断、最大 1024 token；按真实
  token 长度分桶，不让 padding 改变 recurrent state。
- 分类头：context mode、execution phase、route family、network recommendation。
- 回退：route 置信度、margin、OOD 或分类头冲突任一失败时输出 `abstain + S_base`。
- 权威边界：EvidenceState 与 PolicyState 来自 Controller/Gate；Summary 和 Router 预测不能
  覆盖机械状态。

完整引擎、模型、数据、训练参数、校准方法和门槛见
[`PREREGISTRATION.md`](../data/experiments/STATE_ROUTER_STAGE0_VLLM_V1_20260827/PREREGISTRATION.md)，
结果见
[`RESULTS.md`](../data/experiments/STATE_ROUTER_STAGE0_VLLM_V1_20260827/RESULTS.md)。

## 本地安装与复现

所有命令在 WSL `UbuntuRecovered` 的项目根目录执行。本地引擎需已有自己的 `.venv`，项目环境
和引擎环境不会混装：

```bash
uv sync --locked --extra state-router

uv run --extra state-router rwkv-lh-state-router-train
uv run --extra state-router rwkv-lh-state-router-train-b
uv run --extra state-router rwkv-lh-state-router-eval-c

uv run python /home/chase/GitHub/RWKV-LH/scripts/evaluate_state_router_ablation_v1.py \
  --candidate A=data/experiments/STATE_ROUTER_STAGE0_VLLM_HIDDEN_MLP_V1_R2_20260827/predictions.test.jsonl \
  --candidate B=data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827/predictions.test.jsonl \
  --candidate C=data/experiments/STATE_ROUTER_STAGE0_VLLM_CONSTRAINED_LOGITS_V1_20260827/predictions.test.jsonl \
  --output data/experiments/STATE_ROUTER_STAGE0_VLLM_V1_20260827/ablation.json
```

模型 artifact 已在 `data/models/rwkv7-0.4b-g1-vllm-v1/` 登记来源、用途、生成方式和
config/vocab/weights hash。如需从同一冻结权重重新生成：

```bash
PYTHONPATH=/home/chase/GitHub/vllm-rwkv \
  /home/chase/GitHub/vllm-rwkv/.venv/bin/python \
  /home/chase/GitHub/RWKV-LH/scripts/prepare_state_router_vllm_artifact_v1.py \
  --engine-root /home/chase/GitHub/vllm-rwkv
```

## 项目内推理

输入为每行一个 Router input JSON：

```json
{"mode":"fresh","summary":null,"evidence_state":"none","policy_state":"network_allowed","request":"读取本地 pyproject.toml。"}
```

入选的 B 方案必须同时提供 head 和冻结 PCA：

```bash
uv run --extra state-router rwkv-lh-state-router \
  --head data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827/state_router_head.json \
  --projection data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827/projection.train_only.pt \
  --input-jsonl requests.jsonl
```

部署入口会校验引擎 commit/clean 状态、模型文件 hash、PCA 文件 hash、PCA 内容 digest、训练
split 标记、源模型 hash 和分类器 model hash。输出是 `rwkv-lh.state-router-output.v1` JSONL；
它是建议，不是执行或联网授权。

## 消融结论

固定 test 的关键结果如下：

| 候选 | route acc | route macro-F1 | phase macro-F1 | ECE | 提前 final | 正式门槛 |
|---|---:|---:|---:|---:|---:|---|
| A hidden+MLP | 0.986667 | 0.985986 | 0.992048 | 0.006284 | 0.028571 | 未通过 |
| B WKV+PCA+MLP | 0.996667 | 0.996607 | 0.989476 | 0.003315 | 0.007143 | 通过、入选 |
| C 约束 logits | 0.120000 | 0.030888 | 0.157534 | 0.140681 | 0.000000 | 未通过 |

B 的 300 条 test 中只有一条 route 错误：`RTR2K-1602` 的 `mixed -> final`。全量部署复核的
300/300 条离散输出、弃权原因和 State Profile 与正式预测一致。FP16 WKV 在不同批次组成下
存在置信度数值漂移，最大观测值为 `0.048895`，但本轮没有改变任何离散输出；该现象已作为
进入 Shadow 前的观测项保留，不能据此修改已冻结阈值。
