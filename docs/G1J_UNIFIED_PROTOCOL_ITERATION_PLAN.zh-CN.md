# G1J 分角色 Agent：唯一协议、数据来源与验收规范

更新日期：2026-09-07。适用于生产运行、未来生产 trace 数据抽取、评测和测试。与 HANDOFF 冲突时以本规范为准；owner 最新指令优先。

## 1. 唯一协议

每个角色只保留一个协议模块，拥有唯一 `build_prompt_source()` 和 renderer。嵌套的机械进度、目标合同和 gap catalog 也必须调用同模块共享函数。生产、数据抽取和验收不得自行拼接协议字典或保留兼容输入链。

| 角色 | 唯一模块 | schema 后缀 | 构造与渲染 |
|---|---|---|---|
| Selector 2.9B | `selector_intent_v4.py` | selector-intent.v4 | `build_current_progress()` → `build_prompt_source()` → `render_prompt()` |
| Executor 13.3B | `executor_args_v4.py` | executor-args.v4 | `build_target_contract()` / `build_execution_state()` → `build_prompt_source()` → `render_generation_prompt()` |
| Step Auditor 13.3B | `auditor_step_v3.py` | auditor-step.v3 | `build_prompt_source()`（内建 gap catalog）→ `render_prompt()` |
| Finalizer 13.3B | `finalizer_answer.py` | finalizer-answer.v1 | `build_prompt_source()` → `render_prompt()` |
| Final Auditor 13.3B | `auditor_final.py` | auditor-final.v2 | `build_prompt_source()`（内建 gap catalog）→ `render_prompt()` |

模块均位于 `rwkv_lh/goal_state_protocols/`。schema 完整前缀为 `rwkv-lh.g1j-per-stage-state-tuning.`，运行时引用模块的 `INPUT_SCHEMA_VERSION`，不得在调用方拼出身份标签。Executor `render_prompt()` 是相同输入的前缀正文，`render_generation_prompt()` 仅追加同一调用边界，不是另一套输入协议。

角色协议目录不保留旧模块或 identity stub。旧版、未知 schema 和旧独立 Executor 披露/重试格式一律拒绝；历史只能查 Git / GitHub。升级前删除旧模块及其可执行字节码，不允许 vN/vN+1 并存。

### 1.1 Selector 输入

current_progress 精确字段与顺序：

```text
assigned_action_count, successful_action_count, failed_action_count,
last_action, missing_read_roots, missing_write_roots,
workspace_targets, completion_preconditions_satisfied
```

last_action 精确字段与顺序：

```text
operation, status, arguments, error_type, error_message,
result_metadata, observed_roots, mutated_roots
```

- arguments 最多 8 个键，每值最多 160 字符；结构化值仅保留 object/array 大小描述。
- 失败时 error_type/error_message 必填，message 最多 240 字符；成功时为 null。失败不覆盖 observed/mutated root。
- metadata 白名单按顺序为 outcome_type、exit_code、target_kind、entry_count、match_count、byte_count、size_bytes、truncated、changed_path_count。
- workspace_targets 最多 32 条；类型取 `operation_contracts.WORKSPACE_TARGET_KINDS`。
- 网络封装 NetworkSelectorInput 使用 v5，只接受角色 v4。endpoint、menu/role/prompt/target prefix 全部引用角色模块常量。decoder manifest 与运行 attestation 必须匹配当前源码。

### 1.2 强制一致性检查

1. 协议 identity 测试必须枚举目录中的所有角色协议，恰好只有表中五个模块；仅检查一个手工列表的常量不算覆盖。
2. 生产角色输入、单元测试、未来数据抽取只能用共享 builder。scripts/、tests/、temp/ 不得手写 current_progress / execution_state / gap_catalog 等协议结构；负例从有效 builder 结果定点修改。
3. 生产、脚本、测试不导入 temp Python 模块，不依赖旧生成器或旧数据；旧源码与字节码都不得残留为可执行入口。
4. 每行数据的 prompt 必须能由该行绑定的 durable action / boundary 事实通过当前 builder+renderer 逐字节重算；不一致整批拒绝。
5. 运行身份绑定模型、State、协议与 decoder 源码 SHA；引用当前常量，不能只校验同名字符串。

### 1.3 服务器上传与文件身份

