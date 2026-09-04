# Network Selector S68 Semantic-Boundary 2K V1 — 预注册

日期：2026-08-31（Asia/Shanghai）

## 目标与触发证据

本轮不增加模型容量，不改变 25 类协议，只修 S67 全量 dev 证明的数据根因：2,000 条 train 在计数上平衡，但每个 label/语言只有一条真正的操作核心句式，路径和批次标识变化替代了语义多样性。

固定证据：

| 输入 | SHA256 |
|---|---|
| S67 fusion result | `aa94aa036254f8b7e7953b715d4f924ecdd5b44c0a40cb10f653aa5ada73c678` |
| S67 data-diversity analysis | `82c577bef82aa230d8ba40d8cba6def400281b5a8d27f4f800dbaec362703efa` |
| S67 cases | `0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859` |
| S67 manifest | `0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46` |
| frozen S67 generator | `ed3d929824ffdc6fff7ad0af1466fa09f1ac5580ec3d91d92a5abb7583c65987` |

完整 dev 中只有 `append_file / copy_file / replace_text / write_file` recall `<0.90`；`move_file` 是 `copy_file` 的主要错误吸收类。因此固定 contrastive 边界为：

`append_file / write_file / replace_text / copy_file / move_file`。

运行后不得根据结果增删该集合。

## 固定数据规模与协议

- 数据编号：`rwkv-lh.network-selector-semantic-boundary-s68.v1`。
- train/dev/locked test：`2000 / 500 / 500`，25 labels 各 `80 / 20 / 20`。
- 每个 split 英中各半；每个 label/语言为 train `40`、dev `10`、test `10`。
- 当前链路保持 `CurrentDirectStageV2 + compact V7 + literal complete_requirement byte tail`。
- Selector 仍只接收 tool name/description、当前阶段、机械 progress 和完整请求；不得出现参数 schema、Executor 文本、tool result 或 Planner raw JSON。
- state export 只包含 train/dev；locked test 不进入 state tuning、head 训练、checkpoint 选择或阈值选择。

## 固定语义边界构造

五个 contrastive labels 的每种语言固定写入 `9` 条清晰且互斥的核心句式：

- train 只使用 variants `0..4`；
- dev 只使用 variants `5..6`；
- locked test 只使用 variants `7..8`。

同一 split/index 的五个边界 label 共用相同词根、路径标识和通用 modifier，使可学习差异集中在操作语义：

- append 与 whole-file write：保留旧内容后追加 vs 创建/完整覆盖；
- exact replace 与 whole-file write：只替换声明片段并保留其余内容 vs 写完整文件；
- copy 与 move：保留 source vs old source 必须消失。

其他 20 labels 保持 S67 的冻结句式和机械 contract/progress 生成，作为全类 retention。不得添加关键词路由、标签规则或基于 dev 的样本特判。

## 固定隔离与验收

1. train/dev/test 的词根池、task request、rendered-input digest、source-family 全部零交集。
2. 五个边界 label 的核心句式集合跨 split 零交集；每 label/语言的 distinct core counts 必须为 train `5`、dev `2`、test `2`。
3. 五个边界 label 在每个 split/index 上必须形成完整五元 contrastive frame，路径 token 与 modifier 相同。
4. V7 request 必须是最后语义字段和 literal byte tail；target suffix token boundary additive。
5. `ctx_len=2496`，所有 train/dev state rows 不截断。
6. Ladder 与 E3 继续使用固定 `utf8-byte-5gram-cosine.v1`，最大相似度必须 `<0.95`；不得包含 Ladder task id、workspace path 或 acceptance literal。
7. 数据生成期间 RWKV model call、sampling、generated text、raw-output 修改均为 `0`。

固定隔离输入：Ladder tasks `23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`、acceptance `f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`、E3 results `d7400d3bc2f9699feb3dab21ca3d7a734e159d23691b17bed191e7f14dc5c632`。

## 后续冻结顺序

1. 生成 S68 并记录 generator/dataset/state-export SHA；运行全数据结构测试。
2. 只提取 train/dev 的 2.9B zero-state one-forward `global_mean + tail_mean + final_last`；S68 test 在 JSON parse 前跳过。
3. 先运行冻结 `DualViewGatedH128` zero-state head，门仍为 accuracy `>=0.96`、macro-F1 `>=0.96`、每类 recall `>=0.90`。
4. zero 通过则不做 Selector state tuning；zero 不通过才允许使用 S68 的 2K train 做编号 state tuning，并按 `500/1000/1500/2000` 固定顺序 screen，选择首个过门的最少 state。
5. 候选冻结后才允许一次性打开 S68 locked test；随后还必须通过旧能力 retention、artifact/service parity 和真实 Harness canary。

## 环境与原始输出

- 只在 WSL `UbuntuRecovered` 使用 `uv`；模型实验只用物理 GPU0，GPU1/2 不占用。
- 远端 `rwkv-8222:18070` 产品服务不得停止或替换。
- 不得修改、删除、隐藏、截断、重排、修补或替换任何 RWKV 原始输出。Hidden 特征和 raw logits 必须另存并按 SHA 绑定。
