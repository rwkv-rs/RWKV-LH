# S68 locked test 只读归因

S68 locked result SHA-256：
`b3e33b98e9ba7d5d9742fbb805331ae273142e94124e6dd1770f2ee0a6904c0a`。

冻结候选在 dev 达到 `0.978 / 0.9779586489676348 / 0.90`，但 locked test 仅
`0.928 / 0.9196358972475079 / 0.15`，因此已拒绝。

## 可复核现象

- 36 个错误中，`remove_line -> delete_file` 为 17 个，`write_json -> write_file`
  为 9 个，`move_file -> copy_file` 为 5 个，三组占 31/36。
- S68 专门扩展的五类边界在 locked test 为 `0.95` accuracy；其中 append、copy、
  replace、write 四类正确率高，move recall 为 `0.75`。
- 20 个 retention labels 仍沿用 S67 的单一 split-specific 核心句式。locked test
  中 17 类达到 1.0 recall，但未被统一扩展的 line/file、JSON/text 边界出现集中失败。
- 所有 500 条 feature 均通过 exact additive、单次当前前向和有限值检查；17 类完全
  正确，且错误集中于语义近邻，不支持 GPU、state 传递或随机性作为主因。
- test 运行中的训练、checkpoint selection、calibration、state tuning 和 logit
  后处理调用均为 0，排除运行后调参造成的假通过。

## 系统根因与边界

根因仍是语义覆盖不均：S68 只系统修复了五类，而不是完整 25 类操作本体。2,000 条
的数量已经足够让 train 达到 1.0；继续复制路径或增加同义 modifier 不会补上
`line vs path`、`JSON vs generic text` 等决策边界。

S68 test 不再用于任何训练、state tuning、head/epoch 选择或阈值修改。下一轮必须新建
S69：候选数据只复用 S68 train/dev 与更早的 S65 train/dev，统一覆盖 25 类；新建
独立 semantic-definition locked test。S68 test 只作为污染隔离源计算 exact/hash/
固定 byte-5gram 相似度，不提供样本或措辞。
