# RWKV-LH 全代码架构图

更新时间：2026-08-31（Asia/Shanghai）
代码基线：当前工作树 `chase/hybrid-product-v1`（包含未提交实验改动）

本文依据 `rwkv_lh/`、`scripts/`、`benchmarks/`、`tests/` 与产品前端源码生成。盘点范围为
332 个 Python 模块、37 个 Shell 脚本、2 个 JavaScript、2 个 CSS、2 个 HTML 和 1 个 C++
文件，共 376 个源码文件、120121 行。模型权重、数据集和历史实验结果作为数据面统计，不作为源码模块展开。

图例：蓝色为当前产品主链，紫色为可选 Contract Graph 控制面，绿色为持久化/证据，灰色为仓库保留但当前部署不启用的兼容或实验链。

## 1. 整体架构

```mermaid
flowchart TB
    classDef active fill:#e8f1ff,stroke:#2563eb,color:#111827,stroke-width:1.5px
    classDef optional fill:#f3e8ff,stroke:#7c3aed,color:#111827,stroke-width:1.5px
    classDef state fill:#e8fff1,stroke:#15803d,color:#111827,stroke-width:1.5px
    classDef legacy fill:#f3f4f6,stroke:#6b7280,color:#374151,stroke-dasharray:5 5
    classDef external fill:#fff7e6,stroke:#d97706,color:#111827,stroke-width:1.5px

    subgraph ENTRY[产品入口与生命周期]
        direction LR
        UI[Goal Studio<br/>goal_web_assets + web_ui]:::active
        CLI[rwkv-lh CLI<br/>start / resume / status]:::active
        PRO[ProactiveStore + Worker<br/>trigger / approval / lease / retry]:::active
        E2E[rwkv-lh-e2e<br/>冻结套件与故障注入]:::legacy
        UI --> WW[web_worker 独立进程]:::active
        PRO --> BUILD
        CLI --> BUILD
        WW --> BUILD
        E2E -.同一核心组件.-> BUILD
    end

    BUILD[build_product_controller<br/>按不可变 Goal policy 装配一次]:::active
    GOAL[GoalState<br/>原始请求 / workspace / constraints / runtime_policy]:::state
    BUILD --> GOAL
    GOAL --> PROFILE[Executor profile 绑定<br/>offline G3 或 network G6；run 内不切换]:::active
    GOAL --> RETPOL[Retrieval / egress policy]:::active
    GOAL --> SUPMODE{supervisor mode}:::active

    subgraph CONTROL[控制与调度]
        direction TB
        SUPMODE -->|none| CTRL[LongHorizonController<br/>直接 Action 循环]:::active
        SUPMODE -->|contract_graph| SUP[OpenAI-compatible<br/>Strong Planner / Reviewer]:::optional
        SUP --> CG[ContractGraph<br/>义务 / DAG / assertion / result capsule]:::optional
        CG --> CAP[capability_projection v3<br/>语义校验 + ready batch + 作用域冲突检查]:::optional
        CAP --> POOL[ThreadedRWKVAtomPool<br/>隔离 atom workspace / 事务合并]:::optional
        POOL --> CHILD[每个 atom 的子 Controller<br/>固定 action budget / read-write roots]:::optional
        CHILD --> MODEL
        POOL --> REVIEW[执行证据 Review<br/>及 Final presentation Review]:::optional
        REVIEW --> CG
        CG --> FINALIZER[RWKV finalizer atom]:::optional
        FINALIZER --> MODEL
    end

    CTRL --> MODEL

    subgraph RWKV[RWKV 核心双 lane]
        direction LR
        MODEL[LongHorizonModel<br/>请求末端输入 + progressive disclosure]:::active
        SIN[selector input<br/>25 类短菜单 + 有界进度]:::active
        SCLIENT[NetworkExactToolSelectorClient<br/>HTTP + 身份/摘要校验]:::active
        SSVC[本地 Selector Service :29621<br/>持久 WKV state]:::external
        SRWKV[2.9B RWKV S60<br/>Hidden mean+last]:::external
        HEAD[h64 MLP head<br/>完整 logits + eligible raw argmax]:::external
        SELCOMMIT[exact_tool_selection_committed<br/>一个 operation]:::state
        DISCLOSE[只披露该 operation 的完整 schema]:::active
        SESSION[ModelSession<br/>commit / rollback / rollover]:::active
        ECLIENT[OpenAICompatibleRWKVClient<br/>prompt replay transport]:::active
        ERWKV[远端 13.3B RWKV Executor :18075<br/>G3/G6 initial-state profile]:::external
        RAW[原始 generation<br/>bytes / token IDs / SHA / finish reason]:::state
        PARSE[model_io parser<br/>仅归一化调用外壳]:::active

        MODEL --> SIN --> SCLIENT --> SSVC --> SRWKV --> HEAD --> SELCOMMIT
        SELCOMMIT --> DISCLOSE --> SESSION --> ECLIENT --> ERWKV --> RAW --> PARSE
        PARSE -->|参数不合法| REJECT[typed protocol rejection<br/>原输出保留，精确错误回注]:::state
        REJECT --> MODEL
    end

    PROFILE --> SESSION

    subgraph EXEC[统一 Action Harness]
        direction LR
        REG[ActionDefinition 唯一注册表<br/>schema / policy / handler / recovery]:::active
        VALIDATE[机械 schema、scope、policy 校验]:::active
        START[action_started 预提交]:::state
        LOCAL[工作区文件与搜索<br/>读写 / digest / bind evidence]:::active
        CMD[bwrap 命令沙箱<br/>check_command / run_command]:::active
        DET[确定性工具<br/>calculator / date_diff / current_time]:::active
        NETGATE[Network + provenance gate]:::active
        RET[Retrieval kernel<br/>provider → fetch → clean → chunk]:::active
        EVID[ExternalEvidenceEnvelope<br/>snapshot digest + exact spans]:::state
        FINISH[action_finished<br/>ActionResult + artifact revisions]:::state

        PARSE --> VALIDATE
        REG --> VALIDATE --> START
        START --> LOCAL --> FINISH
        START --> CMD --> FINISH
        START --> DET --> FINISH
        START --> NETGATE --> RET --> EVID --> FINISH
    end

    RETPOL --> NETGATE
    FINISH --> OBS[精确 Observation 投影]:::active
    OBS --> MODEL
    PARSE -->|final_answer| OUT[原样 RWKV Final]:::active

    subgraph AUTH[唯一事实源与恢复]
        direction LR
        EVENT[CausalEvent v2<br/>append-only parent/cause/subject/digest]:::state
        FOLD[RunState.rebuild_projection<br/>actions / artifacts / final / failure budget]:::state
        SQL[LongHorizonStore<br/>SQLite runs/events/checkpoints/action_index/leases]:::state
        CACHE[ModelCheckpoint transcript<br/>transport cache，不是业务 authority]:::state
        SNAP[retrieval snapshots / atom workspaces / raw journals]:::state
        VIEW[trace_projection<br/>CLI / Web / benchmark 只读视图]:::state

        EVENT --> FOLD --> SQL --> VIEW
        CACHE --> SQL
        SNAP --> SQL
    end

    GOAL --> EVENT
    SELCOMMIT --> EVENT
    START --> EVENT
    FINISH --> EVENT
    REVIEW --> EVENT
    OUT --> EVENT
    EVENT --> CTRL
    VIEW --> UI
    VIEW --> CLI
    OUT --> UI
    OUT --> CLI

    subgraph RETIRED[保留源码但不在当前产品部署主链]
        direction LR
        ROUTER[0.4B State Router<br/>protocol / MLP / WKV projection / HTTP]:::legacy
        SHADOW[ShadowController<br/>显式 policy 才运行；influence=false]:::legacy
        NATIVE[NativeRWKVModelSession<br/>需服务端完整 durable-state capability]:::legacy
        OLD[旧 supervisor 策略<br/>plan-review / online_microtask / parallel_atoms]:::legacy
        ASSET[旧 web_assets 与旧 selector 协议/heads]:::legacy
        ROUTER --> SHADOW
    end

    BUILD -.兼容显式 shadow.-> SHADOW
    SHADOW -.包裹但不改变结果.-> CTRL
    SESSION -.服务能力满足时才选用.-> NATIVE
    E2E -.实验入口.-> OLD
```

