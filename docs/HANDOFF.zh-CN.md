# RWKV-LH 当前结构与交接

更新时间：2026-09-04（Asia/Shanghai）

本文只描述当前 HEAD：唯一控制链、实际运行位置、各角色真实输入、期望输出、状态传递、已知缺陷和 StateTune 接入合同。

## 1. 唯一控制链

当前架构标识为：

```text
rwkv-stateful-goal-loop.v4
```

完整链路：

```text
Immutable Goal + Append-only Causal Ledger
  -> Strong Planner
  -> 2.9B Selector（三种固定菜单顺序、三份独立 WKV、一次投票）
  -> 13.3B Executor
  -> Harness
  -> Controller Mechanical Evidence Gate
  -> Step Auditor
  -> Evidence Kernel
  -> Strong Stage Checker
  -> Finalizer
  -> Final Auditor
  -> User-visible Final
```

这是一条架构。角色分离只表示职责和 WKV State 的边界：

- Planner 只拆解 stage/step 并标注步骤 phase，不选具体工具、不填参数、不判定完成。
- Selector 只选一个 operation，不填参数。
- Executor 只为已经选定的 operation 填参数，不能改选工具。
- Harness 执行工具并生成事实。
- Controller 机械检查成功 Action 是否覆盖 Planner 声明的读写根。
- Step Auditor 只判断当前 step 的语义证据。
- Stage Checker 只检查一个已完成 stage 是否可以推进。
- Finalizer 只生成候选答案。
- Final Auditor 是终局语义审核；Controller 在审核通过后提交最终输出。

Planner 写出的“需要读取”“将验证”或 `success_evidence` 是要求，不是完成证据。完成顺序固定为：成功 Action -> 机械覆盖 -> Step Auditor -> Evidence Kernel。

## 2. Selector 投票、`ABSTAIN` 和停止语义

2.9B Selector 不拥有一个单独的 Agent，也不存在第二条控制链。它是当前链中的精确工具分类器。

现有 Head 物理上仍有 25 个输出：23 个可执行 operation、`final_answer` 和历史类别 `ABSTAIN`。当前 Controller 不再把 `ABSTAIN` 放入任何可执行 frontier 的 `eligible_labels`，因此它的高 logit 不会中止一个已经由 Planner 和 Controller 确定 phase、scope 与候选集的步骤。无候选、身份不一致、协议错误和运行基础设施失败分别由 Controller 的显式状态处理，不委托给 Head 猜测。

普通步骤使用三个预登记菜单顺序：`canonical`、`rotate_8`、`rotate_17`。每个顺序持有一份独立 WKV；三份 State 接收相同 frontier 和 Action 历史，但 menu bootstrap 顺序不同。禁止合并或平均 WKV。每路在相同 eligible labels 中产生一个 raw-logit argmax，然后按以下固定规则合成唯一 operation：

1. 有 2/3 相同则取多数；
2. 三路各不相同时，只在三个得票 label 中比较三路的中位排名；
3. 中位排名仍相同，再比较中位标准化 logit；
4. 仍相同按固定 canonical class order 决定。

Selector 的 WKV 与 Executor 的 WKV 不共享，是为了避免“选择工具”的状态污染“填写参数”的状态。

需要区分三种现象：

| 现象 | 含义 | 当前行为 |
|---|---|---|
| `ABSTAIN` raw logit 最高 | 历史 Head 对当前输入偏向第 25 类 | 因不在 eligible 集合而被屏蔽，仍保留原始 logit 供分析 |
| eligible 集合为空 | Planner phase、运行策略和 Harness 能力交集为空 | Controller 明确报协议错误，不调用 Executor |
| Selector 身份不一致 | 服务可访问，但模型/Head/State/协议 SHA 与配置不同 | 启动或调用时 fail closed |
| 工具不存在 | label 不在当前 Harness/菜单中 | 协议拒绝，绝不转交 Executor |

## 3. 全局状态与局部 State

全局权威是 append-only causal ledger，保存：

```text
immutable goal
rolling plan + plan revision
step_id + step_revision
tool selection handoff
Action / result / error / side effect
Artifact / artifact revision
mechanical evidence gap
audit boundary and verdict
model / Head / State / protocol / tool identities
run terminal or resumable status
```

