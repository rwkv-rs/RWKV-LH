# 生产 trace → StateTune 角色候选数据管线

更新日期：2026-09-09。当前整改轮次：`STATETUNE_ENTRY_REPAIR_R1_20260909`；沿用唯一生产 trace 抽取入口。

当前已实现五角色生产 trace 抽取、协议与上下文重建、标签校验、切分、覆盖及相似度审计。入口为 [`role_trace_dataset_v1.py`](../rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py)。它消费已经冻结的运行工件，输出候选审计文件；不会调用模型、启动训练、创建 `data/datasets/` 版本目录或自动批准回归集冻结。

本实现轮没有新增 Agent 级 Strict、completed、mutation 数或终止原因测量，也没有新增角色训练成绩。测试使用明确标识的 mock 模型和真实 Harness I/O，只验证代码及工件链路，不能作为合法生产训练来源。代码实现、候选审计通过、正式数据冻结、模型能力提升是四种不同结论。

## 1. 输入与实现边界

| 模块 | 职责 |
|---|---|
| [`role_trace_dataset_v1.py`](../rwkv_lh/goal_state_protocols/role_trace_dataset_v1.py) | 来源登记、只读 SQLite 校验、遍历因果边界、请求与标签绑定、CLI |
| [`role_trace_inputs.py`](../rwkv_lh/role_trace_inputs.py) | 从请求当时的精确 durable snapshot 重建五角色输入，核对生产 checkpoint 文本 |
| [`role_trace_context.py`](../rwkv_lh/role_trace_context.py) | 按实际 transport、初始 State、bootstrap、append、generation、fork 和 rollover 重建消费上下文 |
| [`role_trace_generation.py`](../rwkv_lh/role_trace_generation.py) | 将本次原始 request/response、sampling、预算及 commit/rollback 绑定到准确 checkpoint；逐 token 核对 Selector decoder |
| [`role_trace_labels.py`](../rwkv_lh/role_trace_labels.py) | 用当前角色协议、可见事实与 Executor provenance 校验目标，不改写运行时输出 |
| [`role_trace_artifacts.py`](../rwkv_lh/role_trace_artifacts.py) | 固定 family 切分、覆盖、相似度、不可变回归候选及原子写出 |
| [`role_trace_stages.py`](../rwkv_lh/role_trace_stages.py) | 校验运行前冻结的目标角色、前序 State 和各角色模型身份；不是另一个 Controller 或训练调度器 |

抽取模块不是第六个角色协议。角色输入仍只有以下五个共享构造入口：

| 角色名（`--role`） | 协议模块 | 输入重建 |
|---|---|---|
| `selector_intent` | [`selector_intent_v5.py`](../rwkv_lh/goal_state_protocols/selector_intent_v5.py) | `build_current_progress()` → `build_prompt_source()`；逐一校验 `canonical`、`rotate_8`、`rotate_17` 三个菜单及原始投票 |
| `executor_args` | [`executor_args_v5.py`](../rwkv_lh/goal_state_protocols/executor_args_v5.py) | 重建 target contract 和 execution state，再用 `build_prompt_source()` / `render_generation_prompt()` |
| `auditor_step` | [`auditor_step_v5.py`](../rwkv_lh/goal_state_protocols/auditor_step_v5.py) | 从审计边界的 active step 与可见证据调用 `build_prompt_source()`，由协议构造 gap catalog |
| `finalizer_answer` | [`finalizer_answer.py`](../rwkv_lh/goal_state_protocols/finalizer_answer.py) | 从已完成计划和提交事实调用 `build_prompt_source()` |
| `auditor_final` | [`auditor_final.py`](../rwkv_lh/goal_state_protocols/auditor_final.py) | 从 final boundary、Finalizer 原始候选及证据调用 `build_prompt_source()` |

Controller 在调用 Selector/Executor 前新增 `goal_role_input_boundary`，保存该时刻的 step/revision、Harness target contract、eligible operations、机械证据摘要及共享 builder 产生的 execution state。抽取器重新计算进度及执行事实；不能把 trace 内的现成 prompt 当作事实，也不能读取今天的 workspace 来推断历史文件类型。

