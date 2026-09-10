# G1J 分角色 Agent：唯一协议、数据来源与验收规范

更新日期：2026-09-10。适用于当前生产、数据抽取、训练登记和评测；owner 最新指令优先。最新完整开发采集为 REALPROJECT R1：Strict 0/12、completed 0/12、mutation 0、动作 0；10 题强模型网关 HTTP 500，2 题 Native 生成 State 边界错误。交接 R1 后的真实测试尚未完成闭环；R2 数值整改两道原始失败输入的 GPU 及重启验证已通过；最新 StateTune 入口整合完整回归 1390 passed、0 skipped，固定 Selector 回归与优化器入口已接通，2.9B 新部署后端数值复验通过。工程验证不替代 Agent 验收，optimizer steps 仍为 0。各轮原始结果、当前状态及 SHA 见 [当前交接](HANDOFF.zh-CN.md)。

已修复 REPAIR 的无条件改计划分支、根证据固定八条截断及数据标签等工程问题。当前工作流程是先 Selector，满足当前角色的来源、标签、预注册覆盖与验证条件后训练，再固定前序 State 推进下一角色。Agent 能力低分不再作为训练前禁令。owner 已取消固定三轮上限；历史训练事实用于追溯，后续按指标、预算和实际 run 管理。

## 1. 唯一协议

每个角色只保留一个协议模块，拥有唯一 `build_prompt_source()` 和 renderer。嵌套的机械进度、目标合同和 gap catalog 也必须调用同模块共享函数。生产、数据抽取和验收不得自行拼接协议字典或保留兼容输入链。

| 角色 | 唯一模块 | schema 后缀 | 构造与渲染 |
|---|---|---|---|
| Selector 2.9B | `selector_intent_v6.py` | selector-intent.v6 | `build_current_progress()` → `build_prompt_source()` → `render_prompt()` |
| Executor 13.3B | `executor_args_v6.py` | executor-args.v6 | `build_target_contract()` / `build_execution_state()` → `build_prompt_source()` → `render_generation_prompt()` |
| Step Auditor 13.3B | `auditor_step_v6.py` | auditor-step.v6 | `build_prompt_source()`（内建 gap catalog）→ `render_prompt()` |
| Finalizer 13.3B | `finalizer_answer.py` | finalizer-answer.v2 | `build_prompt_source()` → `render_prompt()` |
| Final Auditor 13.3B | `auditor_final.py` | auditor-final.v4 | `build_prompt_source()`（内建 gap catalog）→ `render_prompt()` |

模块均位于 `rwkv_lh/goal_state_protocols/`。schema 完整前缀为 `rwkv-lh.g1j-per-stage-state-tuning.`，运行时引用模块的 `INPUT_SCHEMA_VERSION`，不得在调用方拼出身份标签。Executor `render_prompt()` 是相同输入的前缀正文，`render_generation_prompt()` 仅追加同一调用边界，不是另一套输入协议。

两个 Auditor 的 catalog 明确为 `possible_unmet_conditions`，目录项本身不构成未满足的事实。Step 协议从同一份可见证据排除与完整观察/实际变更矛盾的 root gap，并在生产与标签校验中拒绝同类断言；失败、截断、未知完整性与不完整投影不能证明完整观察。业务成功条件仍由 RWKV 判断，不根据工具成功自动完成步骤。最终回答/执行缺口继续按既定 repair_scope 交给负责角色。

角色协议目录不保留旧模块或 identity stub。旧版、未知 schema 和旧独立 Executor 披露/重试格式一律拒绝；历史只能查 Git / GitHub。升级前删除旧模块及其可执行字节码，不允许 vN/vN+1 并存。

### 1.1 Selector 输入

current_progress 精确字段与顺序：

```text
assigned_action_count, successful_action_count, failed_action_count,
last_action, missing_read_roots, missing_write_roots,
workspace_targets, completion_preconditions_satisfied, feedback, target_discovery_complete
```

last_action 精确字段与顺序：

```text
operation, status, arguments, error_type, error_message,
result_metadata, observed_roots, mutated_roots
```