模型文本、Planner 声明和 WKV 都不能直接修改全局完成事实。

局部状态范围：

| 角色 | State 范围 | 输入事实范围 |
|---|---|---|
| Selector | 同一个 `(step_id, step_revision, menu_order_id)` 内三路分别延续；换 step/revision 或进入 final 时重建 | 当前 step、phase、当前 step 的 Action、最新审核缺口、eligible labels |
| Executor | 每个 selected action 从配置的初始 State 干净启动 | 当前 step 和直接依赖 step 的受控 Action 投影、唯一工具 schema |
| Step Auditor | 每个 audit boundary 干净启动 | 当前 step 与该 boundary 可引用的 evidence |
| Finalizer | 完整 plan 通过后干净启动 | 已完成 steps、已提交 facts、证据记录、输出格式合同 |
| Final Auditor | 每个 final boundary 干净启动 | Finalizer 候选与全部可引用证据 |

一次 action 的状态流：

1. Controller 取当前 frontier step 和 revision。
2. Controller 按 Planner phase、运行策略、Harness 能力和机械状态生成 eligible labels。
3. 三个 Selector lane 分别输出 25 个 logits，并在同一 eligible labels 中取各自 argmax。
4. Controller 按固定投票规则合成 operation，把三路 raw 结果、参考 checkpoint、Executor 父状态和工具合同绑定成 handoff。
5. Executor 从 clean role State 启动，读取 handoff 和受控事实，只输出参数完整的同名函数调用。
6. Harness 校验并执行，将结果写入 ledger。
7. Controller 计算 read/write roots 的机械覆盖；缺口存在时返回下一轮，不调用 Step Auditor。
8. 机械条件满足后，Step Auditor 给出 `continue` 或 `repair`。
9. 一个 stage 的 steps 全部通过后，Strong Stage Checker 给出 `advance` 或 `repair`。
10. plan 全部完成后，Finalizer 生成候选，Final Auditor 给出 `ready_for_final` 或 `repair`。

## 4. 各角色的输入与期望输出

### 4.1 Strong Planner

输入是 `GoalPlanRequest` 的 JSON 对象：

```json
{
  "run_id":"RUN-ID",
  "goal_digest":"SHA256",
  "plan_revision":0,
  "active_plan":{},
  "latest_audit":null,
  "latest_stage_review":null,
  "workspace_manifest":{},
  "recent_action_facts":[],
  "current_requirement":"用户的不可变目标"
}
```

如果 Controller 拒绝了一次 patch，还会加入 `local_validation_repair`。`current_requirement` 始终放在业务 JSON 尾部。

期望输出只允许一个 JSON 对象：

```json
{
  "add_stages":[
    {
      "stage":1,
      "steps":[
        {
          "step_id":"S1",
          "objective":"一个明确职责",
          "phase":"observe",
          "depends_on":[],
          "success_evidence":["可观察的完成证据"],
          "read_roots":["src"],
          "write_roots":[],
          "constraints":[]
        }
      ]
    }
  ],
  "replace_stages":[],
  "discard_step_ids":[],
  "reason":"简短规划理由"
}
```

不允许 Markdown、工具调用、最终答案或额外字段。Controller 绑定 `patch_id`、`base_revision` 和 schema version。

`phase` 只能是 `observe`、`mutate`、`execute` 或 `derive_evidence`。一个 step 只能承担一种职责；新计划中的读取、修改、命令执行和证据推导必须拆开，并用前一 stage 的 dependency 传递已提交事实。Planner 不得输出具体 operation 名。

### 4.2 2.9B Selector + Head

首次调用的完整模型前缀由三段组成：

```text
SelectorIntentMenuV1: <菜单 JSON，只有 25 个 name/description>
SelectorIntentRoleV1: <协议身份 JSON>
SelectorIntentPromptV1: <当前 frontier JSON>
```

同一 `(step_id, step_revision)` 的后续调用只向该 Selector State 追加新的 `SelectorIntentPromptV1`。

当前 frontier JSON 的业务字段：

