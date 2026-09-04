# Legacy feature manifest compatibility amendment

首次 S67 trainer preflight 在任何参数优化、候选输出或 locked-test 解析前失败。原因是冻结 S60/S61 feature manifest 早于顶层 `test_rows_json_parsed`、`test_labels_accessed` 与 `raw_hidden_modified` 证明字段：S61 缺前两个字段，S60 缺三个字段。其冻结 dataset contract 已明确 `included_splits=[train,dev]` 且 `locked_test_features_extracted=false`；每个冻结 shard 也明确 `labels_stored_in_feature_shard=false`、`generated_rwkv_text=false`、`sampling_invoked=false`、zero state、GPU0 与模型/引擎身份。

读取兼容规则在有效训练前固定如下：

- manifest 和每个 shard 仍必须逐文件匹配预登记 SHA-256；
- `dataset.locked_test_features_extracted` 必须为 false，`included_splits` 不得含 test；
- 新字段若存在必须为 0/false；对上述精确冻结的旧 manifest/shard，字段缺失可由冻结 split contract 与 shard 身份证明补足；
- 仍在读取 cases 时于 JSON 解析前跳过 train/test，并独立核对固定计数；
- 不改变数据、features、labels、模型、候选、损失、门槛、选择策略或任何 RWKV raw 输出。

失败尝试没有创建 `.pending`/最终候选目录，也没有进入 optimizer。