owner 已明确服务器禁止使用 Git，只能从本地上传。所有 Git 版本管理及查询均在本地 WSL 完成，包括 clone/fetch/pull、提交、历史和 rev-parse/status；服务器部署、服务启动、健康检查及身份核验均不得执行 Git，也不要求服务器保留 Git 仓库。

本地冻结项目与 engine 源码后，通过 SSH 配合 rsync/SCP 上传。engine 必须有完整源码文件清单，登记相对路径、逐文件 SHA-256，并冻结 manifest 自身 SHA-256；服务核验实际源码与上传清单一致。完整清单用于证明上传的整个 engine 源码身份，不能用少量抽查文件或一个未经文件核验的提交号代替。模型、State、协议及 decoder 身份仍需同时核验。本地实验记录保存本地提交、源码清单、manifest SHA、上传和服务核验事实，形成可复核绑定；清单缺失或不一致时不得通过身份门，也不得回退远端 Git。此处规定验收方式，不代表当前服务已经完成该验证。

### 1.4 Planner 计划规模

owner 于 2026-09-07 明确取消 Planner 步数要求。Planner 按任务需要给出步骤和阶段，不设固定步骤数、阶段数、累计未完成步骤数或依赖步骤数量上限；新增、替换、丢弃与阶段检查输入应完整保留这些步骤。提示词、schema、计划补丁解析、durable plan 应用与阶段检查入口必须一致，不得在下游保留五步拦截或静默截断。

每步仍有一个职责 phase，阶段内步骤独立且根路径不冲突，依赖只能指向更早阶段；义务绑定、字段类型、有效根、证据权威、完成步骤不可改写及非空阶段等语义合同继续生效。模型上下文、输出 token 和执行资源预算独立登记，不把这些资源预算伪装成固定步数要求。规模政策改变后新运行重新冻结，历史输出及成绩保留原始口径，不重评分。

取消计划数量上限不等于模型上下文无限。当前 13.3B 服务窗口为 16,384 tokens，请求必须核对实际输入与登记的输出预算；超出窗口不能静默截断计划、删证据、临时降低预算或伪装为模型完成。任务结束仍由 RWKV 结合目标覆盖和执行证据判断，并通过既有完成校验；资源不足只能明确报告中断或阻塞。

### 1.5 本地 13.3B Supervisor 原生传输

owner 于 2026-09-07 授权 Planner 与 Stage Checker 使用同一现有 13.3B 服务。当前配置如下；`SupervisorAPISettings` 的通用 backend 默认仍是 `openai-compatible`，本地部署必须显式选择原生 profile。

| 配置 | 当前值 |
|---|---|
| `RWKV_LH_PLANNER_BACKEND_PROFILE` | `vllm-rwkv-native` |
| Planner / Stage Checker 模型 alias | `rwkv7-g1j-13.3b-zero-state-capability-ctx16384` |
| 本地 base URL / 远端端口 | `http://127.0.0.1:29613/v1` / `rwkv-8222:18234/v1` |
| `RWKV_LH_PLANNER_MAX_PLAN_TOKENS` | `8192` |
| `RWKV_LH_PLANNER_READ_TIMEOUT` | `240` 秒，两个 Supervisor 角色共用 |
| `RWKV_LH_PLANNER_MAX_CONTRACT_REVIEW_TOKENS` | Stage Checker 保持 `2400` |
| `RWKV_LH_PLANNER_PLAN_CACHE_ENABLED` | `false` |
| `RWKV_LH_PLANNER_FALLBACK_MODELS` | 空 |

原生适配只用于 `goal_plan` / `goal_stage_review`。Planner 仍只输出计划补丁，Stage Checker 仍只审查已完成阶段；Selector、Executor、Step Auditor、Finalizer、Final Auditor 的模型、预算、职责和 State 不变。唯一的角色请求构造与 system prompt 不变，传输模块仅将已有 payload 按 `_render_user_payload` 序列化后包装为下列原生文本：

```text
System✿{system_prompt}✿
User✿{payload_text}✿
Bot✿<think
```

