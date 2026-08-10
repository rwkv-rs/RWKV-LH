# RWKV-LH 正式使用就绪审计（2026-08-10）

## 结论

RWKV-LH 已经具备进入 **RWKV 正式 canary 阶段** 的工程基础，但还不能标记为生产可用。确定性运行时、题库、构建、隔离 verifier 和真实 vllm-rwkv 链路均已运行；最小真实任务的目标产物通过了独立外部验收，但 Agent 尚未稳定到达严格完成态。

当前状态必须如实表述为：

- 确定性运行时：可用，68 项测试通过。
- E2E 题库：42 题 schema/checker 校验通过。
- verifier 隔离：Linux bubblewrap 可用，缺失时 fail closed。
- Python 包：sdist 与 wheel 构建通过。
- vllm-rwkv：`/models` 健康检查和真实 generation 均已执行。
- 真实最小 canary：外部产物验收通过，严格 Agent 完成失败。
- 正式级别：canary，不是 production。

## 不可变原则：只为 RWKV 服务

RWKV-LH 的产品、架构、题库和运行时只为 RWKV 建立。后续设计评审必须先回答“这是否直接改善 RWKV 的长程执行”；不能用“让所有模型都能接入”作为改动理由。

允许：

- 针对 vllm-rwkv 已实现参数和真实返回行为调整采样与错误语义。
- 针对 RWKV tokenizer、16K 上下文和续写特性做预算、截断恢复与状态投影。
- 保留并改进当前 RWKV 专用 Goal、Plan、Action、Verification、Replan 和 Final 协议。
- 用确定性 Controller、ledger、checkpoint 和隔离 verifier 补足模型不应承担的可靠性责任。
- 参考其他项目已经验证过的持久化、恢复、隔离和 CI 思想，并在本项目内独立实现。

禁止：

- 增加通用 provider 层、AgentAdapter、模型路由或多模型 fallback。
- 为兼容其他模型改写当前精选的提示词格式。
- 用其他模型生成计划、做 Judge 或在 RWKV 失败时代替 RWKV 完成任务。
- 把 LongHorizon-Harness、LangGraph、Temporal 或 Harbor 作为运行时依赖。
- 为追求通用 benchmark 分数削弱 RWKV 专用状态、采样或 verifier 边界。

## 与参考项目的对比

