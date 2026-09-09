# 当前交接

更新日期：2026-09-09；当前整改轮 `STATETUNE_ENTRY_REPAIR_R1_20260909`。执行规范见 [统一规范](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)，本轮源码、红绿回归、限制和 SHA 见 [整改报告](../data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/REPORT.zh-CN.md)。

## Agent 实测与 trace 到达位置

最近完整模型对比仍是 2026-09-07 的 R7：A/B 各 Strict **0/12**、completed **0/12**、mutation **0**，各成功目录观察 12 次；所有题原始终止 `strong_planner_unavailable`，子分类 `fixed_plan_exhausted`。模型没有执行第二个动作，后面的读文件、变更、检查、Stage 与 Final 路径尚无该轮能力证据。不能把它解释为已走到第二或第三阶段。

角色级：每臂 Executor 12 次、Step Auditor 12 次；Selector 12 次 handoff、36 次菜单求值。固定公开初始计划没有 Planner 模型生成，Stage Checker、Finalizer、Final Auditor 均未调用。24 条审计的 root-unproved 与同轮机械观察事实冲突；合同接受不能充当语义标签。

R7 固定 HEAD `9d931fd18e34c18bb918b569dd1e9dec5e2d6cc6`，freeze SHA `e237c85e9705ed84d301a97132a66ddbd8668717cd9d4ec5e0c04d9c3f2a3f64`。两臂在自身冻结条件内 VALID，不能接续或重评分成修复后的结果。原 [R7 报告](/home/chase/GitHub/RWKV-LH-zero-baseline-r4/data/experiments/ZERO_STATE_AGENT_BASELINE_R7_20260907/REPORT.zh-CN.md) SHA `1809a26e0c53583270bb8a905b83298032da72cdde639bfca64873f055ea24ba`；因果分析见同轮 [TRACE_ANALYSIS 报告](/home/chase/GitHub/RWKV-LH-zero-baseline-r4/data/experiments/ZERO_STATE_AGENT_BASELINE_R7_20260907/TRACE_ANALYSIS/REPORT.zh-CN.md)。更早中止/INVALID 实验保持原始记录，不再作为当前执行安排。

## 本轮代码与数据链变化

- Controller 接受步骤 REPAIR 后继续同一步的 Selector/Executor，保留 gap 上下文与重复无进展预算；不再无条件强制 Planner 改计划。各目标根的最新证据全部保留，不被固定八条截断。
- trace 校验允许运行前冻结前序 State 的逐角色来源。当前角色未满足数据条件时明确报告该角色的缺口，后序角色尚未到达不会阻止它。
- Auditor/Finalizer 正例需要独立语义复核；待复核原始边界写入 `review_queue.jsonl`。合法双人纠正单独保存目标及本地 token，原始输出、原 token 和证据不改写；已完成任务也不能自动把错误审计变成正例。
- 实际 prompt IDs、scope 与 BOS 元数据透传并核验；缺失 finish_reason 不再伪造 `stop`。没有服务器完整 token 证据的行保持 `token_ids_complete=false`。
- 修复命令沙箱静默回退、沙箱共享宿主网络、包裹私有片段的来源判定、Web 重启重复 worker，以及两个公共基准的包数据遗漏。

完整测试结果和各项红绿证据以本轮报告为准。测试包含 mock 模型与真实 Harness I/O，不构成生产角色数据或新增 Agent 成绩。

## 唯一架构与角色次序

产品入口仍只有 `rwkv-stateful-goal-loop.v7`；五角色共用唯一协议 builder。工具选择、参数生成、执行、步骤审计、阶段审查、回答与最终审计职责清楚，现有证据不足以支持替换全部角色。先修控制流与数据真值错误，再用固定条件比较角色拆分的调用成本和实际收益。公共 Controller 基类及 State 部署适配器不是旧产品架构。

训练按 **Selector → Executor → Step Auditor → Finalizer → Final Auditor** 推进：当前角色达到预注册指标后固定 State，前序 State 固定、当前及后序 zero，采集下一角色的实际问题。阶段冻结仅作为下一次采集条件，正式组合仍须通过 Agent 验收与消融。模型升级主要调整模型/词表/State/上下文/传输配置，并验证适配；不因 RWKV 名称变化重写角色架构，旧 State 不自动复用。

## Owner 决策与训练记录

2026-09-09 owner 明确取消固定三轮上限，改按预注册指标、预算和实际训练记录管理。旧“Selector 已用尽”“Executor/Step Auditor 剩一轮”“第四轮禁止”均不再适用。历史计数未知仍记 unknown，不伪造为零，也不再以次数对账作为额度阻塞。决策及后续 run 记录要求见 [训练管理记录](../data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/TRAINING_POLICY.json)。

已有按阶段推进的授权继续有效，不重复询问同一权限。具体训练应先登记模型/数据/训练器身份、固定回归、优化参数、资源预算、指标与停止规则；正式数据版本仍在 owner 明确授权范围内。没有实际 optimizer steps 的采集/测试不计为训练。

## 下一步与仍未证明的能力

1. 本轮提交后冻结新源码，按已授权开发范围核验实际服务、模型与 State 身份；服务器只接收本地源码与完整 SHA manifest，不运行 Git。最近原生配置记录见统一规范 §1.5，本轮未重测在线健康或部署新代码。
2. 先登记 Selector 的采集目标、覆盖 scope、样本量与预算。按当前代码保存完整生产 trace，抽取 Selector 并完成合法标签复核；不要求先拿到后序角色数据。
3. 满足当前角色的预注册条件后，在已授权预算内训练并比较固定回归；通过则固定前序 State，进入下一角色。本轮尚无合格正式角色数据，当前工作树也没有已经验证的优化器训练入口；必须登记并接通与实际 RWKV backend 匹配的训练器，不能把数据抽取命令称为训练完成。
4. Planner 合同生成、Stage Checker 上下文/自然结束、后续编码与最终完成能力仍须新生产运行测量；E2E-LH09 的 `mock_api` 适配问题独立待修，不能恢复退役工具链或改分母。最终 Holdout 保持隔离、仅最终一次验收。
