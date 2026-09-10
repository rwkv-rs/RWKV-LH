# 工程、模型、环节接入与错误传播审计 R1

审计日期：2026-09-10；被审源码：`2e998537395b11b73dd30b60a9dbdd5eeaf406f9`。本轮按 owner 要求分析当前项目，未改生产代码、角色协议或训练规则，未新增 Agent 采集或角色训练。本轮证据清单为同目录 `EVIDENCE_SHA256.json`，同时绑定探针脚本和引用的原始报告。

先报告 Agent 结果：最近完整 REALPROJECT 官方 R3 为 **Strict 0/12、completed 0/12、mutation 0、动作 43**；UltraData 官方 R6 为 **Strict 0/3、completed 0/3、mutation 3、动作 6**。合并为 **Strict 0/15、completed 0/15、mutation 3、动作 49**。终止原因：8 题重复成功但无进展，3 题工具/参数协议拒绝，2 题 Step Auditor 协议拒绝，1 题 Native 请求结果未知，1 题重复命令执行失败。原始评分保持不变，最后一类涉及的二进制入口缺陷已在上一轮修复，但尚未重跑 Agent，不能据此宣布题目通过。

## 一、工程实现缺陷及能力缺口

本轮确认 **4 项代码缺陷、2 项设计/能力缺口、1 项根因未明的运行故障**，共 7 个待处理事项。这是当前证据支持的下限，不是穷尽整个仓库后保证只剩 7 个错误。E4 与 E7 相关，但分别是可复现的诊断缺陷与未查明根因的实际事故，不应当成同一次事故的两个已证明根因。

| ID | 类别、优先级 | 证据及影响 |
|---|---|---|
| E1 | 代码缺陷，P1 | `check_command` 声明 read_only=true、side_effect=false（`rwkv_lh/harness.py:626`），实际直接复用 `_run_command`（2917），workspace 为可写 bind（2887）；执行层不禁止写入。真实 bubblewrap 探针成功写入 outside.txt，权限检查未报缺口。只读/检查动作可能修改项目，造成权限和事实归属不一致。 |
| E2 | 代码缺陷，P1 | `_run_command_write_scope_gaps` 在命令 success=false 时直接返回（`rwkv_lh/stateful_goal_loop.py:689`）。真实命令先写 outside.txt 再退出 1，声明写范围只有 allowed.txt，文件仍存在且范围检查无缺口。命令失败被记录，但部分写入的越界性质未被检测，影响后续工作区状态。 |
| E3 | 代码缺陷，P1 | `harness.py:2707` 阻塞运行命令；`execute` 的异常分支（1611）只保留异常类型/字符串。命令先打印并 flush 诊断、再超时，ActionResult.output 为空，未保存 TimeoutExpired 的部分 stdout/stderr。错误字符串中的 argv 不是程序实际输出。构建、测试超时后缺失关键修复证据。 |
| E4 | 代码缺陷，P2 | `rwkv_lh/runtime/openai_compat.py:654` 的首次 POST 异常捕获后退出 except 再进入恢复查询。离线生产客户端探针模拟 POST ReadTimeout → GET 404，最终异常图只剩 unknown 和 HTTP 404，最初错误丢失。未知 State 结果不应盲目重复写操作，但需要保留原始故障与恢复查询两个因果事件。 |
| E5 | 能力缺口，P1 | 命令工具没有持久 session、poll/stdin/stop 生命周期；schema timeout 上限 120 秒，每次新建独立 bubblewrap。真实有限时长后台心跳进程在第一动作结束后不继续。无法自然实现启动开发服务器后在后续动作交互，或长任务先返回会话再持续查看。单命令内部启动并验证仍可能做到，因此不等于所有 Web 任务都不可执行。 |
| E6 | 设计耦合，P1 | `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py:47` 枚举几乎全部生产 Python 源码，99 行逐文件要求与当前工作树相同；`statetune_data.py` 冻结会重抽取原 trace。当前只读准入探针对 15/15 来源均因 harness.py SHA 改变拒绝。此门是有意的完整性保护；缺口是没有经验证的生产者版本/协议/行为兼容准入，修执行层也使未变更角色输入的历史候选无法沿用。不能直接取消 SHA 校验或假定这批数据全部兼容。 |
| E7 | 未查明事故，待定位 | RP-CLI-02 Native create 的特定请求收据为 404，原始及后续只读查询均有证据；未取得首次请求的详细原因。不足以断言请求没到服务器、已成功或某一种网络故障。它中断了 1 题，仍未闭环。 |