## 2. 单次 Action 的真实调用时序

```mermaid
sequenceDiagram
    autonumber
    participant C as Controller
    participant S as 2.9B Selector Service
    participant DB as CausalEvent / SQLite
    participant E as 13.3B Executor Session
    participant H as ActionHarness
    participant W as Workspace / Retrieval

    C->>DB: load + fold + 校验 Goal/projection digest
    C->>S: request-last selector input、eligible labels、父 selector state
    S->>S: RWKV advance → Hidden(mean+last) → MLP logits → eligible raw argmax
    S-->>C: operation + 全 logits + model/head/profile/state identity
    C->>DB: exact_tool_selection_committed
    C->>E: 单一 operation schema + 当前执行要求
    E-->>DB: 先保存 raw generation 与 checkpoint candidate
    C->>C: parser 外壳归一化 + ActionDefinition 参数校验
    alt 参数或协议无效
        C->>DB: protocol_rejection_recorded；不执行 Action
        C->>E: 原错误 + 同一 operation 精确 schema
    else 有效工具调用
        C->>DB: action_started
        C->>H: execute exact operation(arguments)
        H->>W: workspace sandbox / deterministic / network transaction
        W-->>H: ActionResult + artifact/evidence
        H-->>C: 原始、结构化 observation
        C->>DB: action_finished + artifact revisions
        C->>E: bounded exact observation
    else final_answer
        C->>DB: run_completed + exact raw final
    end
```