| 项目 | 它的主要定位 | RWKV-LH 当前对应能力 | 可以借鉴 | 明确不做 |
| --- | --- | --- | --- | --- |
| [LongHorizon-Harness](https://github.com/AMAP-ML/LongHorizon-Harness) | 通用长程 Agent harness，强调角色分离、验证后持久化和运行诊断 | RWKV 专用语义阶段、单一 Controller、持久 Task/Attempt/Memory/Event、独立隐藏验收 | 启动 doctor、只让已验证事实进入最终状态、诊断报告 | 通用模型后端、AgentAdapter、模型混跑、桌面插件生态 |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | graph super-step checkpoint、thread、replay、pending writes | SQLite checkpoint、revision CAS、lease、显式任务图和 resume | 每个逻辑模型调用的 durable result、并行分支成功结果不重做、checkpoint 压缩 | 引入 LangGraph graph/runtime 或按其 API 重写当前 Controller |
| [Temporal](https://docs.temporal.io/) | crash-proof workflow、Activity retry、幂等与恢复语义 | 动作执行前持久化 Attempt，区分 read-only/side-effect/idempotent，未知副作用禁止盲重试 | 稳定 logical call id、结果 read-back、退避/circuit breaker、compensation 可观测性 | 引入 Temporal server/worker，或声称网络请求具有真正 exactly-once |
| [Harbor](https://github.com/harbor-framework/harbor) | 可复现 Agent 环境、评测与训练基础设施 | 42 题 catalog、独立 acceptance、私有输出、bubblewrap worker | 分层 CI、标准结果 artifact、可复现实验元数据 | Harbor 兼容层、通用任务容器取代 RWKV-LH verifier 边界 |

RWKV-LH 的差异不是“规模更小的通用 Agent 框架”，而是 **RWKV 专用语义运行时 + 确定性可靠执行内核 + 真隔离 benchmark**。参考项目用于校准可靠性，不定义本项目的产品方向。

## 真实 canary 观察

### 第一次运行

`E2E-B01` 在空工作区上失败。RWKV 正确理解目标，但把“检查工作区”拆成前置任务；当时 Harness 没有目录发现动作，模型只能错误选择读取不存在的 `greeting.txt`。随后 `failure_analysis` 的 `reason` 重复直到输出上限，JSON 未闭合，运行中断。

已实现：

- 增加只读、作用域受限、条目数有界的 `list_directory` 动作。
- 只对 `failure_analysis` 和 `validation_cross_check` 启用严格的尾部截断决策恢复；仅在服务明确返回 `finish_reason=length`、且完整字段可安全解析时恢复，不放宽普通 JSON 协议。

### 第二次运行

同一 `E2E-B01` 只重跑一次。RWKV 成功列出空目录、创建 `greeting.txt`，独立隐藏 verifier 确认内容精确等于 `Hello, RWKV-LH!\n`，因此外部验收通过。

严格 Agent 状态仍失败，原因有两层：

1. `write_file` 的过程 verifier 当时只验证 `file_exists`。必需语义交叉检查据此拒绝“精确内容已验证”，形成正确方向的严格检查，但暴露了确定性证据不完整。
2. 随后的 `failure_analysis` 请求由推理端关闭连接，客户端只能判定结果未知并中断，不能安全猜测模型是否已经生成完成。

已实现第一层修复：`write_file` 现在强制同时包含 `file_exists` 和精确 `file_content`，防止“文件存在”冒充“写入内容正确”。第二层仍是正式阶段 P0。

## 当前缺陷与优先级

### P0：阻止正式套件稳定运行

1. **模型调用缺少 durable result journal。** 当前会持久化请求开始、返回或结果未知事件，但 crash/断连发生在服务已生成、客户端未收到结果时，无法按稳定 logical call id 做查询或恢复。需要在 vllm-rwkv 能力范围内设计 request read-back；服务不支持时必须保持 unknown 并中断，不能谎称 exactly-once。
2. **推理端缺少正式 doctor 与熔断。** smoke 已验证 endpoint/model，但还应在开跑前记录 vllm-rwkv 版本、模型标识、上下文上限、rapid-sampling 能力和一次最小协议响应；连续断连应触发 circuit breaker，而不是继续消耗题目预算。
3. **最小 canary 尚未严格通过。** 在新的精确内容 verifier 下，必须由一次新的、明确授权的正式运行证明 B01 能到达 Agent completed + external accepted；本次审计不通过重复重跑掩盖失败。

### P1：进入基础题队列前应完成

1. **规划效率约束不足。** 一个单文件任务被拆成 4～5 个任务和 21 次模型请求。需增加 RWKV 专用 plan 预算审计和重复前置任务检测，但不改写提示词格式。
2. **语义交叉检查的证据粒度需要收敛。** 必须保留它来阻止模型用自证式 verifier 过关，但输入应优先包含精确的确定性证据、artifact hash 和 criterion 绑定，减少“外部结果正确、内部证据不足”的假阴性。
3. **上下文与 checkpoint 需要长期压缩策略。** 当前有界工作记忆可以裁剪请求上下文，但 SQLite 中的完整 prompt/output/event 会持续增长；LH11/LH12 前需要定义保留、摘要、归档和可审计恢复边界。
4. **CI 需要分级消耗。** 正式 self-hosted RWKV job 当前在 health 后直接启动 LH12；应调整为 health → `E2E-B01` → 小型基础队列 → LH12，任何前置门槛不通过时都不启动更昂贵的套件。

### P2：生产运维能力

1. 运行级超时、退避、熔断状态和人工恢复原因需要出现在 status/report 中。
2. 需要聚合 request/token/latency、replan、协议恢复、unknown outcome 和 verifier 假阴性指标。
3. 需要 checkpoint schema migration、长运行数据库维护和故障注入矩阵。

## 客户端不能伪造的能力

以下能力只有 vllm-rwkv 实际支持时才能启用：

- 跨请求持久 RWKV recurrent state。
- 服务端 seed/确定性 replay。
- thinking budget 或未实现的采样参数。
- 推理响应丢失后的服务端 request 查询。
- 网络和外部副作用的真正 exactly-once。

RWKV-LH 对这些能力的原则是：探测、记录、fail closed；不通过通用模型或客户端猜测进行模拟。

## 正式晋级门槛

1. `uv run pytest -q`、42 题 validate-only、`rwkv-lh-control`、`uv build` 全部通过。
2. runtime doctor 记录真实 vllm-rwkv 能力，最小协议请求通过。
3. `E2E-B01` 连续的正式运行必须达到 Agent completed、external accepted、无 unknown model outcome。
4. 再运行小型基础队列，确认创建、读取、修改、命令验证和 JSON 操作。
5. 通过后才启动 LH12；LH12 artifact 必须保留审计事件、隔离元数据、严格结果和外部结果。
6. 任何阶段失败都停在该门槛，不用重复运行或其他模型绕过。

达到第 3 项可标记为 **RWKV canary ready**；达到第 4 项可标记为 **RWKV beta**；只有长程恢复、外部状态和隔离验收稳定后才讨论 production。