```json
{
  "schema_version":"rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1",
  "role":"selector_intent",
  "stage_objective":"GoalFrontierStateV2: {...}",
  "stage_role":"tool_intent",
  "progress":{
    "completed_stage_count":0,
    "action_index":0,
    "succeeded_operations":[],
    "failed_operations":[],
    "protocol_rejection_count":0
  },
  "eligible_labels":["search_text","read_file","read_json","file_digest"],
  "current_question":"Choose exactly one eligible operation label..."
}
```

`stage_objective` 内含当前 step、step revision、读写根、success evidence、当前 step 进度、最新 Action、最新 audit gap、eligible tool 描述和最后的 `current_objective`。

普通步骤会分别用 `canonical`、`rotate_8`、`rotate_17` 三种完整菜单顺序运行。`class_order` 始终是下面的 canonical 顺序，菜单顺序变化不能改变 logit 下标语义。线上期望输出不是生成文本或函数调用，而是：

```text
25 个有限 raw logits
每一路 eligible labels 内的确定性 argmax label
每一路独立的下一份 Selector state_ref/state_digest/token_position
固定 2/3 多数或三路平局裁决后的唯一 operation
完整模型、Head、State、菜单和协议身份
```

固定类别顺序：

```text
list_directory  search_text  read_file  read_json  file_digest
write_file      write_json   patch_json replace_text remove_line
append_file     make_directory copy_file move_file   delete_file
bind_evidence   check_command run_command web_search connector_lookup
calculator      date_diff    current_time final_answer ABSTAIN
```

Selector 不输出 `read_file()`、`name()`、参数对象、schema 名或 role 名。

### 4.3 13.3B Executor

每个 selected action 的完整输入由 clean Executor bootstrap 和一段 `ExecutorArgsPromptV1` 组成。

bootstrap 中的受控 JSON 包含：

```text
protocol
constraints
workspace_manifest
action_result_projection_version
recent_action_sequence_range
recent_exact_action_records
instruction
```

随后追加当前唯一参数任务：

```json
{
  "schema_version":"rwkv-lh.g1j-per-stage-state-tuning.executor-args.v1",
  "role":"executor_args",
  "current_requirement":"当前 step 的 objective",
  "selected_operation":"read_file",
  "selected_tool_contract":{"name":"read_file","description":"...","parameters":{}},
  "committed_fact_refs":["ACTION-ID"],
  "executor_history":[{"event_id":"...","event_type":"...","content_refs":[]}],
  "current_question":"Return one canonical direct call..."
}
```

实际生成边界以以下锚点结束：

````text
**Tool Call:**