关键点不是“Controller 帮模型做决定”，而是它只负责提交边界：Selector 决定 operation；Executor
决定全部显式参数、是否继续以及 Final；Harness 只验证并执行已经提交的调用。

## 3. Contract Graph 可选链

```mermaid
flowchart LR
    R[不可变请求 + workspace manifest + operation catalog] --> P[Strong Planner]
    P --> G[revision 0 obligations<br/>追加式 graph nodes]
    G --> V[contract_validation<br/>capability projection / DAG / scope / budget]
    V --> B[ready nodes 分批<br/>无冲突可并行]
    B --> I[隔离 atom workspace]
    I --> A[每个 atom 运行完整 Selector→Executor→Harness 循环]
    A --> X{atom contract 完整？}
    X -->|否| D[丢弃隔离变更 + result capsule]
    X -->|是| M[事务合并声明写根 + result capsule]
    D --> Q[Strong Reviewer]
    M --> Q
    Q -->|证据缺口| G
    Q -->|execution obligations 满足| F[RWKV finalizer atom]
    F --> PR[独立 presentation review]
    PR -->|PASS| O[交付原样 RWKV Final]
    PR -->|返修| G
```

Strong model 只编译义务图和审核公开证据；具体 operation、参数、实际执行推进与 Final 文本仍属于
RWKV。Controller 的 assertion evaluator、作用域检查、写根覆盖和事务提交都是确定性边界，不生成业务内容。

## 4. 状态与数据权威关系

```mermaid
flowchart TB
    D[CausalEventDraft] --> C[CausalEvent v2<br/>sequence + parent + cause + subject + payload schema + digest]
    C --> L[append-only causal_order / causal_records]
    L --> F[RunState.rebuild_projection]
    F --> P1[actions / active_action]
    F --> P2[tool selections / decisions / lane heads]
    F --> P3[artifact heads / revisions]
    F --> P4[status / final / failure budgets / errors]
    P1 --> PD[projection digest]
    P2 --> PD
    P3 --> PD
    P4 --> PD
    PD --> S[(long_horizon.db)]
    S --> LOAD[load / crash recovery]
    LOAD --> L

    MC[ModelCheckpoint transcript/native metadata] --> TC[传输缓存]
    RS[Retrieval snapshot] --> RC[网络事务恢复缓存]
    AW[Atom isolated workspace] --> AC[事务提交候选]
    TC --> S
    RC -.由 action event 引用.-> L
    AC -.成功后才合并.-> P3
```

`RunState` 的可变字段不是第二份事实；保存和加载都会从事件链重新 fold 并校验摘要。模型 transcript、
Selector 动态 WKV state、网络 snapshot 和 atom workspace 分别解决传输或副作用恢复，但都不能单独宣布任务完成。

## 5. 工具面

当前稳定 Selector 分类空间为 25 类：23 个产品 operation、`final_answer` 与 `ABSTAIN`。23 个产品
operation 由一个注册表机械投影：

| 类别 | Operation |
|---|---|
| 工作区读取/证据 | `list_directory`, `search_text`, `read_file`, `read_json`, `file_digest`, `bind_evidence` |
| 工作区变更 | `write_file`, `write_json`, `patch_json`, `replace_text`, `remove_line`, `append_file`, `make_directory`, `copy_file`, `move_file`, `delete_file` |
| 本地进程 | `check_command`, `run_command` |
| 确定性能力 | `calculator`, `date_diff`, `current_time` |
| 外部只读证据 | `web_search`, `connector_lookup` |

`noop` 仍存在于基础 Harness 注册表，供兼容/控制用例使用，但不在冻结的 23 个产品 operation 分类中。
网络工具是否 eligible 由不可变 retrieval policy 机械过滤；注册工具不等于授权执行。

## 6. 离线训练、评测与发布闭环

```mermaid
flowchart LR
    T[真实 trace / 历史 residual / 固定来源] --> G[scripts/generate_*<br/>数据构建、去重、manifest]
    G --> DS[data/datasets<br/>train / dev / locked / source hashes]
    DS --> ST[Selector head training_v2<br/>或远端 RWKV state tuning]
    DS --> RT[历史 State Router training]
    ST --> ART[head / initial-state profile / vLLM artifact]
    RT --> RART[router head / WKV projection<br/>当前不部署]
    ART --> SRV[Selector Service / Executor Service]
    SRV --> E2E[run_rwkv_e2e_benchmark]
    BENCH[benchmarks tasks + acceptance] --> E2E
    E2E --> ISO[benchmark_verifier<br/>隔离验收 + fault injection]
    ISO --> EXP[data/experiments<br/>protocol / manifest / raw / metrics]
    TEST[116 个 test 模块] --> REG[结构、全流程、边界与历史回归]
    EXP --> DEC{预注册门是否通过}
    REG --> DEC
    DEC -->|是| DEPLOY[runtime stack artifact identity + health attestation]
    DEC -->|否| HOLD[保留结果，不进入产品绑定]
```

