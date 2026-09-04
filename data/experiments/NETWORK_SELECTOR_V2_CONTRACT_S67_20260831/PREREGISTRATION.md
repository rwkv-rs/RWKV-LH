# Network Selector V2 Contract S67 预注册

## 目标

构建与当前真实 Harness 完全同构的 `CurrentDirectStageV2` Selector 数据集，修复 S66 训练分布仍使用 V1 stage capsule、导致真实 E3 atom 中 `.py/.md` 被选择为 JSON 写入等问题。

该数据只训练/评估 2.9B Selector。它不包含参数 schema、Executor 输出、强 Planner 原始 JSON、隐藏验收答案或 RWKV 生成文本，不承担工具参数与执行职责。

## 固定规模与编号

- 数据编号：`S67`。
- train/dev/locked-test：`2000 / 500 / 500`。
- 25 个 Selector 类别全部覆盖；每类 train/dev/test 分别 `80 / 20 / 20`。
- 每类每个 split 中英文各半。
- train/dev/test 使用完全不相交的词汇根、路径 token、source family 与请求文本。
- state-tuning 导出仅含 train/dev；locked-test 在候选选择完成前禁止 JSON 解析与标签访问。

## 当前协议固定输入

- V7 renderer：`rwkv_lh/exact_tool_selector/compact_protocol_v7.py`，SHA-256 `312e490f92fcc0d20dc8a78038291d15e298e6c8e27ae20eaff41fe7f38686f0`。
- V2 runtime projection：`rwkv_lh/exact_tool_selector/runtime_projection.py`，SHA-256 `9be096e7c65e5efd63fe32282ca923fed195e5bc551937b39860ada1625d7e00`。
- canonical contract progress：`rwkv_lh/atom_execution.py`，SHA-256 `1078d5905813ba8a809ff12dc72ea7a09c0d687bcd9fe2ae951c8b4cd7f2f043`。
- 每行必须通过真实 `SupervisorAtom -> AtomExecutionContract -> AtomExecutionBinding -> RunState -> build_network_selector_input` 构造；禁止手写仿造 V2 progress 字段。
- `stage_objective` 必须以 `CurrentDirectStageV2: ` 开头。
- 当前完整 atom requirement 必须位于 V7 step 的字节末端。
- persistent history 通过同一 requirement 的先前 V2 steps 重放；不得拼入参数 schema 或结果正文。
- 25 类 menu 只含工具名与描述；模型不生成文本，只提取 mean+last hidden。

## 标签生成

- 标签由预登记的 25 个语义场景族机械映射，禁止由模型生成或根据评测结果回填。
- investigate/verify/public/deterministic 场景无 write root；mutation 场景声明精确 write root 与当前 path kind；final 场景必须由 canonical progress 计算得到 `completion_ready=true`。
- mutation 对比至少覆盖：非 JSON 完整写入、JSON 完整写入、JSON 局部更新、文本替换/删行/追加、目录创建、复制、移动、删除。
- read/verify 对比至少覆盖：目录清单、文本检索、UTF-8 文件读取、JSON 读取、摘要、证据绑定、固定检查命令、一般命令。
- external/deterministic 对比至少覆盖：公开网页发现、结构化连接器、计算、日期差、当前时间。
- `ABSTAIN` 只用于明确没有任何描述工具适用的无权/不可达职责；旧能力仍由 S60/S61/S65 retention gate 单独约束。

## 固定留出与相似度

- Agent Ladder tasks SHA-256：`23cf009831fb38dd05bd3fad69e246a822a59ab6bd725833c6df2aaaf45c93bb`。
- Agent Ladder acceptance SHA-256：`f95da0b4085cdee3bc4555255dfb4f09d9272c00982634c72a040361c5774e06`。
- E3 full results SHA-256：`d7400d3bc2f9699feb3dab21ca3d7a734e159d23691b17bed191e7f14dc5c632`。
- E3 的完整用户请求、全部 Planner atom objective、task id 与验收路径均为 holdout；不得进入 S67 字面量。
- 相似度算法固定为 `utf8-byte-5gram-cosine.v1`，阈值为 `< 0.95`；对每个 S67 request 与全部 Ladder/E3 request/atom objective 取全局最大值。
- 运行后不得修改相似度算法、阈值或 holdout 范围。

## 状态训练导出

- target：`\nSelectorLabelV7: <label>`。
- `ctx_len=2496`，BOS token id `0`，只对 target suffix 计算 loss。
- prompt+target 必须 token-additive，且没有目标截断。
- 物理 GPU 固定为 GPU0；训练前仍需单独冻结模型、引擎、参数与候选 step。

## 训练与选择原则

- 首先训练 zero-state 配对 head；训练时可使用冻结 S65 train 作为旧能力留存，但 S67 训练行固定为 2000。
- dev 候选门：S67 accuracy 与 macro-F1 均 `>=0.96`，每类 recall `>=0.90`；S60/S61/S65 既有 dev 门全部保持，baseline-correct regression 必须为 0。
- zero-state head 通过离线门后，才进入真实 E3 canary；未通过则训练同一 S67 的 2.9B state + 配对 head。
- 若 zero-state head 已通过离线门和真实 canary，最小状态原则优先 zero-state，不为形式上的 state tuning 增加运行状态。
- locked-test 在 dev 候选唯一冻结后才打开；不得用 test 选择 epoch、架构、阈值或状态。

## 完成条件

- 数据、manifest、state rows 的来源、版本、用途、SHA-256 和生成方式完整登记。
- 角色纯度、split 隔离、holdout 相似度、token boundary 与 V2 canonical progress 全部通过。
- 不修改、删除、隐藏、截断、重排或替换任何 RWKV 原始输出。