E1–E3 的实际 Harness 探针与精确生产检查函数结合验证，不是完整 Controller/模型执行；不能倒推为 15 题的已知直接原因。E4 为无联网的生产客户端异常路径探针。E5 为工具能力验证。E6 只读取来源登记、协议和清单，没有读取私有验收程序。详细输出见 `PROBES.json`、`CODING_EXECUTION_PROBES.json`、`NATIVE_ERROR_CAUSE_PROBE.json`。

## 二、模型能力缺陷

当前真实输出支持四类能力缺陷，不能由工具单测或 State 数值一致性替代验收，也不能都称为解析器问题。

1. **工具选择与纠错策略**：需要读取完整文件时选择关键词搜索；0 匹配和反馈到达后仍重复相同操作；改写文件目标下出现 delete_file 选择。
2. **合同与参数遵循**：明确文件目标下输出目录路径；返回未展示工具、错误 JSON/字段；Planner 补丁将新增步骤放到 replace 而非 add。合法合同下的错误输出需要模型改进，不应靠宽松解析吞掉。
3. **程序语义正确性**：Ultra-Code-00001 首次写入的程序采用错误条件和组合公式。独立公开样例诊断 0/4，仅说明该程序错误，不是隐藏验收重评分，也不是所有代码能力的统计准确率。
4. **证据充分性和完成判断**：把找到一行 README 或写入文件成功当成目标完成；错误局部结论让后续阶段从错误前提出发。Step Auditor 有明确实际误判，Final Auditor 尚无当前端到端样本，不能把前者问题直接算给后者。

## 三、链路各环节的接入状态

| 接口 | 当前接入及验证边界 |
|---|---|
| 用户目标 → Planner | 官方 DeepSeek；最新 15/15 初始计划被接受。总计 26 次计划请求、6 次阶段检查请求，0 个强模型请求失败；计划补丁仍有 5 次语义拒绝。调用成功不保证计划质量。 |
| 当前步骤/合同/反馈 → Selector | 2.9B，69 个真实边界、207 次菜单选择；输入接通，但工具策略仍失败。不能把菜单数当独立题数。 |
| Selector 选定工具 → Executor | 13.3B，获得当前工具参数合同、目标及相应执行证据；97 次已返回上下文完成输入字节和 token 核验，模型参数和代码仍可能错误。 |
| Executor 参数 → Harness → 执行事实 | 真实动作已执行；二进制入口修复已回归验证。本轮发现 E1/E2/E3/E5；执行层还不能稳定提供受约束、可持续、保留异常现场的全部能力。 |
| 执行事实 → Step Auditor → 当前步骤反馈 | 49 次已返回上下文核验；同一步修复反馈确实送达。交接正确与审核结论正确必须分开。 |
| 阶段缺口 → Stage Checker → Planner 补丁 | 真实进入 6 次阶段检查；UltraData 中有针对实际错误代码的合理修复。新增步骤的补丁操作仍出现模型错误，已有原反馈修复路径。 |
| 目标覆盖 → Finalizer → Final Auditor | 当前代码和协议入口存在，但最新 15 题均未进入最终两个角色。实际完成回答与最终审计能力未验证，不能报告角色通过率。 |
| 逻辑角色上下文 ↔ Native State | 先前 +2 token 根因已修并通过真实 GPU 精确前缀 State 对齐验证；本轮合并 146 次核验仅对应 Executor 97 + Step Auditor 49 次已返回上下文。它不包含所有角色，也不证明每次生产张量都重新逐元素验过；另有 E7 未确认请求。 |
| 生产 trace → 合格角色数据 → StateTune | 入口已接通，实际 optimizer steps=0。历史候选 81 自动标签、126 待独立复核；跨切分 386 对比较有 113 对超过既定 .95，候选 INVALID；当前另有 E6 的来源准入拒绝。 |