向 `/completions` 发送 `TextCompletionRequest.payload(..., sampler_mode="native")`，不发送 `response_format` / `structured_outputs`，从而避开本部署缺少 `lmformatenforcer` 的约束生成路径。明确传入 temperature 0.1、top_p 1、top_k 0、presence/frequency penalty 0、decay 0.996、stop `✿`、stop token 0、BOS 和返回 token IDs；每次请求显式指定 `zero` / 64 个 `0` 的 State SHA，不继承其他角色的采样上下文、WKV 或 State handle。

响应必须是唯一 choice，`text` 非空且从 `>` 开始，`finish_reason` 严格为 `stop`；`length` 即使伴随完整 JSON 也拒绝。只把本次实际发出的 `<think` prefill 合回原文后交既有严格 JSON decoder，再执行原 GoalPlanPatch / StageReview 合同校验。不得扫描任意 JSON 后缀、补写字段或放宽语义约束。审计保存 raw output、prompt/prefill/output SHA 及返回的 token IDs；IDs 缺失/null不单独否定 JSON，但不能声称已有完整 token trace；已返回的非法 token 类型必须拒绝。缓存身份绑定实际 endpoint、传输参数、预算和 zero 身份，本轮配置仍关闭缓存。

连接探针和使用 mock 审计的 Controller fixture 均不计 Agent 分数、双零噪声或 StateTune 来源。完整源码、测试与连接证据见 [本轮原生适配报告](../data/experiments/VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/REPORT.zh-CN.md)。

## 2. 数据来源与清理规则

旧合成角色数据链已删除，不保留本地归档或 stub，也不得恢复旧生成器以继续训练。旧实验只查 Git / GitHub；当前工作树只保存当前有效数据、隔离验收材料和本轮及后续证据。

### 2.1 唯一生产 trace 流水线

固定模块名 `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py`，已在 `ROLE_TRACE_DATASET_R1_20260907` 实现。当前入口只生成候选审计工件，正式回归冻结与训练仍遵守 §2.2。命令、证据边界及经验见 [使用说明](ROLE_TRACE_DATASET.zh-CN.md)。它遵循：

1. 使用生产 Harness + all-zero 在已冻结的开发范围运行并落盘 LongHorizonStore；可包含 Ladder-10、owner 授权的 `realprojectdevv1` 及已确认生产适配的机制回归。E2E-90 的 LH09 `mock_api` 冲突必须显式处理，不得静默删题；不得读取 Holdout。
2. 遍历 causal_order，以各 assignment / audit boundary 当时之前的 durable facts 重建输入。Selector 调用 build_current_progress；Executor 使用持久化 execution state 及同一 builder；Auditor 从边界证据重建 catalog。保存完整 SQLite、model_states/checkpoint chain、state timeline 和原始 token IDs；native causal_ledger 的 input.prompt 只含最后 delta，不能当完整训练输入。按实际 transport、bootstrap、State 初始化、rollover/fork 与 stop suffix 处理重建完整上下文，再证明唯一 builder 生成的协议正文与该上下文绑定；缺失请求/响应明确排除，不补造事实。
3. 标签权威只允许 executed_fixture、planner_contract、human_double_review。前者必须真实成功且推进至少一个 missing root；第二种要求计划合同只允许一个 eligible 操作；双人复核仅用于失败恢复正例并记录数量。失败动作只作为下一帧负例上下文，没有合法替代标签则丢弃。
4. 按 project family 切分 train/dev/confirmation，同 family 不跨 split；固定 UTF-8 byte 5-gram cosine，阈值 0.95；算法和参数写入 manifest 后不得更改。
5. 训练前覆盖审计包括 failed last_action、非空 error_type、directory target、.py/.json/目录 root、mutate、execute、missing target；任一覆盖为 0 数据集无效。
6. manifest 必须记录源 run id、源 trace SHA、抽取脚本 SHA、协议模块 SHA、切分算法、相似度参数、覆盖审计、逐行重算通过数。

### 2.2 固定回归集与权限

每角色从首次合法 all-zero trace 冻结一份 `rwkv_lh_g1j_<role>_regression_v1` dev/confirmation；以后每轮只新增 train，回归集不变。未经 owner 书面确认，不启动训练、不新建 data/datasets/ 版本目录。

角色轮次按实际训练累计，任何角色不得第 4 轮；换版本或 replacement 不重置。Selector 已满 3 轮。Executor / Step Auditor 旧“各剩 1 轮”声明与 Round3 登记冲突，在 owner 对账前不允许自动消耗所谓剩余额度。Final Auditor 最多 3 轮。

