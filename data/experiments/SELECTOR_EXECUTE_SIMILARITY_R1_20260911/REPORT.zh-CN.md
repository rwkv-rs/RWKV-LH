# Selector 固定去重策略应用

轮次 A 的 Agent 结果：Strict 0/4、completed 0/4、mutation 0、动作 6；两题无进展、两题协议拒绝。

沿用原 PREREGISTRATION.json 的 UTF-8 byte 5-gram、0.95 阈值、boundary 连通分量、固定字典序代表及原 5 个评测 anchor。162+48+46=256 条真实候选保留 24 条，排除 232 条；19 train / 3 dev / 2 confirmation，9 个独立边界，其中 train 7 个。五个评测 anchor 全字段不变，跨切分超相似对 0，execute=3。政策未按结果调整，未改 family 或切分。

本目录是政策应用工件；带来源与双签的正式重放工件见 ../SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911/effective_candidates/。有效 24 条/9 边界不足预注册 30/10，未 freeze、未 smoke、未训练。