- arguments 最多 8 个键，每值最多 160 字符；结构化值仅保留 object/array 大小描述。
- 失败时 error_type/error_message 必填，message 最多 240 字符；成功时为 null。失败不覆盖 observed/mutated root。
- metadata 白名单按顺序为 outcome_type、exit_code、target_kind、entry_count、match_count、byte_count、size_bytes、truncated、changed_path_count。
- workspace_targets 最多 32 条；目录发现或提示投影不完整时 target_discovery_complete=false，此列表不是允许列表；类型取 `operation_contracts.WORKSPACE_TARGET_KINDS`。
- 网络封装 NetworkSelectorInput 使用 v5，只接受角色 v6。endpoint、menu/role/prompt/target prefix 全部引用角色模块常量。decoder manifest 与运行 attestation 必须匹配当前源码。

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

取消计划数量上限不等于模型上下文无限。当前 RWKV 服务窗口为 16,384 tokens；独立强模型的上下文由其服务决定，不能套用 RWKV 的窗口值或仅凭模型 alias 推断。新运行须核验实际限制和请求预算；超出窗口不能静默截断计划、删证据、临时降低预算或伪装为模型完成。任务结束仍由 RWKV 结合目标覆盖和执行证据判断，并通过既有完成校验；资源不足只能明确报告中断或阻塞。

### 1.5 独立强模型 Supervisor 与唯一配置入口

owner 于 2026-09-09 要求 Planner 使用强模型。本地已有的强模型配置现已合入唯一 `.env.local`，Planner / Stage Checker 与 RWKV runtime 的默认读取路径一致，显式进程变量优先。清除旧 `.env` 中的 Supervisor 路由与冗余 `.env.strong.local`，不得依赖组件初始化次序决定模型。历史 13.3B Planner 观察保持原始身份，不改写成强模型结果。

| 配置 | 当前值 |
|---|---|
| `RWKV_LH_PLANNER_BACKEND_PROFILE` | `openai-compatible` |
| `RWKV_LH_PLANNER_STREAM` | `true`，官方服务使用 SSE；通用程序默认 false，原生 RWKV 传输不受此开关影响 |
| Planner / Stage Checker 模型 alias | `deepseek-v4-pro` |
| base URL | owner 于 2026-09-10 选择的官方 `https://api.deepseek.com`；不在代码中固定服务地址 |
| `RWKV_LH_PLANNER_MAX_PLAN_TOKENS` | `32768` |
| `RWKV_LH_PLANNER_READ_TIMEOUT` | `600` 秒，两个 Supervisor 角色共用 |
| `RWKV_LH_PLANNER_MAX_CONTRACT_REVIEW_TOKENS` | Stage Checker `16384` |
| `RWKV_LH_PLANNER_PLAN_CACHE_ENABLED` | `false` |
| `RWKV_LH_PLANNER_FALLBACK_MODELS` | 空 |
| 本地语义纠错 / 传输尝试 | 默认 1 次语义纠错；最多 2 次传输尝试，协议错误不消耗传输重试 |

2026-09-10 已按 owner 指令切换 DeepSeek 官方服务。真实公开任务计划一次调用成功，4 阶段 6 步，生成 12314 tokens（思考 10919），耗时 200.37 秒。后续读取预算按新 token 上限登记为 600 秒；不得将旧网关错误或探针成功改写成整题 Agent 成绩。详情见 [官方接入证据](../data/experiments/DEEPSEEK_OFFICIAL_PLANNER_R1_20260910/REPORT.zh-CN.md)。

当前通过 `/chat/completions` 发送生产 `GoalPlanRequest` / `GoalStageReviewRequest`，使用 `response_format=json_object` 并显式发送输出 token 上限。此前第三方网关对完整非流式 Planner 请求返回过 HTTP 500，相同输入的 SSE 诊断成功；这支持配置流式传输，但不能据此断言网关内部故障原因。流式实现保留同一请求串行锁直到读完，拼接标准 SSE 文本增量后才做 JSON/合同校验；缺少 DONE/finish、切换 model、多个 choice、结束后追加内容均拒绝，读取预算按中断处理。通用聊天与原生 RWKV 传输都要求自然 `stop`，`length` 即使伴随完整 JSON 也拒绝；未知停止原因不伪装成完成。Planner 只生成计划，Stage Checker 只审查已完成阶段；五个 RWKV 角色继续使用各自模型与 State。

