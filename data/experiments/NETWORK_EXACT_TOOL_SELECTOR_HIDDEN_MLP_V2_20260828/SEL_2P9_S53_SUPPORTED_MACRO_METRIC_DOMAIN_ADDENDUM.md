# S53 有支持类别 Macro-F1 指标域补充登记

登记时间：2026-08-29（Asia/Shanghai）。本补充发生在任何 S54 state checkpoint
特征、指标和真实 Harness arm 产生之前。原 S53 Head dev 选择结果已经产生，必须继续保留为
`eligible_for_locked_test=false`，不得覆盖、改写或删除。

## 发现的评价实现缺陷

冻结 S53 dev 集有 325 行，只包含 12 个有真值支持的操作类。项目通用
`classification_metrics` 固定对全部 25 类求平均，并把 13 个零支持且零预测的类记为 F1=0。
因此无论分类器多好，S53 该字段的理论上限都是 `12/25 = 0.48`；当前 Head 的 S53 dev
为 325/325 exact、12 个有支持类 precision/recall/F1 全为 1.0，但旧全域字段正好为 0.48。
这说明原预登记中“S53 macro-F1 >= 0.96”若解释为固定 25 类字段，是不可满足条件。

## 不可变处理

- 原始 `DEV_SELECTION.json`、25 类 confusion、raw logits、raw argmax 和
  `eligible_for_locked_test=false` 原样保留，不回填。
- 新增独立字段 `supported_macro_f1`：只平均真值 support > 0 的类别；这与同段已经登记的
  “所有有支持类别 recall >= 0.90”使用相同指标域。
- S53 的修正门槛为 accuracy >= 0.96、supported-macro-F1 >= 0.96、每个有支持类别 recall
  >= 0.90。固定 25 类 macro-F1 继续报告为诊断值，不再作为 S53 这个部分标签集的可达门槛。
- S28、S39、S52 都保留原来的全 25 类 accuracy/macro-F1 门槛，因而任何未在 S53 出现的
  工具能力仍受完整回归约束，不能因指标域补充而消失。
- S53 locked test、S54 state 因果比较和真实 Harness arm 只能读取冻结原始 logits 后计算上述
  两种 macro；不得 mask logits、改变 argmax、重试、修补或修改任何 RWKV 输出。

该补充只修复数学上不可达的聚合域，不改变数据、模型、预测、阈值数值、相似度算法或真实
Harness 成败口径。
