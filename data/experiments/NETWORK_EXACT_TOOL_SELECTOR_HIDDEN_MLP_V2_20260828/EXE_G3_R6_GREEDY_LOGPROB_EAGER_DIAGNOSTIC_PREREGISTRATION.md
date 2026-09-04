# EXE-G3 R6 greedy logprob / eager 根因诊断预登记

登记日期：2026-08-30（Asia/Shanghai）。登记时实验端口 18075 空闲、产品端口 18070 健康，
本轮尚未启动服务或推理。

## 已冻结的入口证据

- R6 顺序分叉诊断结果：
  `run_g6_r6_greedy_order_divergence_diagnostic/DIAGNOSTIC_RESULT.json`
  - SHA-256：`88c0ce60efe8f5131b509159f79fc1f02836be4b4b338f1a46bfffa8cd6daee5`
- dedicated G3 32 次原始记录：
  `run_g6_r6_greedy_order_divergence_diagnostic/DEDICATED_G3_RAW.jsonl`
  - SHA-256：`fbb2952dfc012be1d3535463b52dd0986dc6d5d6984ae7b601f79da1169d1d45`
  - 相同请求出现两个 variant：43 token 21 次、86 token 11 次；首分叉为生成 token index 42，
    分别选择 EOS token 0 和换行 token 11。
- 固定目标：source index 455，sample
  `EXEG6-25d90fc447d18b7b1bc63d0356ab`，prompt SHA-256
  `006194134f225089cbad9242065c1e3f4f05ca8387c9cd2bff54027b27eae1a2`。

上述 dedicated 与 multi 的同条件重复都发生分叉，已排除“某一前序 profile 或 prompt 导致状态污染”
这一解释。本轮只区分 sampler 参数生效、模型 logits 漂移和 full-decode CUDA Graph 路径。

## 固定实验臂

所有臂使用相同 base model、G3 state `EXE-G3-MULTISTAGE-STEP2000`（SHA-256
`13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`）、物理 GPU0、
concurrency=1、attempt=1、temperature=0.0、top_p=1.0、top_k=0、seed=1067、max_tokens=256，
不重试、不修复、不后处理。

1. `graph_logprobs5`：沿用当前 native full-decode graph 服务，目标请求连续 24 次，唯一新增请求字段
   为 `logprobs=5`。保存完整 HTTP body、raw text、raw token IDs 和 logprob envelope 后，才派生 token
   index 42 的 selected logprob、top-5 最大值及 selected 是否为最大值。
2. `eager_raw`：使用同一引擎、模型和 state，但启动参数增加 `--enforce-eager`；不请求 logprobs，
   目标请求连续 32 次。

总计 56 个新请求。既有 32 次 graph/raw 基线不重跑。

## 固定解释口径

- 若 `graph_logprobs5` 在分叉位置所选 token 不是当步最高 logprob，则优先排查 temperature/seed 在
  GPU sampling state 的传播和 native sampler；不得把它归因于 RWKV state。
- 若所选 token 始终为最高 logprob，但同一前缀的最高 token 在 EOS/换行间变化，则证明进入 sampler
  前的 logits 发生漂移。
- 若 `eager_raw` 32 次只有一个 variant，而 graph 基线有两个，则分叉定位到 CUDA Graph replay 与
  RWKV state/自定义算子生命周期的交界；后续必须修复该通用路径并扩展所有同类 shape。
- 若 eager 仍有两个 variant，则继续排查 graph 之外的 state 初始化同步与 decode 自定义算子。

本轮是根因诊断，不产生质量或上线通过结论，不改变 R6 的 72/72 raw/token/canonical 门槛。
所有 response body 与 RWKV 原始输出必须 append-only、fsync 保存；不得修改、删除、隐藏、重排或
诱导原始输出。