完整 JSON 未满足当前合同或初始/续写边界时，保留原始对象，使用 `GoalPlanResponseError` 进入 Controller 已有的语义纠错；错误说明指出缺失/多余字段，原始计划放在同一请求尾部。被拒绝的对象没有修改计划的权威，不准重写 root、发明字段、接纳旧版本或拼补截断 JSON。网络失败仍保留 pending 与原传输错误。RWKV 原生传输适配作为同一协议的 backend 配置继续可用；其历史验证见 [原生适配报告](../data/experiments/VLLM_RWKV_SUPERVISOR_ADAPTER_R1_20260907/REPORT.zh-CN.md)。

连接探针与 Planner 单边界检查均不计 Agent 分数、双零噪声或 StateTune 来源；模型名由服务返回，自托管权重级 attestation 不适用于这个外部接口。配置迁移与验证证据见 [Planner 修复报告](../data/experiments/PLANNER_STRONG_ROUTING_R1_20260909/REPORT.zh-CN.md)。

### 1.6 单一架构与模型升级

产品统一由 `product_runtime.build_product_controller()` 创建当前 `StatefulGoalLoopController`；生产 CLI 与 Web 不提供旧 Controller / learned State router 分支。公共基类和部署适配器不是第二套产品入口，不按文件名盲删。

五个角色协议的职责保持稳定：Selector 选操作，Executor 填参数，Harness 执行，Step Auditor 判断步骤是否满足，Finalizer 作答，Final Auditor 判断最终证据与回答。Planner / Stage Checker 负责计划和阶段边界。步骤 REPAIR 应将差距交回同一步；工具失败、参数错误或 Auditor 输出无效不能直接作为重规划依据。后续计划调用应有阶段审查或现有工作结束后仍存在目标缺口的依据；重复成功动作仍受无进展预算约束。

2026-09-09 当前实现统一使用 `role-feedback.v1`：步骤语义缺口同时进入 Selector / Executor；最终回答缺口进入 Finalizer；执行证据缺口带原审计身份进入 Planner 并重新打开可执行工作。协议错误只重试原角色、原审计边界，不重放动作或候选；Finalizer 分别保留 semantic feedback 与 protocol retry_feedback。反馈包含来源、接收角色、边界/计划/步骤版本、原条件、证据及被拒绝输出，运行与 trace 重建共享因果日志投影。完成仍须 Final Auditor 接受，预算耗尽只会阻塞/中断。

Stage Checker 接收该阶段所有引用对应的 Harness 动作，action/artifact/revision 使用同一来源解析。内容投影可显式标记，证据条数不再裁成 8/12；审计工具声明也不再限定证据或 gap 数量。目录发现保留全部显式 root，有限发现标明不完整；工具资格依据文件/目录/缺失目标的结构性条件，不按后缀或采样内容推断能力。唯一 GoalPlanPatch v4 及显式 phase 为当前入口，旧版本、未知版本和旧 contract graph 重放拒绝。完整设计及验证边界见 [角色链路契约](CONTROLLER_ROLE_LINK_CONTRACT.zh-CN.md)和本轮报告；工程回归不等于模型能力验收。

RWKV 更新应优先改变部署配置与必要的底层适配：模型/词表 SHA、State 形状与 dtype、上下文和输出预算、生成前缀/停止符、服务能力。角色输入仍调用同一 builder；只有真实语义合同变化才升级并替换协议。每次升级验证 State 注入、token 对齐、自然 stop、五角色输入和真实流程，重新冻结源码与服务身份。旧 State 的形状兼容不等于行为或训练分布兼容，不能自动沿用旧结果。

