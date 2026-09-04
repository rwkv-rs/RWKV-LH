# Network Exact-Tool Selector Hidden+MLP v2.3 — semantic family surface 修订预注册

## 继承

- 冻结时间：2026-08-28（Asia/Shanghai），早于 v2.3 数据生成。
- 完整继承 v2、v2.1、v2.2 的类别、7500 行规模、240/30/30 split、相似度算法/投影/阈值、模型、特征、训练参数、指标、门槛和 state 消融。
- run_r0、run_r1、run_r2 保持 rejected；不得重算或覆盖。

## 根因证据

`temp/analyze_network_selector_v2_similarity_failures.py` 的只读诊断显示：

- train/dev/test 分别从 local index 0 重新开始；calculator/date/ABSTAIN 等模板因而跨 split 获得相同数字、模板、progress 与 subject，只剩短 hash 不同。
- 不含 path/entity 的 stage 模板形成 60-row 周期重复；例如相同 ABSTAIN 或 command 句子跨 split 的 5-gram cosine 约 0.98。
- 已包含独立完整 scoped path 的多数文件操作类别最大值低于 0.95，说明根因是 semantic-family surface 缺失，不是阈值过严。

## 唯一修订

- 数据集版本改为 `rwkv-lh.network-exact-tool-selector.v2.3`。
- surface index 在每类内全局唯一：train=0..239、dev=240..269、test=270..299，不在 split 边界重启。
- 每个 stage objective 都绑定一个自然可读、label-independent 的唯一 scope record（domain、subject、qualifier、family hash）；文件类已有 path 仍保留，同一个 scope 只属于一个 semantic family。
- scope record 只区分任务实体，不编码 operation label，不使用随机噪声，不移动 split，不删除相似 pair。
- task/stage 继续保持 v2.2 的因果分离。

## 固定拒绝条件

仍使用 canonical task/stage/role/progress 的 `utf8-byte-5gram-cosine.v1`、阈值 0.95。任一同类 pair ≥0.95，v2.3 整批拒绝。