输入重建要求 SQLite 中保留请求边界当时的精确 snapshot。把最终状态的 `causal_order` 截短、同时保留未来 action 或投影不构成合法历史快照。缺失的快照不能靠猜测恢复。采集时必须保留足够 checkpoint；benchmark 使用较高 retention，不能把 Store 默认的有限保留量当作全部历史已保存。

## 2. 可接受的来源

来源必须是生产 Harness 在已冻结开发范围中的实际运行。允许 `all_zero`，或运行前登记并固定前序 State 的 `role_stage`。任务失败、未完成或后序角色未到达本身不否定当前角色的可信边界。`production_trace` 描述执行链路，不能把按需求编写的开发题称为真实用户请求。已授权的 `realprojectdevv1` 仍是 authored development benchmark；其作者 reference/mutant、私有黑盒验收和 mock 模型输出均不能充当角色训练数据。

每个 case 需要以下文件，`register` 会计算 SHA-256 并先执行完整来源校验：

```text
FROZEN_RUN/
  RUN_PROTOCOL.json
  source_tree_manifest.json
  cases/CASE_ID/
    state/long_horizon.db
    model_trace.json
    event_log.json
    state_timeline.json.gz
    causal_ledger.json
```

`RUN_PROTOCOL.json` 和 `source_tree_manifest.json` 按 `--case-dir` 的上两级目录定位。来源登记保存七种必需工件的路径与 SHA；可选的 `human_reviews` 工件同样须登记独立路径和 SHA。当前 `register` CLI 不自动生成双人复核材料。

主要校验包括：

1. `source_kind=production_trace`。`all_zero` 的 checkpoint、native cache binding 和 raw generation 必须明确为 `zero` / 64 个 `0`；`role_stage` 则逐一匹配冻结的角色模型/State 身份，目标与后序角色必须 zero。模型 SHA 必须完整；模式由冻结协议决定，不能事后改登记字符串绕过。
2. `source_run_id` 对应冻结协议的 `round`，`run_id` 位于冻结 `selected_case_ids`，suite 有同名的冻结 visible-task 资源登记。改写 suite 字符串不能绕过冻结范围。
3. 完整 source manifest 的摘要与冻结协议一致；逐项核验当前 `rwkv_lh/` 下全部生产 `.py` 和 tokenizer 词表的 SHA，不只抽查五个协议文件。`role_trace_*` 抽取消费模块不作为来源运行的 producer，其 extractor/helper SHA 另记在候选 provenance 中。抽取器只读取资源登记元数据，不打开其中的题目答案或验收文件。
4. SQLite 必须是已冻结的独立文件，不存在有内容的 WAL/journal；以 `mode=ro&immutable=1` 和 `query_only` 读取并执行完整性检查。登记后、读取中发生文件变化会拒绝。
5. event log、state timeline 的每次变化与 SHA、causal ledger 必须能从 SQLite 重算；snapshot 的 revision、最后 causal event 与因果前缀必须一致。单独给篡改的导出文件重新算 SHA 不能绕过这层校验。

受保护的 Holdout、acceptance、sealed、confirmation 来源路径及相应 suite 被拒绝；符号链接的解析目标也检查。登记字段是可审计的来源声明，不会把自编 fixture 变成真实生产运行。操作者仍须保存实际采集与冻结证据。

登记只引用源工件，不会把整个 SQLite/trace 自动复制进候选目录。复现或上传时必须同时保留这些源工件及其冻结清单。服务器身份继续使用本地生成并上传的源码清单；服务器不得调用 Git。

逐角色模式的 `RUN_PROTOCOL.json` 增加 `role_data_collection`，精确字段为 `mode="role_stage"`、非空 `stage_id`、`target_role`、`profiles`。`profiles` 必须包含五个角色名，每个值精确包含 `profile_id`、`profile_sha256`、`model_sha256`。角色次序为 Selector → Executor → Step Auditor → Finalizer → Final Auditor；前序可以固定已验证 State，目标及后序必须 zero。`register` 自动登记该模式；`extract --role` 必须恰好选择冻结的目标角色。

