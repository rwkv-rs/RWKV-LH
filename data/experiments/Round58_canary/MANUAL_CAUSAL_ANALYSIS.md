# Round58 固定 15 题因果分析

## 结果

Strict `1/15`、External `6/15`、Agent `1/15`、FP `0`、FN `5`；LH05 另有一次传输中断。Round58 不可上传。

## 核心证据

- B02：GC1/GC2 supported；GC3 首选输入 M-T1 后正确判 insufficient，第二轮直接 `replan`，没有选择已经存在的 report 复读 M-T3。
- M03：GC1 supported；GC2 对迁移后 M-T3 的内容错误地要求“另一个验证步骤”，第二轮直接 `replan`。
- B24：首选原始 log M-T1，裁决指出缺少去重/排序最终效果；第二轮直接 `replan`。
- M12：GC1/GC2 supported；GC3 只看测试文件中不同输入，判 insufficient；第二轮直接 `replan`，没有选择实现或通过测试的其他观察。
- M01：外部产物正确，但在 Goal evidence 前的任务验证阶段已经阻断，因此 evidence-local reselection 未介入。

## 逐题结论

| 题目 | 结论 |
|---|---|
| B01 | 唯一严格通过。 |
| B02 | FN；第二轮直接 replan。 |
| B10 | 错误产物被阻断。 |
| M01 | FN；阻断早于 Goal evidence。 |
| M03 | FN；对“verified” criterion 过度要求额外验证动作，第二轮 replan。 |
| M06 | 错误 package 被阻断。 |
| M12 | FN；单个测试源码不能覆盖固定输入 criterion，第二轮 replan。 |
| M16 | 未生成 recovered.json，正确阻断。 |
| M18 | 集合不完整，正确阻断。 |
| H12 | 聚合不完整，正确阻断。 |
| H13 | phase 输入不完整，正确阻断。 |
| LH02 | final/config 外部错误，正确阻断。 |
| LH05 | 传输中断且产物未通过，不能用于 Goal evidence 因果结论。 |
| LH11 | checkpoint/memory_summary 缺失，正确阻断。 |
| B24 | FN；第二轮直接 replan。 |

## 结论

source selector 与 semantic adjudicator 的两次 RWKV 意图会互相放大：第一次选择局部来源，第二次判不足，第三次选择器把“不足”理解为需要新任务而非需要不同历史来源。增加轮次只会重复协议困难。下一实验应让同一次 RWKV 输出同时包含 reason、verdict 和它实际依赖的 refs，避免跨请求意图漂移。