```json
````

这个开放围栏是输入侧续写锚点，不是模型输出格式错误。

期望输出是一个 canonical direct-call JSON：

```json
{"function":"read_file","params":{"path":"src/app.py","start_byte":0,"max_tokens":4096}}
```

硬要求：`function` 必须与 `selected_operation` 完全相同，`params` 必须是 JSON object，所有必填参数必须显式给出。不能输出 Python dict、`name()`、解释文字或另一个 operation。

解析器能规范化少量已闭合 envelope 拼写，但训练 target 和发布门禁只接受 canonical 形式；规范化层不能选择工具、补语义参数或改写函数名。

### 4.4 Harness

输入是 Executor 已通过协议与工具 schema 校验的：

```json
{"function":"<operation>","params":{}}
```

Harness 再绑定固定 workspace root、运行策略、网络策略和命令白名单。期望输出是持久 Action 事实，核心字段为：

```text
action_id, sequence, operation, arguments, status,
result, error, artifact_refs,
workspace_digest_before, workspace_digest_after
```

Harness 不规划、不选工具、不写最终答案。

### 4.5 Controller Mechanical Evidence Gate

输入：当前 `step_id/step_revision`、该 revision 绑定的 Action、Planner 声明的 `read_roots/write_roots`。

输出是确定性对象：

```json
{
  "active_step_id":"S1",
  "active_step_revision":1,
  "assigned_action_ids":[],
  "successful_action_ids":[],
  "missing_read_roots":[],
  "missing_write_roots":[],
  "gaps":[],
  "completion_preconditions_satisfied":true,
  "completion_authority":false,
  "source":"controller_mechanical_evidence_gate"
}
```

它只验证机械覆盖，不代替 Step Auditor 的语义判断。

### 4.6 Step Auditor

业务输入：

```json
{
  "boundary":"observation_complete",
  "active_step":{
    "step_id":"S1",
    "objective":"...",
    "stage":1,
    "depends_on":[],
    "success_evidence":["可观察条件"],
    "obligation_ids":[],
    "read_roots":[],
    "write_roots":[],
    "allowed_operations":[],
    "constraints":[]
  },
  "available_evidence_refs":["ACTION-ID"],
  "evidence_records":[{"evidence_ref":"ACTION-ID","action":{}}]
}
```

线上完整输入还包含唯一 `audit_decision` 工具定义和 Tool Call continuation anchor。

期望输出：

```json
{
  "function":"audit_decision",
  "params":{
    "verdict":"continue",
    "step_id":"S1",
    "step_complete":true,
    "evidence_refs":["ACTION-ID"],
    "gaps":[],
    "reason":"证据满足当前 step"
  }
}
```

`continue` 必须同时满足 `step_complete=true`、至少一个合法 evidence ref、`gaps=[]`；否则只能 `repair`，并提供非空 gaps。

### 4.7 Strong Stage Checker

输入：

```json
{
  "run_id":"RUN-ID",
  "goal_digest":"SHA256",
  "stage":1,
  "stage_steps":[{"step_id":"S1","accepted_evidence_refs":["ACTION-ID"]}],
  "workspace_manifest":{},
  "recent_action_facts":[],
  "current_requirement":"用户的不可变目标"
}
```

期望输出只有三个字段：

```json
{"verdict":"advance","gaps":[],"reason":"该 stage 的证据一致"}
```

`repair` 必须带非空 gaps。Controller 绑定 stage、reviewed step IDs、evidence refs、review ID 和 schema identity。

### 4.8 Finalizer

业务输入：

```json
{
  "immutable_goal":"用户的不可变目标",
  "completed_steps":[{"step_id":"S1","evidence_refs":["ACTION-ID"]}],
  "committed_facts":[{"fact_id":"fact:ACTION-ID","value":{},"evidence_refs":["ACTION-ID"]}],
  "evidence_records":[{"evidence_ref":"ACTION-ID","action":{}}],
  "format_contract":{
    "format_id":"goal-user-response-v1",
    "language":"match_immutable_goal",
    "required_sections":[]
  }
}
```

线上完整输入还包含唯一 `final_answer` 工具定义和 Tool Call continuation anchor。

期望输出：

```json
{"function":"final_answer","params":{"text":"面向用户的完整答案"}}
```

Finalizer 只产生候选，不拥有完成权限。

### 4.9 Final Auditor

业务输入：

```json
{
  "immutable_goal":"用户的不可变目标",
  "completed_steps":[{"step_id":"S1","evidence_refs":["ACTION-ID"]}],
  "committed_facts":[{"fact_id":"fact:ACTION-ID","value":{},"evidence_refs":["ACTION-ID"]}],
  "available_evidence_refs":["ACTION-ID"],
  "evidence_records":[{"evidence_ref":"ACTION-ID","action":{}}],
  "final_candidate":{"function":"final_answer","params":{"text":"..."}}
}
```

期望输出：

```json
{
  "function":"audit_decision",
  "params":{
    "verdict":"ready_for_final",
    "step_id":"",
    "step_complete":false,
    "evidence_refs":["ACTION-ID"],
    "gaps":[],
    "reason":"候选答案已被证据覆盖"
  }
}
```

`ready_for_final` 要求 `gaps=[]`；否则返回 `repair` 和非空 gaps。Final Auditor 不能完成任何 plan step。

### 4.10 推理引擎

13.3B 角色通过 `rwkv-lh.native-state.v1` 使用 create/resume/fork/commit/rollback/export/import。每次请求输入为：文本 delta、父 `state_ref`、cache binding、模型身份和 State profile 身份；输出为生成文本、raw token IDs、finish reason、下一份 state ref/digest 和服务身份。

Selector 服务输入为：`menu_order_id`、bootstrap 或同顺序 parent state、step 文本、eligible labels、input/menu digest 和 expected runtime identity；输出为 25 logits、该路 argmax label、下一份 Selector state 与完整身份。两条服务接口共同服务于同一个 Goal Loop。

## 5. 当前工具表与 phase 分类

当前可执行工具共 23 个。Planner 的四个 phase 与 Controller 固定候选集为：

| 类别 | operation |
|---|---|
| `observe` | `list_directory, search_text, read_file, read_json, file_digest, web_search, connector_lookup` |
| `mutate` | `write_file, write_json, patch_json, replace_text, remove_line, append_file, make_directory, copy_file, move_file, delete_file` |
| `execute` | `check_command, run_command` |
| `derive_evidence` | `bind_evidence, calculator, date_diff, current_time` |

`final_answer` 由 Finalizer 处理，`ABSTAIN` 不进入 Executor。

四类 phase 已用于 Planner 输出验证和 Selector 候选收窄。它们当前不用于加载 Executor State profile；`runtime/executor_profiles.py` 仍只支持任务级 `disabled` 或 `retrieval-policy-v1` 路由。若以后按 phase 加载不同 StateTune，必须先用固定数据、参数、阈值和评价算法完成消融，不能让路由器替代 Selector 选择具体 operation。

## 6. StateTune 数据与线上输入必须一致

当前 Git 仓库没有可直接交给训练器的完整训练产物；`data/datasets/` 中保留的是数据说明与合同。开始生成训练数据前，必须先为每个角色建立唯一的 full-serving-transcript renderer，并由数据生成和 runtime 同时调用。

五个可训练角色：

| 角色 | 业务 schema | target |
|---|---|---|
| Selector Intent | `rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1` | 精确 operation label；若使用 suffix 训练则为 `\nSelectorIntentV1: <label>` |
| Executor Args | `rwkv-lh.g1j-per-stage-state-tuning.executor-args.v1` | canonical selected-operation call |
| Step Auditor | `rwkv-lh.g1j-per-stage-state-tuning.auditor-step.v1` | canonical `audit_decision` |
| Finalizer Answer | `rwkv-lh.g1j-per-stage-state-tuning.finalizer-answer.v1` | canonical `final_answer` |
| Final Auditor | `rwkv-lh.g1j-per-stage-state-tuning.auditor-final.v1` | canonical `audit_decision` |

训练行固定为：

```json
{"prompt":"<线上生成前的完整 UTF-8 前缀>","target":"<唯一目标后缀>","text":"<prompt 与 target 的逐字节拼接>"}
```

硬门禁：

1. `text == prompt + target`，且只对 target suffix 计算 loss。
2. UTF-8、LF、`ensure_ascii=false`；loader 不再追加空格、换行、围栏、chat template、BOS 或 EOS。
3. 每行同时验证 `training prompt bytes == runtime pre-generation bytes` 和 token IDs 完全一致。
4. manifest 固定 dataset、source、generator、verifier、full renderer、parser、tokenizer、operation registry、模型和文件 SHA。
5. 同一 trajectory 及其 counterfactual 不能跨 train/dev/sealed。
6. 错误模型输出只能成为 failure evidence，不能直接成为 target。
7. Selector 的同一语义样本必须覆盖三个固定 menu order；三种顺序的 target label 和 canonical class index 必须一致，trajectory 按 order 分别续接 State。
8. 可执行 frontier 不生成 `ABSTAIN` target；无 eligible operation 是 Controller 状态，不是 Selector 训练标签。
9. 在同一数据、输入、采样和评价算法下先跑 zero-State，再跑 StateTune；每个候选最多三次，按预登记指标选最优。

State checkpoint 格式为 `rwkv-peft-time-state.v1`。文件是 PyTorch dictionary，键严格为每层：

```text
blocks.<layer>.att.time_state
```

tensor 必须为有限、非全零 `torch.bfloat16`，单层 shape 为 `(total_num_heads, head_size, head_size)`。

profile manifest：

```json
{
  "schema_version":"vllm.rwkv7-state-profiles.v1",
  "model_artifact":"<exact model artifact>",
  "model_revision":"<exact model revision>",
  "default_profile":"zero",
  "profiles":[
    {
      "id":"executor-local-observation",
      "format":"rwkv-peft-time-state.v1",
      "path":"executor-local-observation.pth",
      "sha256":"<state SHA256>"
    }
  ]
}
```

模型、模型 SHA、引擎 revision、input schema、full renderer SHA、parser SHA、tokenizer SHA、State SHA、manifest SHA 和 profile ID 是一个不可拆分的发布身份。Selector 还必须固定类别顺序、menu digest、feature protocol、Head file SHA 和 Head logical hash。

## 7. 当前运行位置

项目逻辑只在 WSL `UbuntuRecovered` 执行。本地与服务器项目路径：

```text
/home/chase/GitHub/RWKV-LH
```

登录服务器：

```bash
ssh rwkv-8222
cd /home/chase/GitHub/RWKV-LH
```

`rwkv-8222` 由本机 SSH 配置解析。IP、私钥和 API key 不写入仓库。

当前端口：

| 服务 | 服务器监听 | WSL 转发 | GPU |
|---|---:|---:|---:|
| 13.3B Executor/Auditor/Finalizer | `127.0.0.1:18234` | `127.0.0.1:29613` | 0 |
| 2.9B Selector | `127.0.0.1:18231` | `127.0.0.1:29621` | 3 |

隧道：

```bash
ssh -N \
  -L 127.0.0.1:29613:127.0.0.1:18234 \
  -L 127.0.0.1:29621:127.0.0.1:18231 \
  rwkv-8222