### 2.3 Owner 授权的项目开发基准

2026-09-07 owner 授权新增 `data/datasets/rwkv_lh_real_project_dev_v1/`，运行器标识 `realprojectdevv1`，共 12 题：CLI、数据流水线、HTTP API、已有项目维护、Web、全栈各 2 题。来源必须记为 owner-authorized authored development benchmark，即按需求编写的开发任务，不得称作采集的真实用户 trace。此授权限定该开发基准及配套验证，不变更角色训练轮次或自动批准角色数据集版本。

公开任务描述功能、环境、接口与交付合同，只向 Agent 提供登记的初始 workspace。私有黑盒验收、作者 reference/mutant 和完整期望值不得进入 Agent workspace；最终行为验证在隔离进程内读取只读 snapshot。Web/全栈使用实际 Playwright 点击、输入、刷新、键盘与状态/服务行为，不能以 CSS 长度、关键词、源码 token 或 URL 前缀替代功能验收。其他任务通过真实 CLI、HTTP、数据、数据库、重启与失败恢复检查。

冻结前必须逐题确认参考实现通过、登记的语义错误变异被拒绝、公开合同与私有验证一致，并完成整体隔离检查。作者自验不是 Agent 基线，作者参考实现也不是合法 StateTune 样本；后续角色数据仍必须来自生产 Harness 实际运行 trace，并满足 §2.1 的来源和逐字节重建要求。

新套件保留 12 题完整分母，代码/题集/评分/参数/比较门槛在模型运行前冻结；不能读过结果后改题、删失败题或改验收再重评分。既有 Ladder-10 和 E2E-90 的身份及评分保持原样。可见审计显示 E2E-90 只有 2 个带脚手架的迷你项目，另有 13 修复、34 工作流、41 孤立任务，不能等同 90 个从零真实项目；Ladder 的 Web 公开验证器原先没有浏览器，项目级行为证据需要独立建立。

## 3. 迭代顺序与比较纪律

1. 唯一协议、旧链清理、新开发题整体隔离验收及完整单元回归；使用 `uv sync --frozen --extra selector-runtime --extra benchmark-web --group dev` 和 `.venv/bin/python -m playwright install chromium` 准备环境；Torch / State 注入及必需浏览器验证不得跳过。
2. 按 owner 2026-09-07 最后授权“换回 g1j-13.3，然后开始测，之后强模型恢复了再说”，在已知 Planner / Stage Checker 输出缺陷下观察本地原生 13.3B 基线，不再等待上游恢复或先修模型输出。R3 因共享工作树中的并行源码改动被启动身份检查拦截，0 调用、0 题；后续隔离工作树中的 R4 也因首题收尾时运行器的通用题集导入依赖失败而停止并标 INVALID，A 仅有 2 条 `runner_error`、指标未知，B 未开始。当前在隔离目录修复通用依赖并准备 R5，重新冻结后两臂从头运行。核验 §1.3 上传文件身份，保留 R1 无效尝试、R2 A、R3 启动前中止与 R4 运行器失败的原始记录，以重新冻结的代码/服务/题集/参数和全新 workspace/State 完整运行 `realprojectdevv1` 同 12 题的两遍 all-zero，不先跑 Ladder、不跑 E2E-90，也不接续旧 R2 B。合同失败、length、上下文不足和未执行题均按原口径记录，不改模型输出或评分放行。质量门仍为 mutation > 0、operation-target invalid = 0、每题状态库 ≤100,000,000 bytes、无 controller_slice_exhausted，其他硬门按 R5 运行前执行预注册执行；运行授权不意味着这些门已通过。两遍有效 Strict 差为该集合噪声带；不达标修根因，禁止进入训练。
3. 使用已实现的生产 trace 抽取器审计合法来源；覆盖、切分及证据门通过后，在 owner 确认后冻结回归集。候选审计通过不代表模型能力、完整服务端输入 token/BOS 记录或训练授权。
4. 当前 State 同代码做 2⁴ 消融，或至少 all-zero/全开/四个单开；增益必须超过噪声带。
5. 只有有可归因残差、尚有合法轮次且 owner 书面确认时才训练。
6. 本轮先完成 §3 第 2 项授权的项目开发集双零；后续候选比较、Ladder-10 和 E2E-90 机制回归在各自冻结范围开展，保留其既有门槛，再扩大边界/异常/恢复/安全覆盖。每个集合独立报告分母、噪声带与逐题翻转；新项目分数不替代既有 E2E-90 结果。
7. 最终一次 Holdout；结果只报告，不用于返工。

