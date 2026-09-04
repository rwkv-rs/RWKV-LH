# EXE-G8 holdout evaluator metadata projection 补充登记

登记时间：2026-08-29；在任何 G8 checkpoint 或 G6 parent 对 G8 holdout 推理之前。

G8 原始 holdout240 已生成并冻结，source SHA-256 为 `9ca538ed6bf48fcb42b9c78ad59f59178217dd5d5073b9423eac0b222954e54a`。其 prompt、target、sample ID、family、operation、cluster 和 request-tail 均合法，但冻结的 raw-first Executor evaluator 还要求一个只用于 summary 分组的 `language` 字段；冻结 G4 workflow generator 的 Executor row 没有该字段。

不得修改或覆盖原始 holdout。生成一个 metadata-v2 projection：逐行完整复制原对象，仅根据 literal current requirement 是否包含 CJK 字符新增 `language=zh|en`。本 holdout 的 240 条均预期为 `en`。

硬约束：

1. projection 与 source 均 240 行，顺序和 sample ID 一致；
2. 除新增 `language` 外，删除该字段后的 projection 对象必须与 source 字节解析对象完全相等；
3. prompt、target、text、prompt/target SHA、family、operation 和 cluster 不变；
4. projection 不进入训练，不改变评价 target、sampling、阈值或相似度算法；
5. `raw_output_modified=false`，不涉及任何 RWKV 输出。
