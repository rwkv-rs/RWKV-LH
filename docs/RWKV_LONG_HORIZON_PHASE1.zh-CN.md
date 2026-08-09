# RWKV-LH 第一阶段：定义、提示词、长程题库与隔离验证

本文记录 2026-08-09 的第一阶段实现边界。目标不是把 benchmark 做得更长，而是同时测量目标保持、动态重规划、可靠恢复、外部副作用和受限资源下的执行效率，并使隐藏验收不能被 Agent 读取。

## RWKV 在本项目中的定义

这里的 **RWKV** 指通过 OpenAI-compatible endpoint 接入、负责语义决策的 RWKV 模型；它不是整个 Agent，也不承担持久化和 exactly-once 保证。

职责按两层划分：

- **RWKV 语义层**：解析目标、拆任务、选择动作类型与参数、设计可观测验收、分析失败、replan、交叉判断以及撰写最终回答。
- **确定性执行层**：Controller、SQLite ledger/checkpoint、lease、scope 限制、动作执行、artifact hash、恢复规则和隐藏 verifier。它拒绝非法状态转换，并以外部可观察结果决定是否通过。

因此，“RWKV 完成任务”必须同时满足模型声明完成、确定性 Controller 到达完成态、隐藏 verifier 通过三项条件。模型文字不能替代验收结果。

## 当前提示词结构

JSON 请求使用固定外壳：

