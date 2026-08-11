# RWKV-LH architecture findings after Basic-10 ablation

## 当前结论边界

本文依据固定 core30 中的前 10 题、固定 G1i-13.3B、固定 vllm-rwkv 端点以及
`utf8-byte-ngram-cosine.v1` 指标形成。完整 42 题尚未执行，因此本文是整改设计输入，
不是“问题已解决”的声明。

## Basic-10 结果

| 方案 | Agent + external 通过 | External 通过 | 模型请求 | Attempt | 主要含义 |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline | 1/10 | 3/10 | 337 | 56 | 当前架构 |
| no mandatory model cross-check | 5/10 | 6/10 | 194 | 39 | 删除强制语义复核能减少错误拒绝，但丢失部分有用判断 |
| no model failure analysis | 3/10 | 5/10 | 174 | 39 | 失败分析成本高，但并非纯冗余 |
| minimal validation + recovery | 4/10 | 5/10 | 224 | 61 | 两项删除不能直接叠加 |
| task-local validation binding | 8/10 | 8/10 | 359 | 75 | 正确状态边界显著改善正确率，但恢复循环仍造成请求膨胀 |
| separated progress/satisfaction by prompt | 3/10 | 5/10 | 191 | 33 | 状态语义方向正确，但不能依赖模型自由 JSON 独自维护结构不变量 |

task-local 方案把 baseline 中的 7 个 semantic-conflict runs 降为 0，但仍有 6 个
repeated-attempt runs。B09 是 agent-completed / external-failed 假阳性；B02、B03 分别使用
109、52 次请求才完成；B10 在 task-local 方案中重复执行失败测试，在 progress/satisfaction
提示词方案中产物已经外部通过但 agent 因模型协议错误未完成。

## 已确认的系统性根因

### 1. `goal_criteria` 同时承担“推进”与“满足”两种相反语义

`model.py` 的规划提示把字段定义为任务“advances”的 criterion，并要求每个任务非空；
`controller.py` 的完成边界却把 completed task 上的相同字段作为 criterion 已满足证据。
B09 因此只读取 `scores.csv` 就覆盖全部 GC，未创建 `stats.json` 仍由 agent 宣布完成。

依赖图应表达推进关系；Goal 满足必须来自带 verifier evidence 的独立状态。不能用一个字段兼任。

### 2. 任务验证和 Goal 完成使用同一模型上下文

当前 cross-validation 同时看到完整 Goal、当前任务、bound criteria 和工作记忆。模型多次把
“当前读取任务已获得证据”误判为“整个 Goal 尚未验证”。任务局部输入把 Basic-10 外部通过提高到
8/10，证明 RWKV 语义判断有价值，错误来自作用域混合，不是模型层本身应被删除。

### 3. 失败计数绑定 task id，replacement 会重置失败历史

`_same_failure_count` 只统计当前 TaskNode 的 attempts。replan 创建 replacement 后，新的 task id
重新从零计数。B02、B03、B05、B08、B10 均出现相同 action type 的 replacement；系统把同一路径
误当成新策略继续运行。

失败状态必须绑定稳定的 recovery lineage，并记录 action/verifier/failure fingerprint、历史决策和预算。

### 4. 模型拥有结构 ID 与 supersede 映射

replan 要求 RWKV 自行生成全局唯一 task id 和 supersede 映射。实际出现复用已有 ID、未 supersede、
replacement 自依赖等协议错误；两次 JSON 修正失败后整个 run 终止。ID 分配、引用重写和 DAG 校验
属于确定性结构层，不能由模型自由生成。

### 5. 验证失败无法归属并回传给生产者

TaskGraph 禁止 completed task 再迁移。验证任务发现上游实现错误后，controller 只围绕当前验证任务
调用 failure analysis/replan。B10 因而把失败的 `run_command` 替换为另一个 `run_command`，没有把
测试输出交给 `slug.py` 的生产任务进行纠正。

ValidationResult 必须声明 subject/producer；恢复层应创建新的 corrective producer task，并使后续
验证依赖它，同时保留旧 completed task 作为历史，不篡改已发生事件。

### 6. RWKV recurrent state 尚未进入 runtime contract

当前 `OpenAICompatibleRWKVClient` 只发送普通 OpenAI-compatible prompt/completion，并可记录 token ids；
RunState、store 和 model invoker 都没有 recurrent-state handle、父子关系、fork、commit、rollback 或
durable snapshot。现在的“state”主要是 JSON 状态和重放 prompt，尚未发挥 RWKV 的原生递归状态优势。

此外当前端点探测中 `response_format=json_object` 返回 HTTP 500。后续固定复测确认 vllm-rwkv 原生
tool parser 确实存在，但只在部分请求产生 `tool_calls`，正确率和延迟均显著落后于显式 G1i
`/completions`；因此架构不能仅因服务启动了 parser 就假设它可靠，必须以 capability negotiation 和
固定数据回归为准。

### 7. 线上 G1i 工具协议应是 state 增量协议，不是默认 chat template