对照两臂之间不得修改 rwkv_lh/；修改后两臂都重跑，旧比较标 INVALID。题集、参数、阈值、相似度算法预先冻结，运行后不得调整。读取 confirmation 后不修改评分/parser/stop boundary 并 rescore；发现缺陷记录后进入下一轮。单次 Strict 约 ±3 的波动不能直接作为改善，必须对照实际双零噪声带。

## 4. 验收门

角色门仅是 Agent 实验门票：同输入同参数，核心指标双跑最差值严格高于 zero 双跑最好值；结构、schema、operation preservation、路径安全、false-continue 不退化。跨分布回归只用符合当前输入合同的冻结集合；退役数据不能为此恢复重放，旧分布需从合法生产事实重新建立并登记等价覆盖。

Agent 门：Ladder-10 Strict 严格高于 all-zero 且超过噪声带，zero 已过题不回归，协议拒绝/安全失败不增加；本地编码题均有 mutation 与 check/run 证据；合法到达 final 或 blocked，不能靠预算耗尽。E2E-90 Strict 不低于 zero、FN ≤ 1、90/90 完成。并列取更少 State，每个保留 State 必须有去掉即掉分的消融证据。

上述 E2E-90 门槛不因新增项目集而降低；LH09 当前生产适配冲突属于待解决事项，不能把它包装为已完成全面基线。`realprojectdevv1` 的具体比较指标与阈值另在模型运行前预注册，必须包含全部 12 题、Agent 完成/变更/终止原因及真实行为验收，并与自身同代码双零比较。

最终完成条件见 AGENTS §7 的全部八条，另需协议目录/构造一致性检查通过、数据逐行重算 100%、从基线到最终组合每步都有两臂同代码 trace。

## 5. 分析、报告与提交

每轮按 Planner → Controller eligibility → Selector → Executor → Harness → evidence → Auditor → 下一步/终止定位首错；只有冻结合同、真实事实或安全边界可证明的偏离才能归因，不唯一记 unattributed_failure。记录首错后的放大链、逐题翻转矩阵、候选是否实际介入，以及动作/mutation/check-run/invalid/终止原因/状态库大小/分角色调用数。

对可归因首错用同输入只换一个角色 State 做反事实；能解除首错才有资格进入合法下一轮训练。不得靠外置 Head、额外调用或用例特判掩盖 RWKV 能力。

汇报先 Agent 级 Strict / completed / mutation / 终止原因，再角色数字。清理轮未跑 Agent 时明确无新指标。每轮过程、红绿回归和源码 SHA 保存于 data/experiments，完成后本地 git commit，提交信息含轮次 id；owner 负责 push。

## 6. 当前执行状态

Agent 级：R3 为 `INVALID_PRE_GENERATION_STARTUP`，0 题、0 模型生成调用，Strict / completed / mutation 未测量；不是 Strict 0/12 的能力结果。启动身份检查发现三处已有文件变化和一个新增源码文件，A 在进入 `benchmark.main` 前退出，顺序执行器停止，B 未启动，旧 freeze 和日志保持原样，详见 [R3 中止报告](../data/experiments/ZERO_STATE_AGENT_BASELINE_R3_20260907/REPORT.zh-CN.md)。R4 在隔离工作树 `/home/chase/GitHub/RWKV-LH-zero-baseline-r4`、分支 `chase/zero-baseline-r4`、固定提交 `eb861256c8edf2e3f0361027a68ed0fc35cddcf5` 重新冻结并启动 A 臂；启动时间为 2026-09-07 06:55:08 UTC，首题 `RP-API-01`；但随后收尾时运行器导入全部登记题集，因缺少封存题集模块失败，R4 已停止并标 INVALID。A 仅有 2 条 `runner_error`，Strict / completed / mutation 未知，不能使用占位 0，B 未开始。R4 freeze SHA-256 为 `c2317b13cbc8483a42f1cb1a9b40ef2134cb290f2b93b9c28ff70b0e70d3307b`，记录位于该工作树的 `data/experiments/ZERO_STATE_AGENT_BASELINE_R4_20260907/`。当前在隔离目录修复通用运行器依赖并准备 R5，重新冻结后两臂从头运行；没有完整双零成绩。下述 R2 数字和原生适配诊断仍是历史原始记录，不重评分，强模型恢复后再议。

