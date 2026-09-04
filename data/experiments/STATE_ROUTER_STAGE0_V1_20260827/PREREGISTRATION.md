# RWKV-LH State Router 阶段 0 预注册协议

- 日期：2026-08-27
- 状态：训练和 test 评测前冻结
- 冻结代码：`data/experiments/STATE_ROUTER_STAGE0_V1_20260827/FROZEN_CODE_MANIFEST.json`；
  在第一次 2k 正式前向前登记所有协议、后端、训练、指标、A/B/C runner、依赖锁与数据 hash。
- 设计来源：用户提供的《RWKV-LH 主动式工具路由与 State Router 设计方案 v0.1》，SHA-256 `5b34076fbea51b5a2cf0cf889d3d5ef76653f6072e0119612dc4d4028a16ca52`
- 阶段边界：只做离线分类，不接入主 Harness，不改变工具菜单，不授权联网，不启用 State Bank。

## 固定数据

- 数据集：`rwkv-lh.state-router-2k.v1`
- 全量文件：`data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl`
- 全量 SHA-256：`b345e98f0e58fe291767218f7c27da6c766a100145193f0e4be46051896de29f`
- split：semantic-family grouped；train/dev/test = 1400/300/300，任何镜像不得跨 split。
- 独立污染 holdout：ECRA route120 + E2E90，共 210 条；只做污染检查，不参与训练、阈值或 early stopping。
- 文本稳定性：`utf8-byte-ngram-cosine.v1`，UTF-8 byte 5-gram cosine；训练族对 holdout 必须 `<0.75`。

## 方案 A：首轮主方案

- 模型：`fla-hub/rwkv7-0.4B-g1`
- revision：`b84a6a3e9f51168241c733058098cb6354d3fc04`
- 后端：项目内进程 RWKV-FLA/Transformers，不经过远端生成 API。
- 本地运行栈：`rwkv-fla==0.7.202508221413`、`torch==2.8.0`、`transformers==4.55.2`；与 RWKV-FLA 发布时点对齐并由 `uv.lock` 固定传递依赖。
- 输入：`rwkv-lh.state-router-input.v1` 规范文本。
- 特征：最终层、有效 token、mean pooling；最长 1024 token；右侧 padding/truncation。
- 特征模型冻结，只训练 MLP。
- MLP：`hidden_size -> 256 -> GELU(tanh) -> LayerNorm(eps=1e-5) -> Dropout(0.2) -> 4 heads`。
- heads：context mode 2 类、execution phase 4 类、route family 7 类、network recommendation 2 类。
- seed：829；AdamW；lr `1e-3`；weight decay `1e-3`；batch 128；最多 60 epoch；patience 10。
- checkpoint 选择：只使用 dev 综合 macro-F1；test 不参与模型、阈值或 temperature 选择。
- 校准：每个 head 的 temperature 只在 dev 上按 NLL 选择，候选 `[0.25, 4.00]`，步长 `0.01`。

## ABSTAIN 固定规则

- route confidence `>=0.92`；
- route top1-top2 margin `>=0.30`；
- 分类头不得与 Controller/Gate 机械状态冲突；
- route head 可直接输出 `abstain`；
- 任一条件失败：`route_family=abstain`、`state_profile=S_base`、完整工具披露；不得静默选专用 State。

## 指标与门槛

评价实现固定为 `rwkv-lh.state-router-metrics.v1`，ECE 固定 15 个等宽 confidence bins。

首轮实验门槛：

- route accuracy `>=0.90`；route macro-F1 `>=0.88`；
- phase macro-F1 `>=0.90`；
- network-required recall `>=0.92`；connector recall `>=0.90`；
- bare/Summary route 一致率 `>=0.90`。

正式接入门槛（本阶段只报告，不据此改口径）：

- route accuracy `>=0.94`；route macro-F1 `>=0.93`；phase macro-F1 `>=0.95`；
- network-required recall `>=0.97`；connector recall `>=0.95`；bare/Summary 一致率 `>=0.95`；
- 必须联网 FNR `<=0.05`；错误联网率 `<=0.03`；evidence-missing 提前 final `<=0.01`；
- policy-rejected 继续率 `0`；connector 降级 web `<=0.02`；route ECE `<=0.03`；
- 高置信区 route accuracy `>=0.98`；OOD abstain recall `>=0.90`；错误且未 abstain `<=0.02`。

## 三方案消融边界

- A：最终层 mean-pooled hidden + MLP（本轮首先运行）。
- B：同一 0.4B、同一输入与 split 的最后一层 WKV recurrent state；按 exact-token-length
  bucket 前向，提取每个 head 的 row mean、column mean、diagonal、row RMS；PCA 只在 train
  拟合到 256 维（seed 829、4 次迭代），再使用与 A 相同容量和训练协议的 MLP。
- C：同一 0.4B、同一输入与 split 的单 token 约束 code logits；四个 head 分别使用固定
  A..G code legend，prompt 以 `Code:` 结尾，候选 continuation 是 RWKV 词表中的单 token
  ` A`..` G`；固定 prompt hash 为
  `e9354c1c98efae6da70100bd53c3524a265dc7c6131c744ac3925a22116bfcfd`。每个 head
  只在 dev 上选择与 A 相同网格的 temperature，不训练参数。
- B/C 未取得同模型、同 tokenizer、同数据的真实输出前，不允许以占位或规则分类器冒充消融结果。
- 选择顺序固定为：安全门槛、test macro-F1、OOD/abstain、Summary 稳定性、ECE、延迟、显存、工程复杂度。

## 本地运行时决定

`rwkv-rsv` 保留为 Rust 后端候选，但其当前公开库 API提供 logits 和可序列化 State，未直接提供本协议所需最终层 hidden。阶段 0 不修改其语义或用 logits 伪装 hidden。项目内 `HiddenFeatureExtractor` 是稳定边界；将来增加 `rwkv-rsv` hidden 导出后，不改变数据、MLP artifact 或 Router 输出合同。

## 禁止事项

- 不根据 test 修改 split、标签、排除规则、相似度算法、ECE bins 或正式门槛。
- 不让 Summary 覆盖 EvidenceState/PolicyState。
- 不把 Router 输出当作 Network Gate 授权。
- 不用 ECRA/E2E 请求训练 MLP。
- 不接入 Harness，直到阶段 0 报告达到进入 Shadow 的条件。

## 训练前冻结修订 R2

第一次 A 的 2k 运行启动后，Torch 在 backward 明确报告：虽然已请求 deterministic
algorithms，CUDA cuBLAS 因进程启动前没有 `CUBLAS_WORKSPACE_CONFIG` 而不具备确定性。该运行
保留但标记为 invalid，不参加消融，也不使用其 test 值调参。

R2 只在 A/B/C 共用本地后端中、Torch import/首次 CUDA 操作前固定
`CUBLAS_WORKSPACE_CONFIG=:4096:8`。数据、split、标签、模型 revision、特征协议、网络、seed、
optimizer、epoch、patience、temperature 网格、阈值和指标均不改变。R2 代码另存
`FROZEN_CODE_MANIFEST_R2.json`，后续正式结果只认 R2。