训练问题不是“必须后续角色先全部出现”或“Agent 先达到高分”。Selector 原始边界已出现，现有不足在标签确认、固定回归数据独立性和修复后的来源兼容。保持既定阈值与真实 trace 来源，不以合成角色场景或修改家族身份凑数。未答复的复核来源提议不视为已授权；原逐角色训练授权仍有效。

## 四、各角色的实际错误如何放大

**RP-API-01 的已观测链路**：Planner 要求读取 README → Selector 选 search_text → Executor 在 README.md 内搜索字面 README，仅返回一行 → Step Auditor 标记 evidence_complete，S1 通过 → S2 又在 server.py 内搜索字面 server.py，返回 0 → 修复反馈绑定 S2 并传给 Selector/Executor，但重复无效搜索 → 无进展预算终止。该题初始计划后没有再次调用 Planner，因此不能描述为“未完成被 Controller 自动变成重新规划”。起点是读操作策略不符合目标；放大点是审核把不足证据升级为已完成；恢复失败是反馈已到而策略未变。

**ULTRA-Code-00001 的已观测链路**：Executor 写入错误算法 → Step Auditor 接受 → Stage Checker 指出公开样例错误并要求修复 → Planner 的新步骤 replace 补丁被拒绝并沿原反馈路径修正 → Selector 出现不合适的删除/未展示工具输出，之后又写回相同错误代码 → 重复成功预算终止。此处 Strong 阶段检查发挥了纠错作用，但后续动作策略未有效执行纠正。

角色归责：Planner 的确有补丁语义错误，但最新网关调用未阻断这 15 题；Selector 有工具选择与反馈利用缺陷；Executor 有参数遵循和代码正确性缺陷；Step Auditor 有协议输出及证据判断缺陷；Finalizer/Final Auditor 为未到达，缺陷未知。Controller 的证据传递修复有实证，不代表整个执行与事实管理层已经无缺陷。

## 验证、边界和后续顺序

上一轮完整回归 **1432 passed、0 skipped**；本轮未修改生产代码或测试，新增的是隔离诊断探针，因此没有重跑全部单测。没有读取 Real Agent Holdout V2，没有读取私有验证器程序，没有新训练、重评分或修改评测阈值。4 个代码问题均未在本轮修复，不能标记已解决；上述工程问题也不是一次审计即可证明的全部问题清单。

下一步应先处理执行权限/部分写入与失败证据、Native 原因留存，按通用进程生命周期补齐持续工具操作；明确冻结证据与当前训练协议之间的兼容准入。随后在既定覆盖和数据质量达标后按 Selector → Executor → Step Auditor → Finalizer → Final Auditor 推进 StateTune。持续进程能力可独立推进，不应额外设为 Selector 首轮训练门槛。现有证据不支持因为失败就更换五角色划分；需要修复的是角色间事实语义、执行合同及模型的真实决策能力。

引用来源：

- `../REALPROJECT_OFFICIAL_COLLECTION_R3_20260910/REPORT.zh-CN.md`、`METRICS_OVERVIEW.json`、`RP-API-01.FAILURE_CHAIN_OBSERVATION.json`。
- `../ULTRADATA_OFFICIAL_COLLECTION_R6_20260910/REPORT.zh-CN.md`、`FIRST_WRITE_PUBLIC_SAMPLE_DIAGNOSTIC.json`。
- `../COMMAND_ENTRYPOINT_REPAIR_R1_20260910/REPORT.zh-CN.md`、`NATIVE_CREATE_UNKNOWN_AUDIT.json`。