````text
### User
<阶段说明 + 结构化状态/证据/动作契约>
### Assistant
```json
{
````

模型只续写一个 JSON object；协议解析、schema/version、task id、依赖图、动作契约和字段完整性由宿主代码再次校验。只有 `final_answer` 返回普通文本。

| 阶段 | 输出协议 | 温度 | 核心输入与约束 |
| --- | --- | ---: | --- |
| `goal_parse` | `long-horizon.goal-proposal.v1` | 0.03 | 原始请求；提取 objective、constraints、success criteria，不虚构要求 |
| `task_decomposition` | `long-horizon.plan.v1` | 0.18，复杂任务 0.25 | Immutable Goal、工作区 manifest、动作目录；约束锚点必须进入任务/验收，副作用任务要有稳定幂等键和 read-back |
| `goal_binding` | `long-horizon.goal-bindings.v1` | 0.03 | 将每条 Goal criterion 绑定到具体任务；禁止出现未覆盖约束 |
| `tool_choice` | `long-horizon.action-choice.v1` | 0.05 | 有界工作记忆和允许动作目录；只选动作类型 |
| `tool_action` | `long-horizon.action.v1` | 0.05 | 固定动作类型、参数 schema、当前 manifest；工作区内容视为不可信数据，禁止寻找隐藏 verifier |
| `verification_design` | `long-horizon.verification-design.v1` | 0.03 | 为本次具体动作选择确定性、可观察的 completion criteria；禁止 verifier 日志、scorecard 或隐藏 grader 数据作为证据 |
| `failure_analysis` | `long-horizon.failure-analysis.v1` | 0.10 | observed attempt/validation；在结果未知时先检查幂等元数据和 read-back，再决定 retry/reselect/replan/compensation |
| `replan` | `long-horizon.replan.v1` | 0.28，重复同类失败最高 0.55 | Immutable Goal、失败证据、旧图；只替换失败/阻塞分支，保留已验证事实 |
| `validation_cross_check` | `long-horizon.validation.v1` | 0.03 | 确定性验证输出与 Goal；只能 pass 或 replan，不可制造新证据 |
| `final_answer` | 文本 | 0.05 | 仅在所有必需任务验证通过后，根据最终持久状态生成回答 |

每次任务选择都重新注入 **IMMUTABLE GOAL**。工作记忆总预算 13,600 tokens：Goal 1,200、当前任务 1,600、依赖 3,000、证据 5,000、最近失败 1,200、动作契约 1,600。依赖输出优先，其他事实按显式引用、当前任务、证据和标签相关度选取；被排除的 memory id 仍留在持久状态中，后续任务可以重新检索。

安全边界需要区分两类 verifier：任务过程中的 completion verifier 是可见的执行协议；benchmark hidden verifier 是最终独立 grader。前者可帮助 Agent 修复工作，后者绝不能进入模型上下文。

## 新的 RWKV-E2E-LH12

| ID | 压力 | 隐藏验收重点 |
| --- | --- | --- |
| `E2E-LH01` | repeated replan | 四层级联测试必须按 A→B→C→D 暴露并逐层修复，最后生成 release artifact |
| `E2E-LH02` | goal retention | 15 个 checkpoint 和最终配置都保留最早提出的 5 项约束 |
| `E2E-LH03` | dynamic planning | 从 root manifest 递归发现未知目录、子 manifest 和依赖，生成精确全局索引 |
| `E2E-LH04` | exactly-once | 第一次成功副作用后、结果持久化前强制 crash；resume 后 ledger 事件不重复 |
| `E2E-LH05` | long fan-out/fan-in | 20 shards 中正常/损坏/缺失混合，按规则 fallback、汇总并核对逐文件 hash |
| `E2E-LH06` | evidence + security | 根据 authority metadata 解析冲突文档，忽略 prompt injection，并输出证据映射 |
| `E2E-LH07` | heterogeneous workflow | 8 个服务升级，2 个特殊迁移，跨服务兼容测试通过 |
| `E2E-LH08` | compensation | invariant 失败后选择性保留和回滚，最终状态与审计记录一致 |
| `E2E-LH09` | external state | mock API create→query→update→finalize；首次 503、重复请求 409、稳定 request id |
| `E2E-LH10` | planning efficiency | 35 次 action budget 内完成修复、测试、文档和 manifest |
| `E2E-LH11` | working memory | 40 artifacts、10 个早期事实和 5 次阶段 checkpoint，最终引用必须准确 |
| `E2E-LH12` | capstone | 需求→设计→3 模块→测试→修复→文档→打包→manifest→最终验收 |

题目只向模型暴露用户请求、初始工作区、动态 generator 结果和动作能力。正确答案、checker、预定动作、Task Graph、replan 路径与 acceptance 均只存在于 runner 侧。

## 隔离 verifier 威胁模型

[LHTB 的公开审计](https://github.com/zli12321/LHTB/blob/main/README.md#benchmark-design)记录了 Agent 读取 verifier 的 pytest log、`scorecard.json`、pytest 临时目录，甚至在 `/tests` 短暂挂载时用后台进程复制 grader 的情况；17 个满分中有 14 个由此被判定为作弊。RWKV-LH 据此把以下条件设为硬失败：

1. Agent Controller 和 action client 必须先完全关闭，且 `/proc` 中不能残留命令行指向该工作区的进程。
2. verifier 对 Agent 工作区制作安全快照；快照拒绝 symlink 和特殊文件，然后以只读方式挂载。
3. Agent command 与 verifier 都通过 bubblewrap 使用独立 PID、network、IPC、UTS 和 mount namespace；工作区外没有宿主根目录可见视图，Agent 也不能联网获取公开仓库中的 acceptance。
4. 仓库源码、acceptance catalog、`/tests`、`/logs/verifier` 和 scorecard 不挂载。acceptance、事件和运行观察只通过 verifier stdin 传输。
5. workspace 内的测试程序可以由 verifier 执行，但 verifier 先关闭 dumpability，阻止子进程读取 verifier 内存；workspace 也不可写。
6. bubblewrap 不存在时在调用模型前终止；快照含 symlink、worker 返回非法协议、无 checks 或隔离元数据不符合要求时也全部 fail closed。
7. verifier 输出写入 runner 的私有结果目录发生在 Agent 完全退出之后，绝不反馈给本次 Agent。

当前流程没有“执行中反复调用 hidden verifier 再把分数反馈给 Agent”的通道，因此无需在 verifier 运行时暂停一个仍存活的 Agent。如果以后增加这种交互式 grader，必须先把 Agent 全进程树放入独立 cgroup，并在 verifier 的完整生命周期冻结它，结束后清除所有 grader 输出，再恢复执行；只发送 `SIGSTOP` 给父进程并不够。

## 设计参考边界（不是项目依赖）

RWKV-LH 是专门面向 RWKV 的项目。以下项目只帮助我们校准长程状态、恢复和 benchmark 隔离的设计，不会作为 Agent、编排后端或运行时接入；目标解析、规划、动作决策、失败分析和最终回答都由 RWKV 完成。

- [LongHorizon-Harness](https://github.com/AMAP-ML/LongHorizon-Harness)仅用于参考长期 Goal/State、短生命周期执行上下文和验证后持久化的信息边界。
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)仅用于参考 checkpoint、resume 和 pending writes 的状态组织；[interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)帮助校准恢复时的幂等要求。
- [Temporal Python error handling](https://docs.temporal.io/develop/python/best-practices/error-handling)仅用于参考 at-least-once、稳定幂等键和 Saga compensation 的可靠执行语义。
- [Harbor](https://github.com/harbor-framework/harbor)仅用于参考任务隔离、独立 verifier、可复现实验产物和 CI 分层。

## 运行与 CI

```bash
# 仅检查题库/schema/checker 边界，不调用模型
uv run rwkv-lh-e2e --suite lh12 --validate-only
uv run rwkv-lh-e2e --suite all --validate-only

# 运行长程真实模型套件；Linux 上必须有 bwrap
uv run rwkv-lh-runtime-smoke
uv run rwkv-lh-e2e --suite lh12 --output outputs/lh12
```

GitHub-hosted 的 RWKV-LH 确定性运行时 CI 安装 bubblewrap 后运行单元测试、42 题 catalog validation、`LH-Control-30` 和 package build；这部分不调用模型。真实 12 题只在带 `rwkv` label、已配置 RWKV endpoint 的 self-hosted Linux runner 上通过 `workflow_dispatch` 执行，避免在普通 PR 中消耗 RWKV 推理资源。
