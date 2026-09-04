# S65 Selector 多词根泛化数据预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 数据编号：`NET-SEL-2P9-S65-LEXICON-DIVERSITY`
- 目标：修复 S61 focus 数据把每个 split 绑定到单一词根所产生的 shortcut，同时保持 V7 问题末端、25 类、2,000 train / 500 dev / 500 locked test 与 Ladder 隔离。

## 触发证据与根因

S64 冻结基线 + 学习 gate 后，S60 dev 回归已经为 0，但 focus 最高 0.92。逐场景 dev 分析显示：`initial_text_write` 之外的 15 个场景基本全部正确，`initial_text_write` 16/16 全错。S64-G2 的 focus train gate 最小值 `0.9992286`，但该场景 dev gate 最大值只有 `0.0006052`。

S61 generator 对整个 train/dev/test 分别只使用 `quartz-workshop`、`indigo-foundry`、`saffron-studio`，manifest 登记为 `split_specific_entity_and_path_lexicons: true`。由于每个 focus split 只有一个词根，二元 gate 可以用词根记忆 split，不能证明它学会了“多阶段初始写入”。

本轮只修数据分布根因，不改变 label、operation、提示顺序或 Harness。

## 固定构建

- 来源 generator：`scripts/generate_network_selector_transaction_continuation_s61_v1.py`；只复用机械场景、V7 renderer、retention 选择、token/holdout 校验。
- focus 仍为 16 个冻结场景，train/dev/test 数分别 1000/250/250；语言各半。
- retention 仍从冻结 S60 按 25 label × 2 language 平衡抽取，train/dev/test 数分别 1000/250/250，label 不改。
- 总计 train/dev/test = 2000/500/500；state export 只含 train/dev，test 不进入优化或选择。

词根池固定为：train 16 个、dev 8 个、test 8 个，三池互不相交。对同一场景，第 k 个样本使用 `(k + 3 * scenario_index) mod pool_size` 的词根，使每个 train 场景覆盖全部 16 个词根至少 3 次；不能再由单一词根推出 split。dev/test 继续使用未见词根衡量泛化。

所有实体、路径、task_request、rendered input 与 source family 跨 split 精确不重叠。Ladder 继续使用固定 UTF-8 byte 5-gram cosine v1，最大相似度必须 `<0.95`；任何 Ladder task ID、workspace path 或 acceptance 均不得进入数据。

## 冻结验收

生成后必须记录 cases/manifest/state export/generator SHA；验证：

1. 每 split/cohort/scenario/label/language 数量精确；
2. train 每个 focus scenario 的 distinct root 数为 16，dev/test 为 8；词根池交集为空；
3. request、rendered-input SHA 与 source family 跨 split 交集为 0；
4. V7 complete requirement 仍是续写点最后语义字段和 literal byte tail；
5. target suffix token boundary additive，ctx 2496 不截断；
6. 生成 RWKV text、sampling、原始输出修改均为 0。

生成后先提取 zero-state train/dev Hidden(mean+last)，locked test 保持关闭。后续候选不得把本次已知根因变成词根规则；只能用学习式 MLP，在多词根 train 上泛化到未见 dev/test。
