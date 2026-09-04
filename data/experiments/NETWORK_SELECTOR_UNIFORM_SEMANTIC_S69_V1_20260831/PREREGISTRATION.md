# Network Selector S69 Uniform Semantic 2K V1 — 预注册

日期：2026-08-31（Asia/Shanghai）

## 触发证据与目标

S68 locked test 已按固定门拒绝（result
`b3e33b98e9ba7d5d9742fbb805331ae273142e94124e6dd1770f2ee0a6904c0a`）。本轮不根据
S68 test 样本做特判，不增加标签、不增加 Router 职责，只把语义多样性从五类扩展到
全部 25 类。

固定历史输入：

| 输入 | SHA-256 |
|---|---|
| S68 cases | `8b0f1a17f25863f448858d082c7b6cf7dec5cb76414f635f5f2ab8416566d218` |
| S68 manifest | `4a6e201e3d1dc6dff63f72660a08455ae619c1186b45c95c7f9d86ffc985ea0c` |
| S65 cases | `28cbec6cce980e1835ff04529a6b6f555557e3514f8c9f259b65ee6478a23830` |
| S65 manifest | `dc1c166dbad6f5283a6cfc4571b6e17ca107d329b12456d330e18eabfa4bd582` |
| S67 CurrentDirectStageV2 generator | `ed3d929824ffdc6fff7ad0af1466fa09f1ac5580ec3d91d92a5abb7583c65987` |
| S66 historical broad-retention locked result | `5d24d7abedaa54d0cb586e5500a39ffb8a62f918f1fbb7bd3e418b78f153ed0d` |

## 固定数据构成

- S69 仍为 25 labels，train/dev/new locked test=`2000/500/500`，每类
  `80/20/20`，英中各半。
- 每类 train 固定取 `40` 条 S68 train 与 `40` 条 S65 train；dev 固定取
  `10` 条 S68 dev 与 `10` 条 S65 dev。只允许对应 split，test 行必须在 JSON
  解析前跳过。
- 所有复用 request 重新通过冻结 S67 代码构建
  `CurrentDirectStageV2 + compact V7 + literal complete_requirement byte tail`；不复用
  V1 stage 文本。
- S69 test 不取 S68/S65 test。它使用新的 split-isolated root 和只由正式 tool
  description/操作本体写成的两条英、两条中 semantic definitions；与 label name、
  参数 schema、Executor 文本、Planner raw JSON 和 tool result 隔离。
- 新 test 在每个 index 上形成共享路径/标识的 25 类 frame，检验真实语义差异而非路径
  token。

S68 locked test 只在候选行完全生成后进入隔离审计：不得读 label，不得把 request、
短语、路径或错误行写入 S69 train/dev/test；只计算 exact intersection 与固定
`utf8-byte-5gram-cosine.v1`，最大相似度必须 `<0.95`。

## 固定模型、head 与门

- 2.9B zero state，质量引擎 commit
  `0501caa628967103490507d734f6a5efaf165794`，WKV `fp32io16`，物理 GPU0。
- 当前 step 一次前向导出 `global_mean + suffix_mean + final_last`；固定
  `DualViewGatedH128`、seed `1067`、训练/归一化/epoch selection 逻辑与 S68 完全相同。
- dev 门保持 accuracy `>=0.96`、macro-F1 `>=0.96`、每类 recall `>=0.90`。
- zero dev 通过则不做 state tuning；未通过才允许用 S69 2K train 做编号 state tuning
  `500/1000/1500/2000`。禁止把 S68 test 用于该决定。
- 候选冻结后一次性打开全新 S69 locked test，门仍为 `0.96/0.96/0.90`；失败则拒绝，
  不允许回训。

通过 S69 仍不能直接发布；必须继续通过旧能力 retention、artifact/service parity、
真实 Harness canary 和完整项目回归。

## 原始输出与服务

不得修改、删除、隐藏、重排、截断、修补或替换 RWKV hidden、raw logits 或生成文本。
数据生成本身不得调用 RWKV 或 sampling。只用 WSL/`uv`/GPU0；不得停止、替换或污染
`rwkv-8222:18070`，GPU1/2 不使用。
