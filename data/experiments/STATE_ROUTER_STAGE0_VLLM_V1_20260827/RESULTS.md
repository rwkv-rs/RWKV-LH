# RWKV-LH State Router 阶段 0：本地 vllm-rwkv 结果

- 日期：2026-08-27
- 状态：阶段 0 完成；候选 B 通过并入选；尚未进入 Shadow/主 Harness
- 引擎：`/home/chase/GitHub/vllm-rwkv@67f0c5996c50dca0ad779da545cb491527de988f`
- 模型类：`vllm.model_executor.models.rwkv7.RWKV7ForCausalLM`
- 指标协议：`rwkv-lh.state-router-metrics.v1`
- 数据：`rwkv-lh.state-router-2k.v1`，train/dev/test = 1400/300/300
- test SHA-256：`2d69f65491ac3379e8cb22658212c2ad3ae4761fa028dd40fdf7f62323a0fb35`

## 结论

阶段 0 的工程实现、固定 2k 数据、真实本地 vllm-rwkv 前向、A/B/C 消融、完整失败审计和
入选方案部署入口均已完成。安全优先排序只留下候选 B：最后一层真实 WKV state 统计、
train-only PCA 和多头 MLP。

B 同时通过首轮与正式门槛。A 的分类指标很高，但 `evidence_missing` 下提前 `final` 为
`0.028571 > 0.01`，因此不能用 macro-F1 覆盖安全失败。C 未形成可用分类边界。

## 固定 test 结果

| 候选 | 特征 | route acc | route macro-F1 | phase macro-F1 | network recall | connector recall | ECE | 提前 final | 正式 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| A | hidden mean + MLP | 0.986667 | 0.985986 | 0.992048 | 0.970370 | 1.000000 | 0.006284 | 0.028571 | 未通过 |
| B | WKV stats + train-only PCA + MLP | 0.996667 | 0.996607 | 0.989476 | 0.992593 | 1.000000 | 0.003315 | 0.007143 | 通过 |
| C | 单 token 约束 logits | 0.120000 | 0.030888 | 0.157534 | 1.000000 | 0.000000 | 0.140681 | 0.000000 | 未通过 |

B 的 Summary 一致率、OOD abstain recall、高置信 route accuracy 均为 `1.0`；必须联网 FNR
`0.007407`，错误且未 abstain 比例 `0.003333`，错误联网、policy-rejected 后继续和
Connector 降级 Web 均为 `0`。

## 全路径审计

- A：test 4 个 route 错误，全部是 continuation/evidence-missing 的 `mixed -> final`；
  train/dev/test 提前 final 分别为 `0/0.022059/0.028571`。
- B：test 只有 `RTR2K-1602` 一个 `mixed -> final`；train/dev/test 提前 final 分别为
  `0/0/0.007143`，仍满足冻结门槛。
- C：test 有 264 个 route 错误，policy-rejected 后继续率和错误联网率均为 `1.0`。
- 污染检查覆盖固定 ECRA/E2E 210 条 holdout，`utf8-byte-ngram-cosine.v1` 最大相似度
  `0.470357 < 0.75`；semantic-family 跨 split 重叠和精确输入重复均为 `0`。

本轮没有依据 test 修改标签、split、阈值、相似度算法或评价口径。逐样本证据见
`failure_analysis.json`，安全优先选择见 `ablation.json`。

## 本地引擎和资源

模型前向只在本地 vllm-rwkv 自己的 Python/Torch 2.11 环境运行；RWKV-LH 的 Torch 2.8 环境
只承担 PCA、MLP 和指标，不混装推理栈。worker 强制离线，并验证 `vllm.__file__` 来自固定
本地源码树。

- A：特征 `15.426s`，head `1.468s`，总计 `16.893s`。
- B：特征 `15.575s`，PCA `0.327s`，head `1.142s`，总计 `17.044s`。
- C：全 2k 推理 `48.596s`，`41.155 samples/s`。
- A/B CUDA peak allocated 均为 `1,332,373,504` bytes。

完整 `LLM` Model Runner V2 在当前 WSL 因 UVA 不可用，阶段 0 使用仓库自带的 direct-model
boundary；没有修改 vllm-rwkv 源码或 RWKV 数学语义。

## 部署等价性

入选 B 已接入 `rwkv-lh-state-router --projection ...`。入口逐项校验引擎、模型、PCA 和 head
身份。冻结 test 的 300/300 条离散输出、弃权原因和 State Profile 与正式预测一致。

同时保留一个非门槛数值诊断：FP16 WKV 在正式全 2k 特征批次与仅 test 批次的组成不同时，
246/300 条置信度差值超过 `1e-5`，最大值 `0.048895`；本轮 0 条离散决策变化。它不改写正式
门槛或消融结论，但应在阶段 1 Shadow 中持续记录 batch-size/批次组成与阈值附近样本。

## 复核入口

- `PREREGISTRATION.md`：本地 vllm-rwkv 预注册
- `FROZEN_CODE_MANIFEST_R2.json`：正式运行代码冻结修订
- `ablation.json`：固定三方案消融
- `failure_analysis.json`：全量失败审计
- `runtime_equivalence.json`：300 条部署离散等价与置信度诊断
- `LOCAL_RUNTIME_SMOKE.json`：项目入口真实调用
- `DEPLOYMENT_CODE_MANIFEST.json`：部署代码 hash
- `VERIFICATION.json`：测试、锁文件、hash 与差异检查记录
- `../STATE_ROUTER_STAGE0_VLLM_HIDDEN_MLP_V1_R2_20260827/results.json`：A
- `../STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827/results.json`：B
- `../STATE_ROUTER_STAGE0_VLLM_CONSTRAINED_LOGITS_V1_20260827/results.json`：C

最终全仓库回归为 `345 passed in 38.38s`；State Router 聚焦回归为 `16 passed in 5.17s`；
`uv lock --check`、`git diff --check`、Python compileall、正式 R2 hash、部署 hash 和本地引擎
clean commit 校验均通过。
