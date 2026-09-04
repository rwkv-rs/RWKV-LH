# Network Exact-Tool Selector Hidden+MLP v2.4 — hash-distributed natural scope 预注册

## 继承

- 冻结时间：2026-08-28（Asia/Shanghai），早于 v2.4 数据生成。
- 完整继承 v2..v2.3 的类别、规模、split、相似度、模型、特征、训练参数、指标、门槛和 state 消融。
- run_r0..run_r3 保持 rejected。

## 根因证据

v2.3 全量诊断中 19 个具有完整 path/entity 的类别 violation=0；仅 6 个无路径类别仍有 480 对。最高 pair 的 operation 句子相同，domain/subject/qualifier 因 index 模运算每 60 行重复，unique scope 主要只差 10 字节 hash。

## 唯一修订

- 数据集版本改为 `rwkv-lh.network-exact-tool-selector.v2.4`。
- 每个 semantic family 增加一个自然的两词 project identity。两个词分别由 family SHA-256 的独立字节映射到固定、label-independent 的 adjective/noun bank。
- project identity 同时进入总体 task 与 stage scope，使 bootstrap 和 causal delta 对同一实体有稳定绑定。
- adjective/noun bank、映射算法对全部 25 类完全相同，不编码 operation，不使用随机噪声。
- 其余 surface、模板、split、相似度口径与阈值不变。

## 固定拒绝条件

仍使用 canonical task/stage/role/progress 的 `utf8-byte-5gram-cosine.v1`、阈值 0.95。任一同类 pair ≥0.95，v2.4 整批拒绝。
