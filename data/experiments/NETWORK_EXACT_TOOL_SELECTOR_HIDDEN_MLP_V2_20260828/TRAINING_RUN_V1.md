# Selector v2.4 Hidden+MLP Training Run v1

- 冻结日期：2026-08-28（Asia/Shanghai），训练前登记。
- 只允许读取 `run_r1/FEATURE_MANIFEST.json` 验证通过的 7500 行 batch=1 cache。
- last 与 mean 分别独立训练；使用主预注册完全相同的 seed=829、hidden=256、dropout=0.2、AdamW lr=0.001、weight_decay=0.001、batch=128、max_epochs=60、patience=10。
- train/dev/test 固定 6000/750/750，不能移动行。early stop 只看 dev macro-F1；同分只用 dev loss 决胜。
- temperature 只看 dev，0.25..4.00 步长 0.01；不改变 raw argmax。
- 正式 synthetic test 门槛完整继承主预注册。
- JSON artifact 必须由 dependency-light inference 重放 3 个固定 test 行；与 Torch raw logits 的 max_abs_diff ≤0.005 且 argmax 完全相同。失败不得发布 head。
- 本轮不使用任何 state tuning profile；base/zero state 特征已由 cache 固定。
- ECRA 45-case external holdout 在两个 head 都冻结后单独提取/评价，不参与训练或候选修改。
