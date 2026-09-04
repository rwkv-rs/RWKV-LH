# RWKV-LH State Router Stage 0 本地 vllm-rwkv 预注册协议

- 日期：2026-08-27
- 状态：vLLM 2k 正式前向与 test 评测前冻结
- 变更原因：用户明确要求只使用本地 `/home/chase/GitHub/vllm-rwkv` 推理引擎。
- 阶段边界：仍只做离线分类；不接主 Harness、不改变工具菜单、不授权联网、不启用 State Bank。
- 冻结代码：`FROZEN_CODE_MANIFEST.json`

## 本地引擎和模型

- 引擎源码：`/home/chase/GitHub/vllm-rwkv`
- 引擎提交：`67f0c5996c50dca0ad779da545cb491527de988f`，正式运行要求 clean worktree。
- 引擎 Python：`/home/chase/GitHub/vllm-rwkv/.venv/bin/python`
- 引擎运行栈：vLLM `0.1.dev949+g67f0c5996`、Torch `2.11.0+cu128`、
  Transformers RWKV fork `5.15.0.dev0`。
- 推理方式：直接实例化本地 `vllm.model_executor.models.rwkv7.RWKV7ForCausalLM`，
  使用其标准权重加载、CUDA ops、`forward_all_hidden()`、`zero_state()` 和
  `project_logits_fp32()`；不调用 RWKV-FLA/Transformers 模型前向，也不调用远端服务。
- 完整 `LLM` scheduler 在当前 WSL 因 UVA 不可用而不作为 Stage-0 特征边界；该限制只涉及
  Model Runner V2 的 staging buffer。State Router 使用仓库自带 direct-model boundary，
  不修改 vllm-rwkv 源码或 RWKV 数学语义。
- WKV mode：`fp16`；activation `float16`；约束 logits 使用本地引擎 FP32 lm_head。

模型 artifact：`data/models/rwkv7-0.4b-g1-vllm-v1/`。

- 隐藏维度 1024、24 层、head size 64、vocab 65536。
- 原始冻结权重 SHA-256：
  `c6751e01566942bcc13bca06afa8476ae5ed229a3778c8f8b27bddbdf5332af3`。
- 标准 vllm-rwkv artifact 权重 SHA-256：
  `0f871baf0b787f6a3eda82cb8678f72b075eac52c468e0479ea1d4fe2bb147c0`。
- 转换仅机械重命名和把一维 recurrent 参数 reshape 为 `[1,1,C]`；795 个张量的数值不变，
  标准 key 集与 shape 集由本地引擎的 `rwkv7_checkpoint_weight_shapes()` 全量验证。
- 模型、来源、用途、生成脚本、引擎提交、config/vocab/weights hash 见模型 `manifest.json`。

## 固定 tokenizer 和特征

- tokenizer：本地 vllm-rwkv `RWKVTokenizer`，词表来自引擎仓库；vocab SHA-256
  `e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89`。
- BOS/EOS/PAD token 均为 0；每条输入强制一个 BOS；最大 1024 token；左截断。
- 不做 padding 前向。样本按 exact token length 分桶，避免 padding 改变 recurrent state。
- A：最终层所有真实 token hidden mean，`1024 -> 256 -> 4 heads`。
- B：最后一层 WKV state 的 row mean、column mean、diagonal、row RMS，得到 4096 维；
  PCA 只在 train 拟合到 256 维，再使用与 A 相同容量的 MLP。
- C：固定 A..G 单 token code，由 `project_logits_fp32()` 取得候选 logits；只在 dev 校准。
- 单条、batch=4 的 A/B 和 7-code C 真实探针均已通过且全部 finite；同一输入跨两个独立
  本地引擎进程的 hidden 输出逐元素完全相同，最大绝对差 `0.0`。

## 固定数据、训练与门槛

- 数据仍为 `rwkv-lh.state-router-2k.v1`；全量 SHA-256
  `b345e98f0e58fe291767218f7c27da6c766a100145193f0e4be46051896de29f`。
- semantic-family grouped train/dev/test = 1400/300/300；test SHA-256
  `2d69f65491ac3379e8cb22658212c2ad3ae4761fa028dd40fdf7f62323a0fb35`。
- 污染 holdout、`utf8-byte-ngram-cosine.v1`、标签和完整数据验证保持不变。
- MLP、seed 829、AdamW、lr `1e-3`、weight decay `1e-3`、batch 128、60 epoch、
  patience 10、dev-only checkpoint 和 temperature 网格均保持不变。
- ABSTAIN 固定为 route confidence `>=0.92`、margin `>=0.30`、OOD 和机械状态一致性；
  失败时必须输出 `abstain + S_base`。
- 指标仍为 `rwkv-lh.state-router-metrics.v1`，ECE 15 个等宽 bins。
- 首轮与正式安全门槛完全继承
  `../STATE_ROUTER_STAGE0_V1_20260827/PREREGISTRATION.md`，不得根据本轮 test 修改。
- 选择顺序仍为：正式安全门槛、test macro-F1、OOD/abstain、Summary 稳定性、ECE、
  延迟、显存、工程复杂度。

## 隔离与禁止事项

- RWKV-LH 的 Torch 2.8 环境只训练/评测小型 MLP；模型前向只由本地 vllm-rwkv
  Python/Torch 2.11 环境执行，二者不混装。
- worker 强制 `HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`，并校验 `vllm.__file__`
  位于固定本地源码树。
- 本轮使用全新的 `STATE_ROUTER_STAGE0_VLLM_*` cache/产物目录，不复用此前 FLA 特征或 head。
- 不根据 test 修改 split、标签、门槛、相似度算法或 ECE bins；不做样本特判。
- 不让 Summary 覆盖 EvidenceState/PolicyState，不把 Router 建议当作 Network Gate 授权。

## 冻结修订 R2

第一次 A 的本地 vLLM 特征前向成功后，RWKV-LH Torch 2.8 在小型 MLP backward 报告
`CUBLAS_WORKSPACE_CONFIG` 没有在首次 CUDA 操作前设置。该运行保留并标记 invalid，完全排除
于消融；不使用其 test 值修改任何协议。

R2 只在共享后端模块导入 Torch 前恢复 `CUBLAS_WORKSPACE_CONFIG=:4096:8`，并把 A 默认输出
切换到独立 R2 目录。vllm-rwkv 引擎、模型、tokenizer、特征、数据、训练、校准、阈值和指标
均不改变。R2 代码见 `FROZEN_CODE_MANIFEST_R2.json`，正式结果只认 R2。
