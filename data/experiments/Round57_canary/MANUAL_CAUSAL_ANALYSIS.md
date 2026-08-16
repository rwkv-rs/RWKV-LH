# Round57 固定 15 题逐题因果分析

## 结果

本轮 Strict `2/15`、External `3/15`、Agent `2/15`、FP `0`、FN `1`。不满足 canary Strict 门槛，不可上传。M03 在 Goal parse 首次请求即输出不完整 JSON，run 未创建；它是模型协议失败，不是 runner 基础设施失败。

## 逐题

| 题目 | 结果 | 决定性链路 |
|---|---|---|
| B01 | 严格通过 | 写入/复读正确；多源 v2 未造成回归。 |
| B02 | 严格通过 | 输入、派生 JSON、复读均正确；三个 criterion 均完成。 |
| B10 | 正确阻断 | slug 实现/恢复仍错误，未进入 Goal evidence。 |
| M01 | 正确阻断 | 四个服务输出均不符合外部期望；GC1 只选 summary 观察并判 insufficient。 |
| M03 | run 未创建 | Goal parse 返回不完整 JSON；与 Round57 Goal evidence 变量无关。 |
| M06 | 正确阻断 | package/copy 链未完成，未进入 Goal evidence。 |
| M12 | 正确阻断 | 本轮代码仍是错误乘法；选源已从 Round56 的旧 M-T1 改为最新 M-T5，但 M-T5 观察到的仍是错误实现，裁决 insufficient。 |
| M16 | 正确阻断 | 读取/恢复链未生成 recovered.json，早于 Goal evidence。 |
| M18 | 正确阻断 | 只处理单个 input；GC1 选择 M-T2 读取，不能证明 digest_map 存在。 |
| H12 | 正确阻断 | 只读到局部 shard；GC1 选择最新 M-T5（shard_04），不能证明 aggregate。 |
| H13 | 正确阻断 | phase 仍只读单文档，未形成 checkpoint。 |
| LH02 | 正确阻断但选源不精确 | checkpoints 外部检查通过，final/config 错；GC1 却只选最新 final/config，不能证明较早的 step01，因而在更早 criterion 阻断。 |
| LH05 | 正确阻断 | shard 数据获取与 summary/report 链仍不完整。 |
| LH11 | 正确阻断 | 仍将文件范围当不存在的组合路径，未创建 checkpoints/memory_summary。 |
| B24 | FN | sorted.log 与 log.txt 均外部正确；GC1 仍只选原始 log M-T1，裁决正确指出它不能证明去重/排序，然后 obligation replan 重复旧任务。 |

## 对 Round56 根因的验证

- 新到旧目录和时间元数据改变了 M12、M01、H12、LH02 的选择，不再普遍固定为 M-T1。
- semantic prompt 已不包含未选 memory；本轮没有出现 M03/H12 那种引用未选 ref 的回答。
- 单 `actual_ref` 限制已消除，controller 可验证同路径历史 expected/current actual 与多 actual 集合。
- 仍然存在的瓶颈是：一次 source selection 可能只选“输入”或只选“最新输出”，而 criterion 需要另一时间点或更完整集合；当前一次 insufficient 立即升级为全局 obligation replan，放大了局部选源错误。

## 下一步

在不改变 Task/Action/Recovery 的前提下，只增加一次 evidence-local reselection：把 RWKV 的原始 insufficient reason 和先前 refs 原样反馈给 source selector，要求 RWKV 自己选择不同或扩展的集合，再由隔离的 semantic adjudicator 判断。相同集合不得无变化循环。

