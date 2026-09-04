# S53 / EXE-G3 多阶段双状态消融预注册

登记时间：2026-08-29（Asia/Shanghai）。本文件在 S53、S54、EXE-G3 数据生成、训练、
新特征提取或新模型指标产生之前写入。已经完成的 S52 + EXE-G2 canary6 只作为冻结根因证据。

## 当前架构与输入不变量

- 架构保持 `LongHorizonModel -> ActionHarness`：独立 2.9B Selector 只从固定 25 个
  name/description 中输出 Hidden(mean+last) + MLP 原始 argmax；独立 13.3B Executor 只在选择
  提交后接收一个工具的完整参数 schema，并生成参数或最终文本。
- Selector 与 Executor 的 WKV state 分开存储、编号、加载和消融；不得把两者合并，不得由
  13.3B 重新选择工具，也不得让 2.9B 看参数 schema、Executor 文本或完整工具结果。
- 所有当前产品 RWKV 生成/分类输入遵循同一排列：固定契约、菜单、状态和已观察证据在前，
  当前任务或当前阶段问题在最后，紧邻续写/Hidden 提取点。本轮保持已经冻结的 Selector
  V4-request-last 与 Executor V2-request-last 字节协议，不根据失败样本改变提示词措辞。
- 保存所有 25 维原始 Selector logits、原始 argmax、13.3B 原始 token/文本、原始工具结果和
  state 身份。禁止改写、删除、重排、隐藏、规则替换、类别 mask、阈值修补或隐藏重试。

## 冻结根因证据

- S52/V4 zero-state h64 + EXE-G2-V3-RL-step1250 的固定 canary6 结果为 `4/6`；结果文件
  SHA-256 为 `6ba59cfa89a8bbcce79fca85b51c805114e284df587d83147cee95fcad997113`。
- B10 当前路径为
  `list_directory -> read_file(slug.py) -> read_file(slug.py) -> write_file -> run_command(fail) -> read_file`；
  历史外部成功路径读取了 `slug.py` 和 `test_slug.py` 后写入并运行 `python test_slug.py`。
- H10 当前路径为
  `list_directory -> read_file(inventory.csv) -> write_json -> check_command(fail)`；历史外部成功路径
  在写入前读取了 `inventory.csv`、`policy.json` 和 `verify_release.py`，然后同时写 JSON/报告并验证。
- S51/S52 的 `inspect_implement_test` 合成链只有一次 `read_file`，没有覆盖多输入依赖。
- 冻结 EXE-G2 训练集 2,000 个 train prompt 的
  `recent_action_sequence_range.count` 全部为 `0`；它没有见过真实 Harness 的第二步及以后参数生成。
  其 train/dev/manifest SHA-256 分别为
  `1db4a93a9ce0fed2e89c76c2c0c06120848bddb708f905f5a669666814c6712a`、
  `47f4c80adf5f89279ee4e0d4b0792a48118868d3211021ba7ca1141cbdbef8dd`、
  `cfb3f93b2c53e40861a0bbd928022cce89ab073937faf49522180a293510a077`。

以上只用于定位通用缺口；B10/H10 的文件名、内容、隐藏验收和期望输出不得进入新训练数据。

## 数据臂

### S53：Selector 长链前缀补充

- 使用不与 E2E/live 请求重合的实体、路径和值，生成 10 种通用工作流；每种 train/dev/test
  分别 20/5/5 条 trajectory，合计 300 条 trajectory。
- 重点覆盖：实现文件+测试文件双读取，多源 CSV/JSON/verifier 读取，多源文本读取，失败检查后的
  重新观察与修正，联网证据落盘验证，结构化检索落盘验证，以及 search/replace、生成/检查等链路。
- 每条 trajectory prefix-close；每一步都由生产
  `build_network_selector_input` + compact V4 renderer 逐字节生成。只保存操作类型和有界成败进度，
  不含参数 schema、完整结果、Executor 文本或 hidden acceptance。
- S52 仍为冻结保留源；S53 是新增独立 source，不覆盖 S52。