```

状态检查：

```bash
cd /home/chase/GitHub/RWKV-LH
uv run rwkv-lh-stack status
uv run rwkv-lh-runtime-smoke
```

当前运行模式是 `external`。13.3B 端点健康并声明完整 recurrent-state 能力。Selector 端点加载 Head v2，模型、Head、协议和 zero-State 身份一致。Head v2 的训练集只覆盖旧 canonical menu 和 `GoalFrontierStateV1`；当前三顺序与 `GoalFrontierStateV2` 对它属于域外输入，必须以固定真实消融结果判断收益，不能宣称已经训练兼容。

## 8. 推理引擎与服务启动

引擎锁定文件：

```text
rwkv_lh/inference/vllm-rwkv.lock.json
```

锁定身份：

```text
repository: https://github.com/rwkv-rs/vllm-rwkv.git
branch: rwkv-torch
revision: 67f0c5996c50dca0ad779da545cb491527de988f
build_profile: rwkv
```

13.3B 原生 State 服务的引擎目录与 Python：

```text
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python
```

Selector 使用同仓库、同 revision 的干净 checkout，以满足 Head 特征身份门禁；它复用上述 Python 环境：

```text
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50-selector-clean
```

准备引擎：

```bash
cd /home/chase/GitHub/RWKV-LH
uv run rwkv-lh-stack prepare
```

13.3B 模型：

```text
artifact: /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1
served model: rwkv7-g1j-13.3b-zero-state-capability-ctx16384
model SHA-256: 559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65
max model length: 16384
```

启动 13.3B 服务：

```bash
cd /home/chase/GitHub/RWKV-LH
CUDA_VISIBLE_DEVICES=0 \
data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/vllm serve \
  data/models/rwkv7-g1j-13.3b-vllm-v1 \
  --host 127.0.0.1 \
  --port 18234 \
  --tokenizer-mode rwkv \
  --trust-request-chat-template \
  --enable-auto-tool-choice \
  --tool-call-parser rwkv \
  --max-model-len 16384 \
  --served-model-name rwkv7-g1j-13.3b-zero-state-capability-ctx16384 \
  --gpu-memory-utilization 0.35 \
  --max-num-batched-tokens 32768 \
  --max-num-seqs 16 \
  --override-generation-config='{"temperature":0.1}'