例如采集 Executor 时固定合格 Selector，其余四角色 zero。这样 Executor 数据来自实际会部署的上游选择条件；不能与另一份 Selector State 产生的样本混为同一固定回归。此协议只核验采集条件，不自动启动模型或优化器。

## 3. CLI 使用

命令只在 WSL `UbuntuRecovered` 的项目环境中运行。以下 `FROZEN_RUN`、`CASE_ID`、`PROJECT_FAMILY` 均为占位符，须换成已经存在、已授权并冻结的开发运行身份；这些示例不启动新的 Agent 运行。

```bash
cd /home/chase/GitHub/RWKV-LH
.venv/bin/python -m rwkv_lh.goal_state_protocols.role_trace_dataset_v1 register \
  --case-dir /home/chase/GitHub/RWKV-LH/data/experiments/FROZEN_RUN/cases/CASE_ID \
  --run-id CASE_ID \
  --source-run-id FROZEN_RUN \
  --project-family PROJECT_FAMILY \
  --suite realprojectdevv1 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/ROLE_TRACE_CANDIDATE/source_registration.json
```

`register` 一次登记一个 case。多个经校验的登记可汇入同一 `source_runs` 数组；来源身份不得重复，project family 应按实际项目谱系在读取结果前确定，不能为了调整 split 重命名。

```bash
.venv/bin/python -m rwkv_lh.goal_state_protocols.role_trace_dataset_v1 extract \
  --registration /home/chase/GitHub/RWKV-LH/data/experiments/ROLE_TRACE_CANDIDATE/source_registration.json \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/ROLE_TRACE_CANDIDATE/audit_01
```

默认抽取五角色。需要限定角色时可重复提供 `--role`，例如 `--role selector_intent --role executor_args`。`register --output` 是新 JSON 文件，`extract --output` 是新目录；输出仅允许在项目 `data/experiments/` 或 `data/test_runs/` 下，禁止写入 `data/datasets/`，禁止覆盖已有目标。

实际请求的角色集合写入 provenance；`requested_roles_present` 检查候选角色恰好与请求集合一致。任何请求角色完全没有样本都会产生 `invalid`；未请求的后序角色没有样本不阻止当前角色。首阶段使用 `--role selector_intent`，不必等待 Finalizer 等角色。

| 退出码 | 含义 |
|---|---|
| `0` | 登记成功，或候选审计 `status=valid` |
| `2` | 抽取完成并写出审计，但覆盖、切分或相似度质量门不满足，`status=invalid` |
| `1` | 来源、身份、因果、协议或文件校验失败，返回 `status=rejected`；不能发布为有效数据 |

输出目录包含：

- `candidates.jsonl`：有合法标签权威的候选行、split、重建输入、原始输出/token、独立纠正目标及来源证据。
- `review_queue.jsonl`：输入与生成证据可核验但缺语义标签的边界，包含复核所需原始记录、输入、SHA 和可见证据；不进入训练候选数量。
- `manifest.json` / `manifest.sha256`：source registration、源工件、抽取与 helper/协议源码 SHA，行数、覆盖、相似度、排除原因和文件摘要。
- `regression_candidate.json`：仅在审计门通过时输出 dev/confirmation 候选及 fingerprint；不等同 owner 已批准冻结。

写出在临时目录完成后原子发布，已有目标不会被替换。审计 `valid` 只表达已实现质量门的结果，不代替预注册预算、训练授权或服务端 token 完整性检查；固定三轮额度已取消。

## 4. 上下文、token 与标签

输入有两层检查：先用唯一角色 builder 重建协议正文，结合生产 bootstrap/披露包装与该 run 的 checkpoint 全文逐字节一致；再从模型会话审计恢复实际消费的上下文。