脚本层的 127 个 Python 模块与 37 个 Shell 文件主要承担四类职责：数据生成/定稿、远端 state tuning
准备与运行、候选验证/比较、冻结 E2E/能力阶梯执行。它们不进入单次产品 Action 的在线语义链。

## 7. 代码模块索引

| 层 | 主要代码 | 责任边界 |
|---|---|---|
| 产品装配 | `product_runtime.py` | 从已持久化 Goal policy 构造唯一 Controller、Harness、Selector、Supervisor 和 atom pool |
| 控制循环 | `controller.py` | 恢复、边界提交、调度、失败预算、Contract Graph/兼容策略；不补业务答案 |
| RWKV 语义面 | `model.py` | 双 lane handoff、progressive disclosure、Observation 回注、terminal answer |
| 会话与 wire | `model_session.py`, `model_io.py`, `tokenizer.py`, `token_budget.py`, `chunks.py` | checkpoint、commit/rollback、prompt replay/native 选择、调用语法与上下文预算 |
| 执行面 | `harness.py`, `operation_contracts.py` | ActionDefinition 注册、schema/scope、sandbox、文件/命令执行、恢复 |
| Selector | `exact_tool_selector/`, `inference/vllm_rwkv.py` | 输入协议、HTTP client/service、RWKV hidden/WKV state、head、logits、训练与覆盖验证 |
| Executor transport | `runtime/openai_compat.py`, `runtime/protocol.py`, `runtime/executor_profiles.py`, `runtime/sampling.py` | OpenAI-compatible 请求、错误分类、G3/G6 profile 一次性绑定、采样审计 |
| Strong control plane | `supervisor.py`, `supervisor_openai.py`, `contract_graph.py`, `contract_validation.py`, `capability_projection.py` | Planner/Reviewer 协议、义务图、typed assertions 与能力投影 |
| 并行原子 | `atom_execution.py`, `parallel_atoms.py` | atom contract、写根覆盖、隔离执行、依赖交接与事务合并 |
| 检索 | `retrieval/` | policy/provenance、providers、fetch/clean/chunk/snapshot、exact evidence contract 与投影 |
| 权威状态 | `schema.py`, `store.py`, `trace_projection.py` | CausalEvent、确定性 fold、SQLite 事务/租约、只读产品视图 |
| 主动任务 | `proactive.py` | trigger、job、approval、lease fence、heartbeat、退避、dead-letter、通知、workspace 串行化 |
| UI | `web_ui.py`, `web_worker.py`, `goal_web_assets/` | 本地 HTTP/API、每 run 独立 worker、状态/trace/files/export；不创建第二执行路径 |
| 部署 | `runtime/stack.py`, `scripts/manage_runtime_stack.py` | 本地进程所有权、远端 tunnel、Selector/Web/worker 启停与身份健康证明 |
| 历史/旁路 | `state_router/`, `inference/router_server.py`, `web_assets/` | 0.4B Router、shadow 与旧 UI；当前部署关闭，不得影响主链 |
| 评测 | `benchmark_verifier.py`, `scripts/run_rwkv_e2e_benchmark.py`, `benchmarks/`, `tests/` | 冻结任务、隔离验收、故障注入、源码/输出 manifest 与回归 |

## 8. 当前部署边界

- 当前产品装配只公开 `none` 与 `contract_graph` 两种 supervisor mode；Controller 中的旧
  plan-review、`online_microtask`、`parallel_atoms` 仍供历史 trace 和实验 runner 使用。
- 当前部署为本地 2.9B Selector、远端 13.3B Executor、可选外部 Strong Planner/Reviewer，以及本地
  Harness/Web/proactive worker。0.4B State Router 不在进程拓扑中。
- `ModelSession` 已实现 native recurrent-state 适配器，但当前 OpenAI-compatible Executor 未声明完整
  durable state API，因此实际选择可审计的 `prompt_replay`；初始 G3/G6 state profile 仍按请求绑定并校验。
- 产品 UI 使用 `goal_web_assets/`；`web_assets/` 是保留的旧界面资源。
- 这张图表示代码职责和真实调用权威，不表示能力已达到发布门。当前真实三题 Agent canary 仍为
  completed/external/strict `0/3`，联网检索组件通过不等于整体 Agent 闭环通过。
