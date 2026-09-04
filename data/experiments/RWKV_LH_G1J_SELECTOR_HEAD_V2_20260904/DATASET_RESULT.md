# G1J Selector Head v2 数据冻结结果

日期：2026-09-04（Asia/Shanghai）

## 结果

- 数据集：`data/datasets/rwkv_lh_g1j_selector_persistent_head_v2`，约 2.0 MiB。
- manifest SHA-256：`703a8b16c33d144ada28de1fc3dc3a9f039179b203176051c3e58dda3d3421e9`。
- 500 行、250 条 sequence，每条长度 2；train/dev/sealed 为 `300/100/100` 行和 `150/50/50` 条 sequence。
- 25 类每类 20 行；train/dev/sealed 每类严格为 `12/4/4`。
- 第一位置和第二位置均覆盖全部 operation；第二位置必须继承同 scope 第一位置的 Harness 事实，不能复用 bootstrap 作为独立样本。
- 最大 prompt 长度 840 tokens，target 最大 9 tokens，低于提取上限 2048。
- renderer/target parser 500/500 往返一致。

## 相似度审计

算法和阈值保持预注册的 `utf8-byte-5gram-cosine.v1`、`< 0.95`，没有改评价口径。

- train/dev：`0.9487727870580588`。
- train/sealed：`0.9463389759357728`。
- dev/sealed：`0.9239167073133349`。

第一次生成预检没有写出数据集：train/dev 为 `0.9586642130344919`，train/sealed 为 `0.9582074050994863`，超过冻结阈值。根因是相同 operation transition 的公共 JSON 和工具描述占比过高。保留相同算法、字段和阈值，补充十个 fixture 本来就应具备的不同任务上下文后重新生成并通过；没有增加随机填充、target 泄漏或 split 特判。

## 代码与验证

- 生成器 SHA-256：`96fabce40815c298c25e99bf1cb37c7c994a9a0e6622095b922c3bf661c5015d`。
- 持久特征提取器 SHA-256：`1b8728ca2a791dbb75a4af523f0ad0fffeb6010d392db3d8f923c7aa9105cb2f`。
- Head 训练器 SHA-256：`6c47df2909317c1186842c0c9dd046cde59e3b8640951bb48cff49071448bc68`。
- Selector 定向测试：`30 passed in 6.45s`。
- 完整回归：`640 passed in 59.33s`。
- 本阶段没有执行 StateTune，也没有读取 sealed feature 或 label。

下一步只允许用已冻结的 public train/dev sequence 抽取持久特征，并按预注册唯一参数训练一个 Head。若固定 dev 门槛失败，不发布 Head，也不调整数据、Head 参数或阈值补跑。