## 2. 数据来源与清理规则

旧合成角色数据链已删除，不保留本地归档或 stub，也不得恢复旧生成器以继续训练。旧实验只查 Git / GitHub；当前工作树只保存当前有效数据、隔离验收材料和本轮及后续证据。

### 2.1 唯一生产 trace 流水线

唯一入口为 `rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py`，操作见 [使用说明](ROLE_TRACE_DATASET.zh-CN.md)。它输出候选审计与待复核队列，不启动训练或创建正式角色数据集。

1. 来源是冻结开发范围内生产 Harness 的实际 trace，允许 `all_zero`，也允许 `RUN_PROTOCOL.role_data_collection` 预先固定前序 State 的 `role_stage`。阶段模式只抽取指定目标角色，目标及后序角色 zero；所有角色模型与 State 的 SHA 必须与冻结配置一致。开发基准仍是 authored development benchmark，不能称作真实用户请求；reference/mutant、测试 mock 和 Holdout 不能作训练来源。
2. 从每个 assignment / audit boundary 当时的 durable snapshot 调用唯一 builder，逐字节核对 checkpoint。保存完整 SQLite、checkpoint chain、state timeline、原始请求/响应、提交/回滚及生成 token。native 最后一次 delta 不是完整输入，须按 bootstrap、append、fork、rollover 与实际 stop 重建；缺证据排除，事实冲突整批拒绝。
3. Selector 可由唯一 eligible 合同、真实成功且推进 missing root 的执行事实或双人复核标注。Executor 必须保留真实执行绑定，失败本身不能靠人工签名变成执行正例。Step Auditor、Finalizer、Final Auditor 的语义标签必须独立双人复核；kernel 接受和最终 completed 不自动证明模型判断正确。未达后续阶段的合法边界仍可进入待复核队列。
4. 人工纠正必须绑定原始 run/request/boundary、精确输入与原始输出 SHA、当时可见证据和理由，两名 reviewer 同意同一个目标。原始输出与原 token 永久保留，纠正目标及其本地编码单独标明；不能发明新场景、伪造模型原文或给未执行的 Executor 命令授予执行事实。
5. 按 project family 固定 80/10/10 切分，UTF-8 byte 5-gram cosine 阈值 0.95。只检查本阶段请求的角色，每角色 train/dev/confirmation 非空。九类覆盖均报告；若有运行前冻结并由源协议固定 SHA 的角色覆盖 scope，则按该 scope 验收；否则沿用九类全覆盖。不能看过结果后降低覆盖要求。
6. manifest 记录源 run、源工件 SHA、生产协议/抽取器/helper SHA、切分与相似度、逐行重算、覆盖、标签权威、原始与纠正目标及 token 完整性。只有服务器实际返回且与重建匹配的 full input IDs 和显式 BOS 信息能将 `token_ids_complete` 置真；缺失、delta-only 及未知 scope 保持未证明。

### 2.2 固定回归集、预算与训练记录

每角色从首次合格的本阶段来源冻结一份 dev/confirmation，后续只增加 train。回归身份绑定角色、协议、采集时的上游 State、覆盖 scope 和样本 fingerprint；复用不得更换其中任何条件。模型或协议改变时重新审查兼容性，不能把退役分布当当前回归，不能借升级每轮另挑验证题。

owner 已授权按角色逐阶段推进，并于 2026-09-09 明确“取消固定三轮上限，改按预注册指标、预算和实际训练记录管理”。后续没有 Selector 用尽额度、Executor 剩一轮或第四轮禁令；历史不明确的训练次数如实标 unknown，不作为额度阻塞。新的具体训练须有明确授权范围及预注册预算，已有范围内不重复索取授权。

每个 run 在开始前登记：角色/阶段、模型与 tokenizer、协议、源数据 manifest 与固定回归身份、训练器及适配器 SHA、初始 State、随机种子、优化器与参数、最大 steps/时间/资源预算、角色指标与阈值、Agent 观察指标、停止和候选保留规则。结束记录实际 optimizer steps、资源消耗、日志 SHA、输出 State SHA 与验证结果。失败/中断记录真实已执行工作；采集、代码修复和纯评测不伪报成训练。预算耗尽后按原规则停止，不临时加预算或改评分。

