# RWKV-LH × ECRA 主动 Harness 实现报告 R2

> 历史实现节点；后续 3 个 P1、5 个 P2 的整改与 `245 passed` 结果见
> `../RWKV_HARNESS_P1P2_REMEDIATION_20260825/REPORT.md`。

状态：工程主链完成；真实 RWKV 路由门禁失败，尚不可标记为 production-ready。

记录日期：2026-08-25（Asia/Shanghai）

## 已完成的工程主链

- 单一 CausalEvent authority、Strong Planner 零具体工具权、RWKV 唯一动作作者；
- Contract Graph v2 capability projection、强模型失败 pending/resume、并行 RWKV atom；
- `offline / auto_public / explicit_egress` 不可变运行策略和 public path 审批；
- ECRA-derived fetch/SSRF redirect gate/clean/chunk/provider、逐 run 不可变 route/source snapshot；
- 外部证据 Action-ID 绑定和从 CausalEvent 折叠的 disposable retrieval ledger；
- secret/workspace-sensitive/tool-untrusted provenance 拒绝，Controller 不改 query、不替换工具；
- OpenAI-compatible 强规划器产品入口；凭据只从 ignored env/进程环境读取，不进入 Goal/trace/manifest；
- RWKV native-state transaction 协议、能力探测、自动回退和 checkpoint digest；
- 持久主动队列、one-shot/interval trigger、审批、租约/心跳、崩溃接管、指数重试、死信和通知；
- CLI/Web/主动 worker 从同一不可变 Goal 重建同一 Controller；
- 本地全量回归 `233 passed`；公开站点 fetch/实际 peer-IP 二次校验 smoke 返回 HTTP 200，未记录正文。

本轮额外修复了三个系统性缺陷：同 clean 正文的不同 raw/source 不再发生 snapshot 路径碰撞；并发调度者
不会重复物化同一周期 occurrence；非法 job 状态转换不会生成虚假生命周期通知。

## 距离全套主动 Harness

按固定的六层工程/采纳 rubric 估算为 **67/100，尚差约 33%**：

| 层 | 权重 | 当前得分 | 证据/缺口 |
|---|---:|---:|---|
| authority 与规划/动作权分离 | 20 | 18 | 主链已闭合；Strong plan 仍有 schema/语义不稳定 |
| 工具、检索、证据与出站安全 | 20 | 17 | 主链已实现；部分 live connector 仍会 typed unavailable |
| 状态、事务、恢复与幂等 | 15 | 12 | prompt/native 协议和恢复存在；当前 RWKV 服务尚未提供真实 native-state transport |
| 主动触发与运行控制面 | 15 | 11 | one-shot/interval/审批/租约/重试/通知完成；event/webhook/file trigger 与运维面未做 |
| RWKV 路由与闭环行为质量 | 15 | 6 | R9 首工具 5/7，network Macro-F1 0.7083，未过线 |
| 全量确认、稳定性和生产运维 | 15 | 3 | route120/Full90/确认复跑因 Canary 失败未启动 |

这个百分比描述“可作为全套主动 Harness 采纳”的距离，不是否认工程骨架已经可运行。当前最大剩余量已经
不是再增加一个 Router，而是：Strong Planner 合同稳定性、RWKV Observation→下一动作的 state tuning、真实
native state transport、更多主动触发器和完整确认实验。

## R9 决策

R9 的 7 例结果：首工具 `0.7143`、序列前缀 `0.5714`、network Macro-F1 `0.7083`、web/connector
Macro-F1 `0.8333`、required-online FNR `0.3333`、privacy backend execution `0`、privacy rejection
coverage `0.5`、failed/unavailable `2`。因此严格停止，没有运行 route120/Full90。原始错误和 state tuning
方向见相邻实验的 `R9_ANALYSIS.md`。

## 当前不应伪装成工程缺陷的外部缺口

1. 当前本地 RWKV endpoint 没有宣告 native state create/fork/commit/rollback 能力；运行时会诚实回退，
   `native_required` 会失败关闭。
2. R9-091 是强规划器连续三次生成不满足冻结 contract schema/semantic 的 patch；Controller 已正确保存
   pending 并中断。
3. R9-111/118 是 RWKV 的具体动作选择与因果状态保持问题；Network Gate 没有泄漏，也没有替模型改写。

只有 route120、Full90 和同条件确认复跑全部达到预注册门槛后，才能把当前路径升级为默认主动 Harness。