本次生成还必须通过独立的请求/响应证据校验：同一 request 必须有唯一、先后顺序正确的 start 和 response，input checkpoint 来自准确边界 snapshot，digest、lane、transport、State、原文 SHA/UTF-8 字节数、sampling 和输出预算均一致。candidate 必须在响应后有唯一 durable commit 或 rollback；commit 核对 parent、candidate digest、命令摘要和上下文链，rollback 核对恢复的原输入 checkpoint。不能用后来保存的 input metadata 替代请求当时的证据，也不能把“有响应”当作“已提交”。这些检查只证明生成事实，不自行授予正例标签权威。

Selector 的每条原始 lane 另外核对 input/menu/eligible digest、fresh State、decoder ID/protocol/SHA、checkpoint 与 decoder trace SHA。输出 token IDs 必须等于当前协议标签后缀的 token 序列；每个位置都要有完整 eligible trie token 集、有限 logit、与记录一致的 argmax/chosen logit/runner-up margin。随后重算三个独立菜单的集成投票。缺少某条原始 lane，或把集成输出复制成三个原始输出，都不能通过。

`prompt_replay` 重建完整请求正文。`native_rwkv` 区分 fresh bootstrap、append delta、已提交的生成 token、fork 与 rollover；rollover 的历史 parent 是归档关联，不能当作新的 State 已消费前缀。缺失创建/提交记录、rollback 候选、不同模型或 State 身份、错误 parent/delta/state-chain digest 都不能拼成合法训练上下文。原始生成 token 含已证明被传输移除的 stop suffix 时按原 token 保留，不补猜特殊 token。

实际响应的 `prompt_token_ids`、`prompt_token_ids_scope` 和 `input_bos_token_count` 会透传落盘。只有完整正文/完整消费上下文的 IDs 与重建序列及显式 BOS 前缀一致时，才填入真实 `token_ids` 并设置 `token_ids_complete=true`。原生 State 请求的 delta-only、scope 未说明或未返回 IDs 仍为未证明，不把本地重新编码改名为服务器记录。Selector 是 fresh State 的完整单次 forward，服务保存实际送入模型的 prompt IDs；其他原生 State 请求必须明确提供 `full_context` 才能证明完整前缀。本轮没有用真实在线运行证明所有后端均已返回完整元数据。

标签只允许以下权威来源：

| 权威 | 当前实现依据 |
|---|---|
| `executed_fixture` | 实际 Harness action 成功且至少推进一个当时 missing read/write root；并核对 request、Selector handoff、原始命令及 action 绑定。名称中的 fixture 不允许拿单元测试 fixture 作为来源 |
| `planner_contract` | Selector 当时只有一个 eligible operation，且原始 lane 选择与它一致；不是人为替模型选一个“更好”的操作 |
| `human_double_review` | 恰好两名不同 reviewer 对同一 request/role、精确 input/target SHA 作 `accept`；支持真实失败恢复、语义标签复核及同一真实边界的显式纠正 |

Executor 标签通过当前参数语义与 provenance 校验，必须有实际成功执行；人工 `failure_recovery_positive` 只处理真实失败上下文的恢复，不能把失败执行或未执行命令变成执行正例。Step Auditor、Finalizer 和 Final Auditor 一律需要独立语义双人复核。kernel acceptance、根推进及 completed 用于核对运行事实，不能授予这些角色语义真值；原始审计与可见根证据冲突时不能直接用作正确目标。

语义复核用途 `semantic_label` 保留原始目标；用途 `trace_correction` 必须提供与原文不同的显式 `target_text`。两份记录共同绑定 `source_run_id`、`run_id`、`request_id`、`role`、`boundary_event_id`、`input_sha256`、`target_sha256`、`original_output_record_sha256`，并提供仅来自当时可见范围的 `evidence_refs`、非空 `rationale`、`reviewer_id` 和 `decision="accept"`。两人对同一目标达成一致才接受。当前纠正适用于 Selector/Auditor/Finalizer；Executor 不接受绕过执行证据的纠正。

复核文件是 JSON 数组，放入来源登记该 run 的 `artifacts.human_reviews={path,sha256}`。先导出待复核队列，提供独立复核后，在新输出目录重新抽取；CLI 不生成或代签人工复核。测试里的 mock reviewers 仅用于代码回归。