训练与正式 `data/datasets/` 版本遵循 owner 的现有书面授权范围。候选审计 valid 不自动构成新的数据冻结或无预算训练授权。

### 2.3 Owner 授权的项目开发基准

2026-09-07 owner 授权新增 `data/datasets/rwkv_lh_real_project_dev_v1/`，运行器标识 `realprojectdevv1`，共 12 题：CLI、数据流水线、HTTP API、已有项目维护、Web、全栈各 2 题。来源必须记为 owner-authorized authored development benchmark，即按需求编写的开发任务，不得称作采集的真实用户 trace。此授权限定该开发基准及配套验证，不自动批准角色训练预算或角色数据集版本。

公开任务描述功能、环境、接口与交付合同，只向 Agent 提供登记的初始 workspace。私有黑盒验收、作者 reference/mutant 和完整期望值不得进入 Agent workspace；最终行为验证在隔离进程内读取只读 snapshot。Web/全栈使用实际 Playwright 点击、输入、刷新、键盘与状态/服务行为，不能以 CSS 长度、关键词、源码 token 或 URL 前缀替代功能验收。其他任务通过真实 CLI、HTTP、数据、数据库、重启与失败恢复检查。

冻结前必须逐题确认参考实现通过、登记的语义错误变异被拒绝、公开合同与私有验证一致，并完成整体隔离检查。作者自验不是 Agent 基线，作者参考实现也不是合法 StateTune 样本；后续角色数据仍必须来自生产 Harness 实际运行 trace，并满足 §2.1 的来源和逐字节重建要求。

新套件保留 12 题完整分母，代码/题集/评分/参数/比较门槛在模型运行前冻结；不能读过结果后改题、删失败题或改验收再重评分。既有 Ladder-10 和 E2E-90 的身份及评分保持原样。可见审计显示 E2E-90 只有 2 个带脚手架的迷你项目，另有 13 修复、34 工作流、41 孤立任务，不能等同 90 个从零真实项目；Ladder 的 Web 公开验证器原先没有浏览器，项目级行为证据需要独立建立。

## 3. 迭代顺序与比较纪律

1. 完成影响执行、协议、隔离和 trace 可信性的工程回归，冻结生产源码/模型/State/engine/decoder/题集/参数。完整测试使用 AGENTS 中的环境和命令，不跳过 Torch / State 注入或必要浏览器。训练不能修复宿主机误执行、丢失 token 或错误身份这类工程问题。
2. 在授权开发范围采集当前代码的 zero 观察，按原口径记录全部题的 Strict、completed、mutation、终止原因、角色调用和首错。0 分、无 mutation、后序角色未到达均可成为训练诊断；不要求 Agent 先达最终能力门。来源身份、因果和标签质量必须满足 §2.1。
3. 首阶段只审计 Selector。按预注册 scope 收集合格操作标签并冻结该角色回归；达到登记的数量、覆盖和证据条件，在已授权预算内训练、验证。原始错误选择可作为精确边界的复核材料，不要求任务已完成。
4. Selector 达到本阶段预注册角色指标和不回归要求后，固定其 State；在同一产品架构运行 Executor zero，继续真实填写参数并执行，收集实际错误及后续正确动作，再训练 Executor。随后同法推进 Step Auditor → Finalizer → Final Auditor。某角色已达标可保持 zero；不要求五角色一起训练，也不为制造数据跳过真实生产决策。
5. 每阶段先做“固定其他 State、只换目标角色 State”的比较。进入下一采集阶段的合格 State 是实验条件冻结；整个组合是否正式保留仍按 §4 的 Agent 门和消融决定。不能因为后序角色还弱，就无限阻止前序角色采集/训练；也不能把前序角色分数提高写成 Agent 已完成。
6. 当前组合与 all-zero 在同代码固定集合上比较并独立报告噪声、逐题翻转及首错；消融按实际启用的 State 数量逐个撤去，必要时扩展组合，不硬编码四个 State。Ladder-10、E2E-90 与 12 题项目集按各自冻结合同开展；LH09 生产适配冲突另行修复，不能删题或改分母。
7. 最终 Holdout 只运行一次，结果只报告、不用于返工。

