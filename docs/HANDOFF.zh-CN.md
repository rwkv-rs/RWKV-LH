# 当前交接

更新日期：2026-09-09；当前轮 `CONTROLLER_ROLE_CLOSURE_R1_20260909`。执行规范见 [统一规范](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md)，最新分析、修复边界与 SHA 见 [链路报告](../data/experiments/CONTROLLER_ROLE_CLOSURE_R1_20260909/REPORT.zh-CN.md)，统一设计见 [角色链路契约](CONTROLLER_ROLE_LINK_CONTRACT.zh-CN.md)。前轮整改记录保留在 `STATETUNE_ENTRY_REPAIR_R1_20260909`。

## Agent 实测与 trace 到达位置

最近完整模型对比仍是 2026-09-07 的 R7：A/B 各 Strict **0/12**、completed **0/12**、mutation **0**，各成功目录观察 12 次；所有题原始终止 `strong_planner_unavailable`，子分类 `fixed_plan_exhausted`。模型没有执行第二个动作，后面的读文件、变更、检查、Stage 与 Final 路径尚无该轮能力证据。不能把它解释为已走到第二或第三阶段。

角色级：每臂 Executor 12 次、Step Auditor 12 次；Selector 12 次 handoff、36 次菜单求值。固定公开初始计划没有 Planner 模型生成，Stage Checker、Finalizer、Final Auditor 均未调用。24 条审计的 root-unproved 与同轮机械观察事实冲突；合同接受不能充当语义标签。

R7 固定 HEAD `9d931fd18e34c18bb918b569dd1e9dec5e2d6cc6`，freeze SHA `e237c85e9705ed84d301a97132a66ddbd8668717cd9d4ec5e0c04d9c3f2a3f64`。两臂在自身冻结条件内 VALID，不能接续或重评分成修复后的结果。原 [R7 报告](/home/chase/GitHub/RWKV-LH-zero-baseline-r4/data/experiments/ZERO_STATE_AGENT_BASELINE_R7_20260907/REPORT.zh-CN.md) SHA `1809a26e0c53583270bb8a905b83298032da72cdde639bfca64873f055ea24ba`；因果分析见同轮 [TRACE_ANALYSIS 报告](/home/chase/GitHub/RWKV-LH-zero-baseline-r4/data/experiments/ZERO_STATE_AGENT_BASELINE_R7_20260907/TRACE_ANALYSIS/REPORT.zh-CN.md)。更早中止/INVALID 实验保持原始记录，不再作为当前执行安排。

## 本轮代码与数据链变化

- Controller 接受步骤 REPAIR 后继续同一步；本轮另删除工具重复失败、Executor provenance 拒绝、Step Auditor 协议无效三条误转 Planner 的分支及其专用反馈字段。重复失败和无进展预算保留。
- 当前闭环轮补齐 Selector/Executor 共享的语义反馈、Finalizer 原候选/缺口与独立协议重试反馈；审计错误保留原边界而不重复动作/候选；最终执行缺口回到 Planner 并打开新的执行步骤。Stage Checker 接收全部相关动作，统一解析 artifact/revision 来源；去掉审计 evidence/gap 数量声明上限。工具兼容只使用结构前提，有限发现显式标记未知，显式 root 不裁剪。
- trace 校验允许运行前冻结前序 State 的逐角色来源。当前角色未满足数据条件时明确报告该角色的缺口，后序角色尚未到达不会阻止它。
- Auditor/Finalizer 正例需要独立语义复核；待复核原始边界写入 `review_queue.jsonl`。合法双人纠正单独保存目标及本地 token，原始输出、原 token 和证据不改写；已完成任务也不能自动把错误审计变成正例。
- 实际 prompt IDs、scope 与 BOS 元数据透传并核验；缺失 finish_reason 不再伪造 `stop`。没有服务器完整 token 证据的行保持 `token_ids_complete=false`。
- 修复命令沙箱静默回退、沙箱共享宿主网络、包裹私有片段的来源判定、Web 重启重复 worker，以及两个公共基准的包数据遗漏。

本轮完整回归 **1061 passed，0 skipped，194.99 秒**；验证输入差异、同边界重试、恢复、执行补证、阶段事实与五角色逐字节重建。测试包含 mock 模型与真实 Harness I/O，不构成生产角色数据或新增 Agent 成绩。

## 唯一架构与角色次序

产品入口仍只有 `rwkv-stateful-goal-loop.v7`；每个角色使用其唯一协议 builder。Owner 本轮明确保留当前五角色，问题优先定位于角色交接；不得按题型、路径或后缀穷举兼容。先统一任务契约、工具能力、证据、反馈、重试归属和恢复语义。公共 Controller 基类及 State 部署适配器不是第二套产品架构；GoalPlanPatch 仅接受当前 v4 和显式 phase，旧重放及角色模块已删除。

训练按 **Selector → Executor → Step Auditor → Finalizer → Final Auditor** 推进：当前角色达到预注册指标后固定 State，前序 State 固定、当前及后序 zero，采集下一角色的实际问题。阶段冻结仅作为下一次采集条件，正式组合仍须通过 Agent 验收与消融。模型升级主要调整模型/词表/State/上下文/传输配置，并验证适配；不因 RWKV 名称变化重写角色架构，旧 State 不自动复用。

## Owner 决策与训练记录

2026-09-09 owner 明确取消固定三轮上限，改按预注册指标、预算和实际训练记录管理。旧“Selector 已用尽”“Executor/Step Auditor 剩一轮”“第四轮禁止”均不再适用。历史计数未知仍记 unknown，不伪造为零，也不再以次数对账作为额度阻塞。决策及后续 run 记录要求见 [训练管理记录](../data/experiments/STATETUNE_ENTRY_REPAIR_R1_20260909/TRAINING_POLICY.json)。

已有按阶段推进的授权继续有效，不重复询问同一权限。具体训练应先登记模型/数据/训练器身份、固定回归、优化参数、资源预算、指标与停止规则；正式数据版本仍在 owner 明确授权范围内。没有实际 optimizer steps 的采集/测试不计为训练。

## 下一步与仍未证明的能力

1. 统一角色链路已完成本轮工程整改与完整回归，证据见闭环报告；下一步重新冻结生产运行测量实际模型表现。
2. 后续继续已授权的 2.9B 重新部署与训练后端兼容验证：只读核验发现旧转换目录已清理，原始 G1j 2.9B 权重仍在 NAS，SHA 与官方发布相符；当前在线服务为 13.3B。尚未部署新 Selector、未启动训练，不能复用未经验证的 13.3B 训练形状或旧模型身份。服务器只接收本地源码与完整 SHA manifest，不运行 Git。
3. 链路稳定后登记 Selector 覆盖 scope、样本量、固定回归、模型/数据/训练器 SHA、参数和实际预算，冻结新生产 trace。满足当前角色的预注册条件后执行已授权训练，通过后固定 State 并进入下一角色；不要求先拿到后序角色数据或 Agent 先高分。当前工作树尚无验证完成的优化器训练入口。
4. Planner 合同生成、Stage Checker 上下文/自然结束、后续编码与最终完成能力仍须新生产运行测量；E2E-LH09 的 `mock_api` 适配问题独立待修，不能恢复退役工具链或改分母。最终 Holdout 保持隔离、仅最终一次验收。