```

2.9B 模型与协议：

```text
artifact: /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-2.9b-vllm-v1
model: rwkv7-g1j-2.9b-vllm-v1
model SHA-256: c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c
feature protocol: rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1
input protocol: rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1
```

Selector 必须使用以下唯一 Head v2 身份：

```text
Head: data/experiments/RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904/selector_intent/head/selector_head.json
file SHA-256: 49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a
logical hash: ef83fd7bf9340977f2ae16d95899690addf3446467ea43a138c61f0926c69bdd
```

启动入口：

```bash
cd /home/chase/GitHub/RWKV-LH
PYTHONPATH=/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50-selector-clean \
CUDA_VISIBLE_DEVICES=3 \
data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python \
  -m rwkv_lh.exact_tool_selector.network_service \
  --host 127.0.0.1 \
  --port 18231 \
  --engine-root /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50-selector-clean \
  --engine-revision 67f0c5996c50dca0ad779da545cb491527de988f \
  --engine-python /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python \
  --model-artifact /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-2.9b-vllm-v1 \
  --model-name rwkv7-g1j-2.9b-vllm-v1 \
  --model-sha256 c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c \
  --head /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904/selector_intent/head/selector_head.json \
  --head-sha256 49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a \
  --head-hash ef83fd7bf9340977f2ae16d95899690addf3446467ea43a138c61f0926c69bdd \
  --input-protocol rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1 \
  --profile-id zero \
  --profile-sha256 0000000000000000000000000000000000000000000000000000000000000000 \
  --state-dir /home/chase/GitHub/RWKV-LH/data/runtime/selector_state/head_v2_zero \
  --runtime-temp /home/chase/GitHub/RWKV-LH/temp/selector_runtime_head_v2