用户明确的协议在同一 RWKV state 上按块追加：首次为 `System: Tools`、任务 User 块、
`Assistant: ```json`；工具执行后只追加 `User: Function output: ...` 和新的
`Assistant: ```json`，直到模型选择 `submit`。没有 state handle 时，完整前缀重放只是等价 fallback。

固定 5 题、2 次重复的 state-equivalent 格式探测中，线上 fenced 格式首轮 10/10 可解析、10/10
工具名正确、6/10 参数 exact；Function output 后 10/10 可解析、8/10 选择 submit、2/10 参数 exact。
当前项目格式对应为首轮 8/10 参数 exact、后续 6/10 选择 submit。线上格式后续状态路由更好且生成
更短，但参数契约仍需加强，不能只替换字符串模板就宣称完成。

直接把同样内容交给 `/chat/completions` 默认 template 时，20 次回复均未以 ` ```json` 开头，说明
服务端默认 chat template 没有自动实现线上增量协议。项目必须显式控制 prompt chunk 或配置正确的
服务端 template/state API。

29610 的 OpenAPI 只读探测发现 17 个路径，但没有 state/recurrent/snapshot 路径。出现的 `stream_state`
属于 chat/completion derender 的输出格式状态；`cache_salt`、prompt cache breakpoint 和 cached tokens
属于前缀缓存能力，不能代替可持久化、可 fork/rollback 的 RWKV recurrent state。使用最后一条 assistant
消息预填 ` ```json` 并设置 `continue_final_message=true` 时，服务返回 `error_line_length_XXX` 类模板哨兵，
20/20 均无可解析 JSON。因此当前可靠入口仍是 `/completions` 上显式渲染线上 G1i chunk；服务端 state
接口完成前只能使用完整前缀重放/前缀缓存 fallback。

## 建议的目标状态契约

### Task / Goal evidence

- `TaskNode.dependencies`：只表达推进关系。
- `TaskNode.satisfies_criteria`：只声明该任务完成后可能直接建立的 Goal 条件；允许为空。
- `CriterionEvidence`：`criterion_id`、`status`、`owner_task_id`、`attempt_id`、`validation_refs`、
  `artifact_refs`、`state_ref`、`verified_at`、`invalidated_by`。
- Goal 完成只读取 `CriterionEvidence(status=verified)`，不直接读取任务规划声明。

### Recovery lineage

- `RecoveryState`：`lineage_id`、`root_task_id`、`failed_task_id`、`subject_task_id`、
  `failure_fingerprint`、`same_failure_count`、`decision_history`、`remaining_budget`。
- replacement 继承 lineage，不能因换 task id 清零。
- 相同 failure/action/verifier fingerprint 达到固定近重复阈值时，禁止再次生成等价 replacement；
  必须改变生产策略、回退到 subject producer，或明确 blocked。

### RWKV model state

- `ModelStateRef`：`state_id`、`parent_state_id`、`lane`、`model`、`digest`、`token_count`、
  `durable_ref`、`created_at`、`status`。
- lane 至少区分：`goal`、`task:<id>`、`validation:<attempt>`、`recovery:<lineage>`。
- validation 使用只读 fork，不得污染主任务 state；成功决策可提交摘要/证据，不能隐式提交完整生成状态。
- recovery 从失败前的稳定 task state fork；成功 correction commit，重复/错误分支 rollback。
- 服务重启需要 durable snapshot 或可验证的 prompt replay fallback；不能只有易失的服务端缓存 ID。

## 需要修改的模块

### `rwkv_lh/schema.py`

- 升级 RunState schema 版本并提供显式迁移。
- 将规划相关性和已验证 Goal evidence 分离。
- 增加 `CriterionEvidence`、`RecoveryState`、`ModelStateRef`。
- 为 ValidationResult 增加 `subject_task_id`、`criterion_ids`、`evidence_refs`、`failure_fingerprint`。

### `rwkv_lh/task_graph.py`

- 由 controller/store 分配稳定 task id，模型只返回局部节点引用或无 ID 节点。
- 增加 corrective successor / invalidation 语义；保留旧 completed 节点不可变，但允许其证据被新失败事件标为失效。
- DAG 引用重写、replacement lineage 和 cycle 检查全部在确定性层完成。

### `rwkv_lh/model.py`

- 规划输出不再负责全局 ID、supersede 和完成状态。
- plan 只提出语义任务、依赖意图和直接 satisfaction claim；controller 校验后物化。
- cross_validate 使用 task-local state fork；Goal-level judge 只在完成边界调用，且读取 CriterionEvidence。
- failure analysis 输入结构化 RecoveryState，输出有限决策与 corrective intent，不直接修改图。
- JSON 修复失败返回 typed protocol failure，由 controller 决定 retry/fallback/block，不直接让整个 run 异常终止。
- 工具执行主循环使用 G1i 原生的一次一函数调用协议；长程规划只在确有必要的边界触发，不再把每个
  action 固定拆成 tool choice、arguments、verification design 三次模型请求。

### `rwkv_lh/controller.py`

