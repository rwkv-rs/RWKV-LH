# Round1 结构基线

## 相对旧 E2E-42 基线的系统性整改

Round1 是固定 RWKV-E2E-90 的第一轮，不与旧 42 题结果宣称同口径提升。本轮候选架构包含：

1. 将任务推进关联 `goal_criteria` 与可直接满足 Goal 的 `satisfies_criteria` 分离；只有通过验证的
   `CriterionEvidence` 才能触发完成。
2. 由确定性结构层分配全局 task id，并重写局部依赖引用、验证 DAG。
3. 将 recovery lineage 持久化到 replacement 之外，把验证失败路由回实际 producer。
4. 通过显式 capability negotiation 区分真实 recurrent state 与 prompt replay，不把 KV/cache
   推断成可恢复 RWKV state。
5. 最终回答直接返回 RWKV 原始响应；审计同时保存 raw 与可见文本，但不删、增、改、排序或替换。
6. 正式实验保存 prompt、raw output、parsed payload、格式归一、事件、完整状态快照及逐字段 delta。

## 固定全测结果

- External acceptance：7/90。
- Strict E2E：5/90。
- Basic / Medium / Hard external：5/30、1/30、1/30。
- False positive / false negative：6 / 2。
- 因果链完整：90/90。
- RWKV 最终输出非干预：11/11 个 completed run 字节完全一致。
- LH-Control：30/30。
- 离线回归：112/112。

## 结论

本轮建立 E2E-90 同口径基线。由于没有前一轮 E2E-90 成绩，不把它标记为“相对旧最佳提升”，
也不触发功能分支 GitHub 最佳点上传。后续轮次必须与本轮固定口径直接比较。
