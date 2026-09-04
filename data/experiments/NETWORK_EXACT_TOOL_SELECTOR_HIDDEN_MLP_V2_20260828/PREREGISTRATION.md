# Network Exact-Tool Selector Hidden+MLP v2 — 预注册

## 目标与边界

- 冻结时间：2026-08-28（Asia/Shanghai）
- 目标：训练独立 2.9B RWKV Hidden+MLP Selector，在 25 个固定类别中只选择一个工具。
- Selector 输入仅含原始任务、当前阶段目标/角色、操作计数以及 25 个工具的名称/描述。
- Selector 不接收参数 schema、Executor 文本、工具返回值、workspace 内容、推理过程或 13.3B state。
- Executor 13.3B 只在 Selector 原始 logits 已提交后收到被选工具的完整 schema 与执行目标。
- 本实验不生成、修复、截断、替换或删除任何 RWKV 原始文本；Hidden+MLP 本身不产生 RWKV 文本。
- 20 类 v1 协议及其 collection plan 保持冻结。本实验使用新增联网/确定性工具后的独立 v2 数据源，不把 v1 未验证 fixture 冒充训练数据。

## 固定类别

顺序以 `rwkv_lh.exact_tool_selector.network_protocol.NETWORK_EXACT_TOOL_LABELS` 为准，共 25 类：18 个 workspace/command operation、`web_search`、`connector_lookup`、`calculator`、`date_diff`、`current_time`、`final_answer`、`ABSTAIN`。

## 固定数据协议

- 数据集版本：`rwkv-lh.network-exact-tool-selector.v2`
- 来源：独立编写的 operation-intent 合同模板与 split-specific surface bank；标签来自预先登记的唯一 operation 合同，不来自待训练模型或 13.3B 自标。
- 每类 300 个独立 semantic family，共 7500 行。
- 每类固定 train/dev/test = 240/30/30；split 由 `sha256(family_id) % 10` 决定，0=dev、1=test、2..9=train，然后在生成时确定性选足固定数量。
- train/dev/test 使用不同 domain/subject/qualifier surface bank。
- 相似度算法固定为 `utf8-byte-5gram-cosine.v1`，同类阈值 `0.95`。不得在看到结果后更改算法或阈值。
- 每行保存 source、version、purpose、生成命令、generator SHA、协议 SHA、menu digest、输入 digest；manifest 保存数据文件 SHA。
- `data/datasets/rwkv_lh_ecra_route_v1` 的 45 个 web/connector 边界用例只作外部 holdout，不进入训练、校准或阈值选择。

## 固定特征与消融

- 模型：`rwkv7-g1i-2.9b-20260805-ctx16384`
- 权重 SHA-256：`ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`
- 引擎：项目固定 `vllm-rwkv` revision `67f0c5996c50...`，模型 artifact 转换必须逐 tensor 验证 dtype、shape 与内容摘要一致，`values_changed=false`。
- base state：zero/base Selector profile；本轮不使用训练 state。
- 特征 A：最后一层最后一个真实 token hidden，FP32 导出。
- 特征 B：最后一层所有真实 token hidden mean，FP32 导出。
- 两个特征使用完全相同的 split、seed、训练超参数和评价代码。
- MLP：`Linear(feature_dim,256) -> GELU -> LayerNorm -> Dropout(0.2) -> Linear(256,25)`。
- seed=829，AdamW，lr=0.001，weight_decay=0.001，batch=128，最多 60 epochs，dev macro-F1 early stop patience=10。
- temperature 只在 dev 上按 0.25..4.00、步长 0.01 选择；temperature 只校准概率，不改变 raw-logit argmax。
- 特征选择规则：先比较 test macro-F1，再比较 external holdout accuracy，再比较 test accuracy；全部相同则选择计算更少的 last-token hidden。

## 固定指标与通过门槛

正式 test（750 行）必须同时满足：

1. exact accuracy ≥ 0.90；
2. macro-F1 ≥ 0.90；
3. 每类 recall ≥ 0.75；
4. 五个新增 operation 每类 recall ≥ 0.85；
5. `search_text/web_search/connector_lookup` 三类边界子集 accuracy ≥ 0.85；
6. forbidden Selector field leak = 0；
7. class order、menu digest、model SHA、feature protocol、head SHA 全部精确匹配。

外部 ECRA 45-case holdout 必须同时满足：

- overall accuracy ≥ 0.80；
- web_search recall ≥ 0.75；
- connector_lookup recall ≥ 0.75。

任一门槛失败，不接入 product runtime，也不得修改评价口径后重报同一实验。

## State tuning 后续消融

Hidden+MLP base profile 通过后，才允许在同一固定 test/holdout 上比较：

- S0：zero/base Selector state；
- S1：单一 Selector state-tuning profile；
- S2：按阶段拆分的多个 Selector state profile。

仅当候选在相同数据和指标上有可重复净收益且无 per-class 回归时采用。S1 达标即不采用 S2。Selector 与 Executor state 必须使用不同目录、profile ID、SHA 和 checkpoint lane；不得在每阶段加载不同 state，除非 S2 预注册消融证明必要。

## 产物与完成条件

- 数据：`data/datasets/rwkv_lh_network_exact_tool_selector_v2/`
- 运行：本目录 `run_*`，保存特征 cache identity、训练历史、逐例预测、混淆矩阵、指标和所有 SHA。
- 代码、数据、模型 artifact、head、state profile 均能由 manifest 复核。
- 全量同类场景、边界、异常和历史联网 E2E 回归通过后，才能宣称 Selector 改造完成。