`target_origin` 区分 `raw_model_output` 与 `human_trace_correction`；`original_target_text`、`raw_output`、`raw_output_token_ids` 始终保存原始模型证据。`target_token_ids`、`target_token_ids_source` 与 `target_tokenizer_sha256` 单独记录实际训练目标的编码；纠正目标是本地词表编码，不冒充模型生成 token。纠正也必须通过原边界的当前协议与可见事实校验，不能改写运行时结果或发明场景。

自然 `stop`、原始 output SHA、实际 raw token IDs、模型/冻结 State 以及 `postprocessed=false` 均须校验。响应缺失 finish_reason 不再补成 `stop`。当前含 `length` 或缺原始 token 的生成会排除，不能将解析后的另一个字符串或补造序列当作自然完成的模型原文。

原始模型目标保留完整原 token 流，人工纠正目标另存。JSON 解析复用生产端的停止符处理，只恢复有原 token 证明的 Markdown fence。传输已移除的普通 `\nUser:` 仍在原始目标证据中，不能重新拼到 JSON parser 输入末尾。

## 5. 排除与整批拒绝

可明确识别的缺请求/响应、缺保留边界 snapshot、缺原始输出 token、无自然 stop、无合法正例权威等，记录为逐样本排除；仅有 request 而无 durable role output 的情况也登记。此类缺口不会被补生成“正确动作”。

工件 SHA 不一致、导出事实与 SQLite 矛盾、未来 snapshot 污染、协议/source/State 身份变化、原始 token 与文本不一致、重复或互相冲突的请求、builder 与 checkpoint 字节不符等属于完整性错误，拒绝整批；不会把互相矛盾的数据静默当作普通排除后继续宣称有效。无法验证的必需来源结构也不能通过登记。

旧 trace 若没有新增的输入边界，或者已经在历史序列化中丢失了模型输入所依赖的字段顺序，不能从 prompt 倒推或重新渲染后冒充原始数据。应保留排除/拒绝证据，在授权范围的新冻结运行中采集足够材料。

## 6. 固定切分、覆盖与回归复用

project family 使用固定 80/10/10 切分：`SHA256(UTF8("rwkv-lh-role-trace-family-v1") + 0x00 + UTF8(exact_family))` 的完整 256-bit 无符号整数模 10,000，`0–7999` 为 train，`8000–8999` 为 dev，`9000–9999` 为 confirmation。同一精确 family ID 不跨 split；任何一轮都不能重新挑 family 名来移动失败样本。

相似度固定为完整 `input_text` 的 UTF-8 byte 5-gram 计数向量 cosine，无 padding；只比较同角色、不同 split 的样本，`cosine >= 0.95` 拒绝。阈值判断使用整数等价比较，避免浮点边界漂移。空范数采用“文本完全相同为 1，否则为 0”。发现近重复后记录违规，不静默删题或调整阈值。

每个请求角色必须有样本及非空 train/dev/confirmation，并始终报告九项覆盖：`failed_last_action`、`nonempty_error_type`、`directory_target`、`py_root`、`json_root`、`directory_root`、`mutate`、`execute`、`missing_target`。默认九项全部为必需；预注册的角色 scope 可指定本阶段必需子集。角色缺席、split 为空或任一必需项为零均为 `invalid`。样本数量门和训练预算在具体 run 另行预注册，管线最小非空检查不等于已经足够训练。

角色 scope 文件精确字段为 `schema_version="rwkv-lh.role-trace-coverage-scope.v1"`、非空 `objective` 和 `requirements`；requirements 的角色键须恰好等于本次 `--role`，每个值为非空、无重复的已知覆盖字段列表。文件在采集前冻结，其 SHA 写入源 `RUN_PROTOCOL.role_data_scope_sha256`，来源登记顶层添加 `coverage_scope={path,sha256}`。例如聚焦 Selector 目录与缺失目标时可登记这两个覆盖项；其余七项仍完整报告为观察值，不能在结果出来后把缺项移出门槛。