两臂之间不得修改 `rwkv_lh/`；修改后两臂重跑，跨代码的旧比较标 INVALID。冻结的历史实验原文和成绩不重评分。本次 R7 在其原冻结代码内的 A/B 证据仍有效，不能沿用为修复后成绩。题集、参数、阈值、相似度、预算和覆盖 scope 均在相应运行前冻结。读取 confirmation 后不修改评分/parser/stop boundary 再 rescore。单次 Strict 约 ±3 的波动不能直接算改善，每个集合使用自己的有效双零噪声带。

## 4. 验收门

以下是训练后候选与正式组合的保留门，不是首次采集或训练前提。角色门：同输入同参数，核心指标双跑最差值严格高于 zero 双跑最好值；结构、schema、operation preservation、路径安全、false-continue 不退化。跨分布回归只用符合当前输入合同的冻结集合；退役数据不能为此恢复重放，旧分布需从合法生产事实重新建立并登记等价覆盖。

Agent 门：Ladder-10 Strict 严格高于 all-zero 且超过噪声带，zero 已过题不回归，协议拒绝/安全失败不增加；本地编码题均有 mutation 与 check/run 证据；合法到达 final 或 blocked，不能靠预算耗尽。E2E-90 Strict 不低于 zero、FN ≤ 1、90/90 完成。并列取更少 State，每个保留 State 必须有去掉即掉分的消融证据。

上述 E2E-90 门槛不因新增项目集而降低；LH09 当前生产适配冲突属于待解决事项，不能把它包装为已完成全面基线。`realprojectdevv1` 的具体比较指标与阈值另在模型运行前预注册，必须包含全部 12 题、Agent 完成/变更/终止原因及真实行为验收，并与自身同代码双零比较。

最终完成条件见 AGENTS §7 的全部八条，另需协议目录/构造一致性检查通过、数据逐行重算 100%、从基线到最终组合每步都有两臂同代码 trace。

## 5. 分析、报告与提交

每轮按 Planner → Controller eligibility → Selector → Executor → Harness → evidence → Auditor → 下一步/终止定位首错；只有冻结合同、真实事实或安全边界可证明的偏离才能归因，不唯一记 unattributed_failure。记录首错后的放大链、逐题翻转矩阵、候选是否实际介入，以及动作/mutation/check-run/invalid/终止原因/状态库大小/分角色调用数。

对可归因首错，在训练得到候选后用同输入只换一个角色 State 做反事实，检验它是否解除首错；没有现成合格 State 不阻止针对首错采集和训练。不得靠外置 Head、额外调用或用例特判掩盖 RWKV 能力。

汇报先 Agent 级 Strict / completed / mutation / 终止原因，再角色数字。清理轮未跑 Agent 时明确无新指标。每轮过程、红绿回归和源码 SHA 保存于 data/experiments，完成后本地 git commit，提交信息含轮次 id；owner 负责 push。

## 6. 当前执行状态

当前状态统一维护于 [HANDOFF](HANDOFF.zh-CN.md)，训练管线能力与缺口见 [StateTune 状态](STATETUNE_DATA_PIPELINE_STATUS.zh-CN.md)。当前文档不再复制 R2–R6 的“正在运行”“不得训练”等过期指令；历史 run、失败与原始评分仅按其冻结报告追溯。

闭环轮没有新增模型成绩。后续 `RWKV29_DEPLOY_COMPAT_R1_20260909` 已部署当前 2.9B Selector，并通过 Native 数值兼容验证；尚未取得修复后的真实 Agent 指标、冻结正式角色数据或启动优化器训练。代码回归、真实模型数值验证、角色训练与 Agent 成绩分别报告，不把 fixture 通过写成模型能力提升。
