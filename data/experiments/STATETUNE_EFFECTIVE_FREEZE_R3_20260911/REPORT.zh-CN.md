# 有效成员冻结修复 R3

本轮不产生新的 Agent 成绩。沿用轮次 A：Strict 0/4、completed 0/4、mutation 0、动作 6；两题无进展、两题协议拒绝。optimizer steps=0。

原冻结接口在过滤后没有重新计算覆盖和回归成员，且无法把多个经独立准入的来源组合为可精确重放的最终候选。现新增密封 selected-source 登记：先逐组用生产提取器重放，比较完整 manifest 和所有原始工件字节，再按已登记 ID 过滤，重新执行覆盖、相似度、固定回归与计数审计。原始完整性失败不能被过滤隐藏。

每组 waiver 额外要求两个独立复核文件，同时 pin 来源登记、waiver、角色、来源数量和当前重放模块 SHA；旧 wrapper 的签名不能直接复用。已有单来源接口仍逐字节重放，并对过滤后的有效成员重新审计。status=valid、minimum_counts、首次不虚构 prior 等硬门保留。五角色协议、输入构造、推理与 State 转移未改。

RED_V2.log 三项先失败；SCOPE_RED.log 验证缺少范围复核被旧入口接受。修复后 SCOPE_GREEN.log 38 passed；最终完整回归 PYTEST_FINAL.log **1479 passed、0 failed、0 skipped，243.39 秒**。较早测试和环境失败保留，不覆盖。

独立技术复核已完成。真实 22 来源重放依赖当前 SHA 的新双签，另列 SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911，不能用单测替代真实数据验证。此工程提交不批准训练或发布正式数据集；当前去重结果 24 条/9 个边界低于预注册 30 条/10 个边界。
