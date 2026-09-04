# S56 / S55 有支持类别 Macro-F1 指标域补充登记

登记时间：2026-08-29（Asia/Shanghai）。本补充发生在 S56 特征提取完成、
Head 训练或任何 S56 真实 Harness arm 产生之前；数据、logits、argmax、阈值数值和
相似度算法均不改变。

S55 真实联动 dev/test 各 240 行，只覆盖该五类工作流实际使用的 11 个工具类。
项目通用 `classification_metrics` 固定对全部 25 类求平均，并把 14 个零支持类记为
F1=0，因此其固定 25 类 macro-F1 理论上限只有 `11/25 = 0.44`。原登记中的
“S55 macro-F1 >=0.98”若使用该全域字段，在数学上不可满足。

冻结处理如下：

- S55 门槛中的 macro-F1 明确为只平均真值 `support > 0` 的 11 类
  `supported_macro_f1`，数值门槛仍为 >=0.98。
- S55 accuracy >=0.98、每个有支持类别 recall >=0.90 均保持不变。
- S28 使用完整 25 类 accuracy/macro-F1 >=0.99；S39/S52/S53 使用其原登记与
  S53 既有指标域补充。因此 S55 未覆盖的工具仍受完整历史覆盖约束，不能消失。
- 固定 25 类 macro-F1、完整 confusion、所有 raw logits 和 raw argmax 仍原样报告；
  不 mask logits、不改变预测、不重试、不后处理。

本补充只修复部分标签集的聚合域，不改变任何模型输入、输出或候选选择证据。
