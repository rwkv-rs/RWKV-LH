# RWKV-LH 长程 Agent 设计

## 1. 目标与边界

RWKV-LH 解决的是“模型需要在较长时间内完成多个互相依赖的真实动作”这一类问题，而不是一次问答。

系统必须保证：

- 原始目标和硬约束不会在长时间执行中漂移；
- 任务进度不依赖模型上下文记忆；
- 副作用、验证结果、失败和恢复动作可以审计；
- 模型说 `done` 不等于任务完成；
- 中断后从持久状态继续，而不是重新执行全部任务；
- temperature 和 seed 是每个模型请求的属性，而不是进程级固定参数。

仓库不包含网页检索流程、答案 Judge、检索 benchmark 或前端。外部能力通过显式 Harness Action 注入。

## 2. 执行架构

```mermaid
flowchart TD
    Q["User Goal + Scoped Workspace"] --> GP["RWKV Goal Parser"]
    GP --> G["Immutable Goal State + Digest"]
    G --> PL["RWKV Task Decomposition"]
    PL --> TG["Task Graph / Ledger"]
    TG --> EC["Single Execution Controller"]
    EC --> WM["Working Memory Projection"]
    WM --> AS["RWKV Action Selection"]
    AS --> AH["Scoped Action Harness"]
    AH --> DV["Deterministic Validation"]
    DV -->|"Pass"| TG
    DV -->|"Retryable"| EC
    DV -->|"Material Failure"| RP["RWKV Replan"]
    RP --> TG
    TG -->|"Required Graph Complete"| CV["Cross-validation"]
    CV --> FW["RWKV Final Writer"]
    EC <--> DB["SQLite + Checkpoints + Event Log + Lease"]
```

RWKV 负责 Goal Parse、Task Graph、Action Selection、语义交叉验证、失败后的 Replan，以及最终用户输出。

确定性系统负责保存 Goal、校验 DAG、在副作用前创建 Attempt、限制作用域、执行动作、运行 verifier、管理恢复与投影有界工作记忆。确定性系统不得替模型改写最终答案。

## 3. 持久状态

SQLite 是默认状态存储，`StateStore` Protocol 保留替换数据库实现的边界。主要表包括：

- `runs`：当前 RunState、goal digest、状态和 revision；
- `task_index`：任务节点的可查询索引；
- `checkpoints`：关键里程碑快照；
- `events`：模型请求、动作、验证、失败、恢复和状态变更；
- `run_leases`：保证同一个 run 同时只有一个 Controller owner。

写入使用 revision compare-and-swap。旧 revision 不能覆盖新状态。Goal 在创建时计算 digest，恢复和执行前都会检查。大输出保存为 artifact，由相对路径和 SHA256 引用。

## 4. Task Graph 与 Attempt

每个 TaskNode 记录 task id、依赖、GoalCriterion 绑定、动作、完成条件、重试策略、尝试记录、输出引用、错误和 supersede 关系。

状态包括 `pending`、`running`、`completed`、`failed`、`blocked` 和 `superseded`。

每次动作执行都有独立 Attempt。Attempt 在副作用之前持久化，并记录 action fingerprint 与 idempotency key。发生崩溃时：

- 只读动作可以安全重试；
- 幂等动作可以重新执行并验证；
- 无法确认结果的非幂等动作不会自动重复，而是进入 blocked 状态。

## 5. Working Memory

完整历史不进入每次 prompt。`WorkingMemoryBuilder` 只选择不可变 Goal、当前 Task、依赖输出、显式 memory reference、相关 evidence、最近一次材料性失败和 Action Contract。

RWKV 官方 tokenizer 随包提供，用于真实 token 计数。默认总输入预算为 13,600 tokens，为 16K 模型保留输出空间。

## 6. Harness 与扩展能力

核心 Harness 提供文件与 JSON 写入、精确替换、追加、复制、删除、目录创建、文件读取、带行号 evidence binding、`shell=False` 的 argv 命令以及显式 noop。

所有路径必须位于 Goal workspace root。命令使用 argv 数组，不经过 shell。

第三方能力使用 `ActionHarness.register_action()` 或构造参数 `actions` 注入。每个扩展必须通过 `ActionDefinition` 明确：

```text
read_only
side_effect
idempotent
default_timeout
argument_schema
required_postconditions
```

核心包不会扫描或自动加载检索工具。

## 7. 结构化 OpenAI-compatible RWKV runtime

```mermaid
flowchart LR
    MR["Model Role"] --> TP["TemperaturePolicy"]
    TP --> SC["Context-local Sampling"]
    SC --> RC["Typed Request Contract"]
    RC --> HC["Pooled HTTP Client"]
    HC --> API["OpenAI-compatible RWKV API"]
    API --> PR["Typed Response / Error"]
    PR --> EV["Run Event Audit"]
```

模块边界：

- `runtime/settings.py`：环境配置、URL、模型、超时、重试、TLS 和 proxy policy；
- `runtime/sampling.py`：ContextVar 隔离的 temperature、seed、task id 与 lane；
- `runtime/protocol.py`：请求、响应、usage、health 数据结构和错误分类；
- `runtime/openai_compat.py`：线程隔离 Session、连接池、UTF-8 JSON、有限重试和 OpenAI-compatible endpoint。

可重试错误仅限连接错误、超时以及明确的 408/425/429/5xx。协议错误和普通 4xx 不会用重复请求掩盖。

## 8. Request-level temperature

| Request type | 默认 temp | 目的 |
| --- | ---: | --- |
| goal_parse | 0.03 | 稳定保留目标约束 |
| task_decomposition | 0.18 | 允许有限策略空间 |
| tool_action | 0.05 | 稳定结构化动作 |
| validation_cross_check | 0.03 | 保守判断证据 |
| replan | 0.28 起 | 在材料性失败后改变策略 |
| final_answer | 0.05 | 忠实表达已验证结果 |

同一协议输出失败最多做一次同温度格式纠正。只有重复策略失败才提高 replan 温度；出现新证据时重新从基础 replan 温度开始。采样参数通过 ContextVar 进入 HTTP payload，并在请求返回后恢复。

## 9. Completion 与 Validation

任务完成条件是 required completion criteria 全部通过。Verifier 覆盖文件状态与内容、JSON、命令退出码、哈希、HTTP 字段、evidence binding、memory reference 和 model cross-check。

Run 完成还要求所有 required GoalCriterion 被 active completed tasks 覆盖。最终文字只在这一状态之后调用 RWKV 生成。

## 10. 测试定位

`LH-Control-30` 是 Architecture Regression。它用确定性 fixture 检验状态机、Controller、Verifier、恢复和采样隔离，不能代表 RWKV 自主完成 30 个任务。

真实 RWKV E2E 测试必须满足：

- 仅提供用户目标、初始 workspace 和允许工具；
- 不提供答案、Task Graph、动作序列或 replan 路径；
- 最终由独立、不可见的 acceptance checker 检查 observable result；
- 报告保存模型输入输出、温度、工具调用、重试、replan、恢复和最终验证。