```

使用非零 Selector State 时，必须同时提供 profile manifest 及其 SHA。

## 9. 当前未解决的问题

| 环节 | 当前问题 | 归类 | 完成门禁 |
|---|---|---|---|
| Selector 决策 | Head v2 未训练三种 menu order 与 `GoalFrontierStateV2`；投票效果尚需真实固定集验证 | Head 泛化/输入分布问题，不能据此归因于 2.9B 基座 | 固定真实 holdout 与顺序敏感性指标达标 |
| Planner phase | 新 v3 patch 依赖 Planner 正确拆开观察、修改、执行和证据推导 | Planner 输入合同与语义验证已实现，真实计划质量待回归 | 固定 Planner 集的 phase、依赖和根目录全通过 |
| Executor 状态遵循 | 完整事实输入中会重复已完成对象，未服从 remaining state | 输入合同与 zero-State 能力共同待验证 | 固定完整链路集达标 |
| Executor JSON | `replace_text` 场景会生成 Python dict 形式 | 模型格式遵循问题 | canonical JSON 全通过 |
| Executor operation identity | 命令场景会把 schema/role 名写成 function | 模型显式 operation 遵循问题 | function 与 selected operation 全相等 |
| StateTune 输入 | 数据生成尚未与完整 serving transcript 共用同一个 renderer | 工程协议问题 | 每行 bytes 和 token IDs 双一致 |
| Executor State 路由 | 当前没有按四类 phase 选择 State profile | 按当前计划暂不实现 StateTune | 消融通过后再接入确定性映射 |
| 推理引擎发布 | 13.3B native-State 修改尚未封装成可复现的干净引擎 revision；Selector 只能使用干净基础 checkout | 工程发布问题；当前未发现 native State 行为缺陷 | 固定 native-State 引擎 commit，并验证 13.3B 与 Selector 特征身份 |

协议拒绝上限 12 是整条任务的自动熔断预算，不是 12 种错误。一个 selection 最多进行一次同工具参数修复；达到预算后记录 `run_blocked(reason="protocol_rejection_budget_exhausted")`。相同失败第 5 次、相同只读零进展第 3 次也会停止自动执行。

## 10. 训练返回后的接入顺序

1. 固定模型、数据、full renderer、parser、tokenizer、训练器、State 和 manifest 的路径与 SHA。
2. 验证每个训练 prompt 与线上 generation 前缀逐字节、逐 token 相等。
3. 对每个角色运行相同输入和采样的 zero-State/StateTune A-B；每个候选最多三次。
4. 对 Executor 四类 profile 先跑类内矩阵，再跑全部 23 operation 交叉矩阵。
5. 对 Selector 跑中文/英文、多工具、三种菜单顺序、高 `ABSTAIN` logit 屏蔽、停止、恢复和长轨迹 holdout。
6. 跑完整 Agent Ladder，检查首次偏离、工具分布、step 完成、停止率和最终任务完成率。
7. 全部达到预登记阈值后更新 `.env.local`，再用 `rwkv-lh-stack status` 验明完整发布身份。

验证命令：

```bash
cd /home/chase/GitHub/RWKV-LH
uv run pytest -q
uv run rwkv-lh-runtime-smoke
uv run rwkv-lh-e2e --suite all --validate-only
git diff --check
```
