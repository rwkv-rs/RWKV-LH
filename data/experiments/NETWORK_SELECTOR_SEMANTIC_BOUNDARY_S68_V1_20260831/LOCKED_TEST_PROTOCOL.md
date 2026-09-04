# S68 locked test 一次性验收协议

日期：2026-08-31（Asia/Shanghai）

## 解锁条件与冻结候选

只有下列 zero-state 候选已在 train/dev 冻结后才解锁 S68 test：

| 输入 | SHA-256 |
|---|---|
| S68 preregistration | `4e5f0a29560fbce4ab60509e14aaf81dad380b5c0e1f7ba7713758d14779d08b` |
| S68 cases | `8b0f1a17f25863f448858d082c7b6cf7dec5cb76414f635f5f2ab8416566d218` |
| zero feature manifest | `9920dd0d7e3fc64b27699c3b445ad2cc5f44bf6243045e555ce5fd799bcab0aa` |
| zero head result | `913a02df5cc63baf82c45bf855443a29042acdb42c7a7d55ccf001a8ab04fa3b` |
| frozen head state | `f5b83ac847ec8632634c223337402e4c0518d226527fbd0d7d0ac1525388bd2e` |

冻结候选固定为 2.9B zero state、FP32-CMix engine commit
`0501caa628967103490507d734f6a5efaf165794`、`fp32io16` 与
`DualViewGatedH128` selected epoch 6。不得在 test 后改 head、normalization、标签顺序、
阈值、state 或 feature protocol。

## 固定运行与指标

1. 在 test 解析前完成所有输入哈希、GPU0、引擎、模型、派生运行时、head state 与
   远端产品健康 preflight。
2. 数据扫描时 train/dev 必须在 `json.loads` 前跳过；只解析 500 条 test。
3. 每条 test 重放 bootstrap/history，当前 step 仅一次前向同时提取
   `global_mean + suffix_mean + final_last`；feature shard 不存 label。
4. 只加载冻结 normalization/state dict 做一次 raw-logit forward；训练、epoch 选择、
   calibration、logit 后处理和 state tuning 调用均为 0。
5. 固定验收门沿用 dev：accuracy `>=0.96`、macro-F1 `>=0.96`、25 类最低 recall
   `>=0.90`。同时报告五个 semantic-boundary labels 和英中分组，但分组不另设运行后
   门槛。
6. locked test 若未过门，候选直接拒绝；不得用 test 错例继续训练或选择 S68 state。
   后续改进必须新建编号数据集和新 locked test。
7. 保存未修改 hidden reduction、未修改 raw logits、混淆矩阵及全部 SHA-256；输出
   路径投影为最终目录而非 `.pending`。

只使用物理 GPU0；不停止或替换 `rwkv-8222:18070`。任何 RWKV 生成文本、sampling、
原始 hidden/logit 修改、删除、重排、隐藏或截断均为禁止项。