- 拆成明确阶段：plan materialization、task execution、evidence commit、goal coverage、recovery routing。
- task pass 只提交 TaskEvidence；criterion verified 需要绑定 verifier evidence 后单独提交。
- 维护 recovery lineage；跨 replacement 计算重复失败。
- 验证失败根据 subject_task_id 路由到 corrective producer，而不是只替换 verifier。
- 保留有价值的 RWKV failure analysis，但由确定性 guard 决定允许的状态迁移。
- 将 `submit` 视为候选终止意图而不是直接完成；controller 仍需依据 typed evidence 与 Goal coverage
  决定接受、返回 Function output 错误，或进入 recovery fork。

### `rwkv_lh/prompting.py`

- 增加独立 `G1iToolDialogFormatter`，不要继续把线上协议混在 `### User/### Assistant` JSON helper 中。
- 初始 chunk：System Tools 只写入 state 一次；每轮只追加一个 User 块与
  `Assistant: ```json` 生成前缀。
- Function output 使用固定 envelope，至少包含 call id、success、typed result/error、evidence refs 和
  state revision；不得把任意工具 stdout 无边界地直接注入 state。
- 解析第一个完整 JSON function call；未知 name、缺失参数和额外参数由确定性 schema validator 拒绝，
  再把 typed Function output 错误追加给 RWKV 修正。

### `rwkv_lh/validation.py`

- verifier 输出 typed evidence claim，而不是直接拥有 Task/Goal completion。
- 每个 verifier 必须声明 subject 和证据来源；模型 cross-check 只能补充语义证据，不能覆盖失败的确定性证据。
- 同一 evidence 的重复验证复用结果或明确失效原因，避免模型重复判断相同观测。

### `rwkv_lh/memory.py`

- 不再向每个 task 注入完整 Goal + 全部状态。
- 按 lane 组装最小 state projection：当前任务、依赖 evidence、当前 failure lineage、允许动作契约。
- Goal state、task state、validation fork、recovery fork 的输入边界分别测试。

### `rwkv_lh/store.py`

- 原子持久化 CriterionEvidence、RecoveryState 和 ModelStateRef 的 commit/rollback 事件。
- 保存 state parent/digest/durable reference；恢复时验证模型、digest 和父链。
- checkpoint retention 同时考虑 JSON state 与 recurrent state snapshot 生命周期。

### `rwkv_lh/runtime/protocol.py`、`runtime/openai_compat.py`、vllm-rwkv 服务端

- 增加 capability negotiation，明确 JSON、tool_calls、state resume/fork/export 是否真实可用。
- 请求/响应支持 opaque recurrent state handle，避免通过普通 JSON 传输巨大 tensor。
- 需要服务端 state create/resume/fork/commit/delete/export/import 接口以及模型/shape/dtype/digest 校验。
- OpenAI-compatible 功能不可用时必须明确降级到当前 prompt replay，不能静默假装 state 已复用。
- runtime 应暴露 `append_and_generate(state_ref, user_chunk, assistant_prefix)` 语义；初次调用创建 state，
  后续 Function output 从返回的 state_ref 恢复。默认 `/chat/completions` 只作为经过能力验证的适配器，
  不能成为 G1i 协议的隐式格式拥有者。

## 实施顺序

1. 先实现 schema v2、typed evidence、稳定 ID 分配和 recovery lineage；这些不依赖服务端 state。
2. 把 task-local validation 作为新边界实现，保留 RWKV 语义层。
3. 实现 producer-directed recovery 和近重复 guard，先回归 Basic-10 的 B02/B03/B09/B10 同类路径。
4. 给 vllm-rwkv 增加 state capability/handle 接口，再接入 ModelStateRef 与 lane fork/commit/rollback。
5. 固定新协议与数据后运行 42 题、LH-Control-30、离线测试、异常/恢复/服务重启测试。

任何阶段都不得只修 B09 或 B10；它们只是状态覆盖错误和 recovery ownership 错误的代表入口。

## 2026-08-11 G1i 工具链整改结果

本轮没有直接采用“全工具表一次 function call”。生产链消融中该方案仅 3/5 工具名正确，并让一个
已经正确生成的 `read_json` 动作被模型生成的无效 verifier 参数阻断。说明 action type narrowing 是
对 RWKV 有效的选择空间边界，不能因为减少请求数就删除。

最终候选结构为：紧凑 action-type selection → 单工具 `g1i-tool-dialog.v1` arguments call → Harness
确定性内建 postconditions。自定义 action 才回退到 RWKV verifier design。协议层归一化 JSON-string
arguments；工作记忆不再暴露绝对 workspace root；Harness 拒绝绝对工具路径；`write_file` 固化
`overwrite=true` 幂等重试不变量。

固定五题最终 `g1i_production_action_validation_run5.json` 为 5/5 完成、5/5 工具名正确、4/5 exact、
平均 `utf8-byte-ngram-cosine.v1` 相似度 0.988121。唯一非 exact 是已存在根目录上的
`create_parents=true/false`，没有修改预注册 expected 或指标口径。离线产品回归为 97 passed。

本段仍不是完整问题解决声明：Goal evidence、recovery lineage、producer-directed correction 和真实 RWKV
recurrent state 尚未实现；完整 42 题结果需在后续回归节补充。
