# V3 强 Planner / Selector / Executor 全量诊断

- 真实固定集：10 题；严格通过 0/10。
- 强 Planner：82/82 返回可解析单 JSON；语义拒绝 6 次，全部在限定重试内恢复。
- Planner 语义偏差：{"existing_target_latest_read_dependency": 2, "kind_effect_pair": 3, "other_semantic": 1}。
- Selector：257 次原始 25-logit 选择，完整性=True；eligibility 改变全局 argmax 49 次。
- 13.3B：406 次原始 generation，逐字节身份完整=True；协议错误分类={"argument_or_schema": 53, "not_one_json_object": 89, "other": 2, "selector_abstained": 19}。
- 联网动作：9/9 成功；联网链路可达不等于任务质量通过。
- 结论：强模型格式/API 不是主瓶颈；先用 schema 消除 kind/effect 组合，再用真实 planner-style 原子轨迹补齐 2.9B Selector 语义分布。
- 原运行、Planner 响应正文、Selector prompt 与 RWKV 原始输出均未改动；报告不复制这些正文。