当前 Planner 与 Stage Checker 已按 §1.5 配置为本地同一 13.3B alias，本地与远端各三种生产 loader 核验均通过。真实生产 Planner 单次探针返回 HTTP 200，自然 `stop`，1,918 输入 + 4,651 输出 = 6,569 tokens，耗时 62.601 秒；恢复实际 prefill 后 JSON 语法通过，生产 GoalPlanPatch 首先因额外顶层 `goal_digest` 拒绝。完整原文的独立审计另发现 7/7 `success_evidence` 为字符串、S1 义务绑定为空、其余非 observe 步骤仍有 read roots，不能将这些写成生产 parser 已逐项报错。该诊断轮未启动全面基线，接入缺陷仍未解决；后续 owner 已授权在已知缺陷下观察运行，传输成功不代表模型合同或能力通过。适配轮完整回归已通过 764 项，无跳过，耗时 62.43 秒；其代码验证结论不代表模型能力通过。报告与原始证据位于 `data/experiments/VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/`。

Stage Checker 的 19 步 Controller 连接 fixture 有 19 次真实 Harness 读取和明确的 mock accepted audits；完整阶段引用保留，recent facts 独立限于 8 条。该输入预检为 15,067 tokens，加原定 2,400 输出预算得到 17,467，超过服务 16,384 窗口，因而没有发起生成，没有删步骤、截事实或降低预算。此为连接 fixture 的物理上下文限制，不是 Stage Checker 模型成绩；后续较小既有 fixture 的连接结果单独登记。

独立的既有 1 步 / 1 条事实 fixture（真实 Harness 写入、明确 mock 审计）在原定 Stage Checker 2,400-token 预算下返回 HTTP 200，但重复思考后 `finish_reason=length`，因此没有有效 JSON 判定。输入 1,005、输出 2,400 tokens，耗时 32.352 秒；原文及拒绝证据见本轮 `SMALL_STAGE_CHECKER_NATIVE_CONNECTION_PROBE.json`。此为连接失败样本，不属于能力评测或训练来源。

§1.4 的计划数量整改仍生效，其他字段、依赖、阶段和证据约束不因数量放开而取消。此前诊断与整改分别位于 `data/experiments/LOCAL_13B_SUPERVISOR_CONNECTION_R1_20260907/` 和 `data/experiments/PLANNER_UNBOUNDED_PLAN_R1_20260907/`，其冻结报告保持原样。

上一轮已统一五角色 builder 并删除旧协议与数据链。owner 确认服务器 `rwkv-8222` 后执行旧资源清理与当前源码部署，并授权编写 12 题项目开发基准。服务器禁止使用 Git，部署和身份核验只使用本地上传的完整 engine 源码清单与 manifest SHA；每次新运行均绑定相应核验记录。R2 的中转 `gpt-5.6-sol` 配置只属于历史冻结状态，不代表当前本地原生配置。

首次 `real_project_zero_a` 已按上述约束中止并记录于 `data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/INVALID_ATTEMPT_01.json`，不用于成绩、噪声或训练来源。后续上传身份核验与 R2 冻结已完成；R2 A 完整运行 12 题，Strict 0/12、completed 0/12、mutation 0，全部终止于 `strong_planner_unavailable`，operation-target invalid 2，11 题没有 RWKV 生成。B 臂暂未启动，上游诊断独立于 Agent 评分，尚无合格的双零能力基线。当前按后续 owner 授权准备 R5 观察运行；已知 Planner 输出合同和硬门问题未因此解决，不能进入训练。没有启动角色训练或读取 Holdout。服务器清理记录见 `data/experiments/SERVER_RUNTIME_CLEANUP_R1_20260907/`，本轮结果见 `data/experiments/ZERO_STATE_AGENT_BASELINE_R1_20260907/R2_A_RUN_REPORT.zh-CN.md`；新增开发任务与作者自验不能被称为真实用户 trace 或 Agent 能力提升。
