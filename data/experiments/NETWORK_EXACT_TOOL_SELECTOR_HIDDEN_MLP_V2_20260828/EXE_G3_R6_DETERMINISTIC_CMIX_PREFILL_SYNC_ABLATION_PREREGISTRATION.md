# EXE-G3 R6 deterministic CMix + prefill sync 消融预注册

登记时间：2026-08-30（Asia/Shanghai）。本文件在启动任一 arm 前冻结。

## 前置证据

- 首 decode trace 结果 SHA-256：
  `bc0c765cd5d3cf89272a00d1afad78d50acdc6ef56f1d79a17cede5bd9e61c60`；稳定 prefill 后的
  首分歧为 layer0 CMix output。
- deterministic CMix candidate 结果 SHA-256：
  `261a2766e28dd4170a4b2f42c6245b0960d42be31bcc47c1bbecabc6d0ace781`；真实维度 64/64
  bitwise exact，9 个相关测试通过，p50 `0.03132852725684643 ms`，候选门槛全通过。

## 目的

候选 CMix 已去除 decode 的无序 atomic 归约。本实验只消融 packed prefill 边界同步，确定此前
由全量 fingerprint 隐式引入的同步中，哪一个最小集合足以让完整原始生成逐 bit 稳定。同步
只等待既有 CUDA 工作完成，不修改张量、权重、state、logits、token 或 RWKV 文本。

## 固定输入与 arms

- 模型/state：13.3B + `EXE-G3-MULTISTAGE-STEP2000`，state SHA-256
  `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`。
- 物理 GPU0，固定 eager、WKV `fp32io16`、禁用 FlashInfer/Rapid sampler。
- 固定冻结 dev480 的 index455：`EXEG6-25d90fc447d18b7b1bc63d0356ab`，prompt SHA-256
  `006194134f225089cbad9242065c1e3f4f05ca8387c9cd2bff54027b27eae1a2`。
- sampling 与 R6 相同：temperature0、top_p1、top_k0、seed1067、max_tokens256、固定 stop；
  每个 arm 请求 16 次并请求 logprobs5。
- 固定顺序：`none`、`addln`、`layer`、`combined`。每个 arm 独立重启服务：
  - `none`：只启用 deterministic CMix candidate；
  - `addln`：仅在 2D packed-prefill 的每次 `add_ln` 返回后同步当前 CUDA stream；
  - `layer`：仅在每次 `tmix_varlen`、`cmix_varlen` 返回后同步当前 CUDA stream；
  - `combined`：同时执行上述两组同步。
- decode 过程不由 adapter 添加同步。raw response body、raw text、token IDs、finish reason、logprobs
  先进入 fsync append-only hash chain，任何派生比较都在保存后执行。

## 固定指标、门槛与选择

- 每 arm transport/envelope/hash-chain 必须 16/16 valid，产品 `18070` 前后健康。
- 稳定 arm 必须同时满足 raw text SHA、raw token IDs SHA、finish reason 与完整 token-logprob sequence
  各只有 1 个 exact variant；不使用语义相似度代替。
- 候选选择优先级冻结为 `none < addln < layer < combined`；选择第一个稳定 arm。这是同步范围
  最小化顺序，不按生成内容好坏挑输出。
- 报告每 arm latency p50/p95，但本轮只定位正确性；胜出 arm 还必须进入后续端到端性能验证。
- 若四个 arm 均不稳定，结果保持未选择并继续定位；不得因结果修改重复次数、顺序或 exact 口径。

## 冻结实现身份

- adapter SHA-256：
  `06fdef5c13a78962c273341773b74b73026f851452bb0c66dd9ca92966656682`。
- launcher SHA-256：
  `8f843d0394bddccc2f6091bdcba1fd84194bb9a9fe54ccd14d8a71f223dc5e23`。
- candidate extension SHA-256：
  `31b64460dca6bc9d6b73a17120137822ae8b740eb5f3a3ee1fffbb1ea4a00fb1`。
- 原 state adapter SHA-256：
  `be0523b8abb557b8cdbbc22c4cc8dd927b2d07d675afba25b8702897a485bec2`。

本消融通过不等于 R7、联网质量或第一正式版本通过。