Auditor/Finalizer 的覆盖是其实际可见 evidence refs 所引用动作的**来源场景**：回到该动作执行前的 durable assignment，统计它的阶段、目标类型及失败恢复上下文。它不表示这些角色的 prompt 有 Selector 同名字段。未引用动作、后续 assignment、今天的文件类型均不得贡献覆盖。

首次审计通过后，在 owner 已有明确授权范围内冻结每角色一份不变的回归集，不重复索取同一授权；未授权的新范围按统一规范登记。后续仅增加 train；复用时必须显式提供旧工件以及从独立冻结登记获得的文件 SHA 和 fingerprint，不能刚读取旧文件就现场算出两个值充当独立身份凭据：

```bash
.venv/bin/python -m rwkv_lh.goal_state_protocols.role_trace_dataset_v1 extract \
  --registration /home/chase/GitHub/RWKV-LH/data/experiments/NEXT_ROLE_TRACE/source_registration.json \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/NEXT_ROLE_TRACE/audit_01 \
  --prior-regression /home/chase/GitHub/RWKV-LH/data/experiments/APPROVED_FREEZE/regression_candidate.json \
  --regression-sha256 FROZEN_FILE_SHA256 \
  --expected-regression-fingerprint FROZEN_REGRESSION_FINGERPRINT
```

三项复用参数必须同时给出。新的 dev/confirmation family 行会排除，旧回归内容、角色集合、切分、覆盖要求、scope SHA、冻结的上游 State 条件和 fingerprint 均须保持；新增 train 与旧回归仍执行跨 split 相似度检查。不同上游 State 的来源不能混入同一角色回归。CLI 不搜索历史 confirmation 文件，也不会读 Real Agent Holdout。

## 7. 本轮得到的操作经验

1. **先验证落盘重建。** 内存 snapshot 全部通过仍不足够。本轮实际 SQLite 回归发现 `sort_keys=True` 会丢失嵌套事实的插入顺序，使四个非 Selector 角色重建出的 prompt SHA 失配。Store 已改为保留映射顺序，事件和投影的 canonical digest 算法不变；没有逐字段补 order 特例，也没有改变角色 renderer。红绿证据见 [SQLite 红测](../data/experiments/ROLE_TRACE_DATASET_R1_20260907/inputs_sqlite_red.txt) 与 [输入绿测](../data/experiments/ROLE_TRACE_DATASET_R1_20260907/inputs_green.txt)。
2. **目标类型必须在调用前记录。** 文本路径本身不证明当时是目录、文件或 missing target；读当前磁盘会泄漏后续变更。新增 assignment 事件只记录当前 Controller/Harness 已有事实，不新增模型调用或选择工具的逻辑。
3. **只保存 ledger 的最后 prompt 不够。** native delta、fresh State 重置、真实生成 stop 和 fork/rollover 的物理含义必须分别核对；原始输出 token 与本地重建输入 token 不能混用。
4. **完成与审计边界按实际生产事件绑定。** 不能凭名字推断 Finalizer 已被 Final Auditor 接受；应使用其具体 decision/request、边界与 accepted audit。三菜单 Selector 也必须保留每一 lane 的原始请求、token 和投票，不能把集成后的结果当作三条原始模型输出。
5. **签名完整不等于事实一致。** 重新计算伪造 JSON 的 SHA 不会使它与 SQLite 因果链相符；冻结来源范围、源码身份、snapshot revision 和各导出之间必须交叉验证。
6. **候选有效与 Agent 提升分开报告。** 单题 fixture 缺少非空的三种 split，仍应得到 invalid；后序角色未到达则只影响对应角色。测试不计训练 run，也不能代替新生产数据、固定回归与 Agent 消融。

新增 durable 事件增加了日志和 snapshot 写入，并会改变后续因果 ID；它不增加 Controller transition、模型调用或 Planner 步数限制。由于源码身份及因果记录变化，后续比较仍须重新冻结、两臂同代码运行。完整运行与训练权限继续遵循 [AGENTS](../AGENTS.md)、[统一规范](G1J_UNIFIED_PROTOCOL_ITERATION_PLAN.zh-CN.md) 和 [HANDOFF](HANDOFF.zh-CN.md)。