### S54：2.9B Selector state-tuning 2K

- exactly 2,000 train + 500 dev，25 类分别 80/20；中英文各半；dev 不进优化。
- 提示使用 V4-request-last 的完整持久 trajectory；目标只监督 `SelectorLabelV4: <operation>` 后缀。
- 优先使用 S53/S52 的独立训练前缀；不足类别由冻结 S30 的语义输入重新渲染为 V4 补足。
- parent state 为 zero，物理 GPU0，2,000 steps，seed 1054，ctx 1536，step 500/1000/1500/2000。

### EXE-G3：13.3B Executor 多阶段 state-tuning 2K

- exactly 2,000 train + 480 dev；24 个 Executor 操作全部保留。
- train 每类先保留 50 条冻结 G2 的首步样本（1,200），再加入共 800 条多阶段样本；dev 每类
  10 条首步 + 10 条多阶段（480）。八个按固定类别顺序最前的操作各 34 条多阶段 train，
  其余十六类各 33 条，总计 800。
- 多阶段 prompt 必须保持 Executor V2-request-last；`current_requirement` 仍是最后字段，训练 target
  仍是一个未改写的直接 JSON 调用。`recent_action_sequence_range.count` 必须在 1..5，动作/结果在前。
- 关键多阶段族必须包含：从目录/前次读取中选择尚未观察的依赖、从多份已观察输入构造 JSON/文本、
  写入后运行直接测试文件、失败验证后的修正、联网/connector 结果落盘与再读取。
- 使用合成独立实体，不复制 B10/H10/live2 的路径、内容或目标；不得读取隐藏验收生成 label。
- 从 exact zero 训练，物理 GPU0，2,000 steps，seed 1055，ctx 2496，保存
  250/500/750/1000/1250/1500/1750/2000；不得继续 G2 state。

## 固定消融与门槛

相似度算法保持 canonical operation / canonical direct-call exact equality（相同为 1，否则 0），并报告
schema-valid、canonical exact、wire exact、raw-byte exact、macro-F1、逐类 recall、时延和混淆矩阵。
运行后不得修改评价口径。

1. Selector Head：S28 test retention accuracy/macro-F1 `>=0.99`；S39 与 S52 locked
   accuracy/macro-F1 `>=0.96`；S53 dev/test accuracy/macro-F1 `>=0.96`，所有有支持类别 recall
   `>=0.90`；portable logits 最大误差 `<=0.005` 且 argmax 完全相同。
2. Selector state：使用同一冻结 Head 比较 zero/S54；上述所有阈值不得回退，S53 changed decisions
   至少 1，净 rescue 必须为正。若不满足，选择 zero state，不能因为“训练完成”而启用 S54。
3. Executor state：在冻结 G2 dev480 和新的多阶段 dev480 上比较 zero/G2/G3。G3 必须 schema-valid
   `100%`、canonical exact `100%`、每类 canonical exact `>=0.95`，且相对 G2 多阶段净 rescue `>0`、
   原 G2 dev 不得新增 canonical regression。按满足联合门槛的最早 checkpoint 选择。
4. 真实四臂只改变独立组件：`S52+G2` 冻结基线、`S53-head+G2`、`S52+G3`、
   `S53-head+G3`；S54 只有通过固定因果门后才作为第五臂。固定 canary6 必须 `6/6 strict`。
5. canary 通过后运行 frozen live-network2，必须 `2/2 strict`；然后重放固定 retrieval9，所有既有
   来源质量、expected-host、证据完整性和延迟 gate 继续通过；最后 Full90 必须调度 `90/90`，
   benchmark-only `mock_api` 保留显式不支持失败，不加入产品工具，不得提前中止。

只有通过以上联合门槛的最小 state 组合可以写入 `.env.local`。若 zero Selector 已通过，则不加载
无净收益的 S54；若 G3 未通过，则保留 G2 并明确当前版本不可投用。所有实验输出写入本目录的新编号
子目录，旧 artifact 不覆盖。
