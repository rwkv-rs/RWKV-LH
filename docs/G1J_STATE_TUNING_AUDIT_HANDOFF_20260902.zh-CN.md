# G1J 分环节 State Tuning 冻结实施协议

更新时间：2026-09-02（Asia/Shanghai）

本文是重新开始 G1J State Tuning 的唯一交接协议。旧的混合 State、旧 Selector 数据代号、旧分类 Head、旧 checkpoint、旧 profile、旧兼容运行和旧实验结论均不继承。本文只定义新的五环节方案；未写入本文的字段、文件、重试、转换、阈值和训练参数均不得临场增加。

## 0. 当前事实

```text
state_tuning_status: DATASETS_BUILT_HEAD_RETRAIN_REQUIRED
formal_dataset_count: 5
trained_stage_count: 0
selected_checkpoint_count: 0
selected_state_count: 0
runtime_state_profile_count: 0
release_state_count: 0
```

当前允许存在的模型资产只有 G1J 基础权重。基础权重不是 State Tuning 产物。

| 模型 | 基础权重 | SHA-256 | 固定结构 |
|---|---|---|---|
| G1J 2.9B | `/mnt/nas-model/g1j/rwkv7-g1j-2.9b-20260831-ctx16384.pth` | `966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239` | 32 layers, embedding 2560, vocab 65536, bf16 |
| G1J 13.3B | `/mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth` | `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65` | 61 layers, embedding 4096, vocab 65536, bf16 |

所有角色的初始 State 固定为 zero/unset：不加载 State 文件，不复用旧 State SHA。服务和运行身份使用 `profile_id=zero` 与 64 个零组成的 SHA。Selector 只在使用经过同分布持久轨迹训练并验证的 Head 时接受父 State；Executor 的每个新 action 从该角色初始 State 干净启动。

在本协议的 Gate 0、Gate 1 和 zero baseline 全部完成前，禁止创建训练输出目录，禁止启动 State Tuning，禁止选择 checkpoint，禁止更新默认 profile。

## 1. Goal 模式与终止语义

Goal 是类似 Codex“设定一个目标”的持续运行模式，不是模型、Planner、Controller、全局 State 或 StateTune 单元。

固定运行链路为：

```text
用户的 immutable objective
    ↓
Strong Planner 生成或修订 rolling plan
    ↓
当前唯一 frontier objective
    ↓
Selector / Intent 选择唯一 operation
    ↓
Executor-Args 只填写该 operation 的参数
    ↓
工具真实执行并提交 evidence
    ↓
Step Auditor 返回 continue 或 repair
    ↓
Strong Stage Checker 返回 advance 或 repair
    ↓
循环，直到 rolling plan evidence-complete
    ↓
Selector / Intent 选择 final_answer
    ↓
Finalizer 生成 final_answer.text
    ↓
Final Auditor 返回 ready_for_final 或 repair
    ↓
ready_for_final 才写入 COMPLETED
```

终止必须同时满足：

1. rolling plan 已 evidence-complete；
2. Selector 模型显式选择 `final_answer`；
3. Finalizer 模型生成合法且非空的 `final_answer.text`；
4. Final Auditor 返回 `ready_for_final`；
5. 运行时验证 candidate 与 evidence 绑定后写入 `COMPLETED`。

`interrupt`、`yield`、`failure`、`blocked`、`slice exhaustion`、协议拒绝和工具异常都不是完成。任何 `repair` 必须返回执行循环。Controller 只能调度、持久化、绑定 ID 和执行确定性 schema 校验，不能替模型选择 operation、补参数、生成 final text 或改写审核 verdict。

## 2. 五个独立 StateTune 单元

| 序号 | 数据集 ID | 模型 | State ID | 唯一输出 | State 生命周期 |
|---|---|---|---|---|---|
| 1 | `rwkv_lh_g1j_selector_intent_state_tuning_v1` | G1J 2.9B | `selector-intent-2p9-v1` | 一个 operation label | 每个 `(step_id, step_revision)` 从角色初始 State 开始，只在同一 scope 内继续 parent WKV |
| 2 | `rwkv_lh_g1j_executor_args_state_tuning_v1` | G1J 13.3B | `executor-args-v1` | 已选 operation 的完整 params | 每个已选 action 干净启动；失败时同一 handoff 最多一次修复 |
| 3 | `rwkv_lh_g1j_auditor_step_state_tuning_v1` | G1J 13.3B | `auditor-step-v1` | `continue` 或 `repair` | 每个 action audit 干净启动并在返回后丢弃 WKV |
| 4 | `rwkv_lh_g1j_finalizer_answer_state_tuning_v1` | G1J 13.3B | `finalizer-answer-v1` | `final_answer.text` | final selection 后独立干净启动 |
| 5 | `rwkv_lh_g1j_auditor_final_state_tuning_v1` | G1J 13.3B | `auditor-final-v1` | `ready_for_final` 或 `repair` | 每个 pre-final audit 干净启动并在返回后丢弃 WKV |

Strong Planner 和 Strong Stage Checker 不做 State Tuning。五个 State 之间禁止继承、拼接、相加、平均、路由或 merge WKV。一个训练文件只能属于表中一个数据集 ID。

Selector 的边界连续性不属于跨角色继承：每次只可读取同一个 `(step_id, step_revision)` 的上一个 Selector checkpoint，换 step、换 revision 或进入 Final 时必须从角色初始 State 重启；绝不读取 Executor、Auditor 或 Finalizer WKV。当前 Planner step、该 step 的最新 Harness 结果、最新审核反馈和当次 eligible 工具描述通过 `GoalFrontierStateV1` 放入现有 `stage_objective` 字符串，外层 `selector-intent.v1` JSON 字段与 Head 标签顺序保持不变。新的 `persistent-causal-sequences.v1` 训练轨迹必须以该 scope 为 sequence 边界，禁止把整个 run 拼成一条 Selector 序列。

第一轮固定只有这五个 State。不得为单个工具另建 State；若未来需要拆分，必须新建协议版本和独立预注册，不能修改本轮文件。

## 3. Gate 0：先完成运行时角色拆分

当前代码还不满足直接训练条件，必须先完成以下四项结构整改：

1. 当前 action lane 仍可能让 Executor session 处理 `final_answer`。必须把 Finalizer 变成独立 session、独立 bootstrap、独立 State profile 和独立 attestation。
2. 当前 Step Audit 与 Final Audit 可复用同一个 auditor session 配置。必须按 boundary 选择不同 profile，且两个 profile 的 ID、SHA、加载记录分别持久化。
3. Selector 的生产输入、标签后缀、分类 Head 和 State 的身份必须重新冻结；不得加载旧 Head 或旧数据代号对应的 feature/head 产物。
4. 五个生产 renderer 必须从运行路径提取为可直接导入的唯一函数，数据生成器不得复制 prompt 模板。

Gate 0 固定新增以下模块，不接受其他命名：

```text
rwkv_lh/goal_state_protocols/__init__.py
rwkv_lh/goal_state_protocols/selector_intent.py
rwkv_lh/goal_state_protocols/executor_args.py
rwkv_lh/goal_state_protocols/auditor_step.py
rwkv_lh/goal_state_protocols/finalizer_answer.py
rwkv_lh/goal_state_protocols/auditor_final.py
```

每个模块必须导出且只由生产和数据生成共同调用：

```text
INPUT_SCHEMA_VERSION
OUTPUT_SCHEMA_VERSION
render_prompt(source) -> str
render_target(source) -> str
parse_target(target) -> typed value
validate_source(source) -> None
```

五个模块的 schema version 固定以 `rwkv-lh.g1j-per-stage-state-tuning.<stage>.v1` 命名。历史协议序号不得出现在这些 schema version、数据集 ID、State ID、Head ID 或实验 ID 中。

Gate 0 必须增加并通过以下架构测试：

- Executor State 不能进入 Finalizer；
- Step Auditor State 不能进入 Final Auditor；
- Selector State 不能进入 Executor；
- 任意角色都不能接收另一个角色的 State SHA；
- non-final operation 永远不能写 terminal status；
- Selector 选择 `final_answer` 后只能进入 Finalizer；
- Finalizer 不能直接写 `COMPLETED`；
- Final Auditor 的 `repair` 必须回到 Goal 循环；
- interrupt/yield/failure 后保持可恢复且非 terminal；
- 服务 attestation 中的模型、Head、State 和协议 SHA 与请求逐项一致。

Gate 0 未通过时，后续生成器必须以非零退出码停止。

## 4. 数据目录与文件合同

每个环节使用独立目录：

```text
data/datasets/<dataset_id>/
├── README.md
├── manifest.json
├── split_registry.json
├── source_registry.jsonl
├── sample_index.jsonl
├── verification_records.jsonl
├── tokenizer_records.jsonl
├── rwkv_state_tuning.train.requires_target_suffix.jsonl
├── rwkv_state_tuning.dev.requires_target_suffix.jsonl
├── generation_validation.json
├── leakage_audit.json
└── tokenizer_target_suffix_audit.json
```

sealed 数据固定放在：

```text
data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_<YYYYMMDD>/<stage>/sealed_test/
├── source_registry.jsonl
├── sample_index.jsonl
├── verification_records.jsonl
├── tokenizer_records.jsonl
└── rwkv_state_tuning.sealed.requires_target_suffix.jsonl
```

训练器只能读取 `rwkv_state_tuning.train.requires_target_suffix.jsonl`。Dev evaluator 只能读取 dev 文件。训练、Dev 选择和生成器都不能读取 sealed 目录。

### 4.1 唯一训练行格式

项目现有 RWKV-PEFT `target_suffix` loader 的正式格式固定为三个字段：

```json
{"prompt":"<production renderer 返回的完整 UTF-8 前缀>","target":"<production target renderer 返回的完整 UTF-8 后缀>","text":"<prompt 与 target 的字节级直接拼接>"}
```

字段集合必须严格等于 `prompt,target,text`，序列化顺序也固定为 `prompt,target,text`。训练行禁止加入 sample ID、split、标签副本、验收说明、提示答案、自然语言 rubric、loss 配置或其他元数据。

固定序列化参数：

```python
json.dumps(row, ensure_ascii=False, sort_keys=False, separators=(",", ":")) + "\n"
```

固定不变量：

```text
set(row) == {"prompt", "target", "text"}
row["prompt"] != ""
row["target"] != ""
row["text"].encode("utf-8") == row["prompt"].encode("utf-8") + row["target"].encode("utf-8")
```

不得使用 `question/answer`，不得把 sidecar 字段复制到训练行，不得在 staging 时改写 prompt 或 target。训练 loader 不兼容时应修改并测试 loader；禁止生成第二种数据格式绕过本合同。

### 4.2 `source_registry.jsonl`

此文件保存生成依据，不进入训练。每行公共字段和顺序固定为：

| 字段 | 类型 | 规则 |
|---|---|---|
| `schema_version` | string | 对应环节 source schema v1 |
| `source_id` | string | 全局唯一，非空 |
| `stage` | enum | 五个 State ID 之一 |
| `project_family` | string | 整个项目族的稳定 ID |
| `source_kind` | enum | `production_trace`、`executable_fixture`、`deterministic_counterfactual`、`human_double_review` |
| `source_path` | string | 项目根相对路径 |
| `source_sha256` | string | 64 位小写十六进制 |
| `record_locator` | string | JSON pointer、JSONL 行号或 trace event ID |
| `parent_source_ids` | array[string] | 去重并排序 |
| `payload` | object | 第 6 节对应环节的固定 payload |

字段集合必须与表一致；`payload` 的字段集合也必须与第 6 节一致。

### 4.3 `sample_index.jsonl`

每行字段和顺序固定为：

```text
schema_version, dataset_id, sample_id, stage, split, project_family,
source_id, input_schema_version, output_schema_version,
renderer_sha256, parser_sha256, verifier_id, verifier_sha256,
prompt_sha256, target_sha256, text_sha256,
prompt_tokens, target_tokens, total_tokens_with_bos
```

所有 string 非空；所有 SHA 为 64 位小写十六进制；三个 token 字段为非负整数；`total_tokens_with_bos = 1 + prompt_tokens + target_tokens`。字段集合严格相等，禁止扩展。

### 4.4 `verification_records.jsonl`

每行字段和顺序固定为：

```text
schema_version, sample_id, source_id, parser_passed, schema_passed,
semantic_passed, role_boundary_passed, execution_passed,
evidence_binding_passed, leakage_passed, family_split_passed
```

最后八个结果字段均为 boolean。进入训练或 Dev 的每一行必须全部为 `true`。某个 verifier 不适用时，生成器必须调用该环节注册的恒真验证函数并在 manifest 中固定其 SHA，不能省略字段或写 null。

### 4.5 `tokenizer_records.jsonl`

每行字段和顺序固定为：

```text
schema_version, sample_id, tokenizer_sha256, bos_token_id,
context_length, prompt_tokens, target_tokens, total_tokens_with_bos,
first_target_predicted_from_last_prompt_token, no_truncation,
serving_token_ids_match_training
```

`bos_token_id` 固定为 `0`，`context_length` 固定为 `4096`，最后三个字段必须为 `true`。

### 4.6 `manifest.json`

顶层字段和顺序固定为：

```text
schema_version, dataset_id, dataset_version, stage, purpose,
source, protocol, serialization, split, training, counts, files, status
```

嵌套字段固定为：

```text
source = {
  source_registry_sha256,
  generator_path,
  generator_sha256,
  verifier_paths,
  verifier_sha256
}

protocol = {
  input_schema_version,
  output_schema_version,
  renderer_path,
  renderer_sha256,
  parser_path,
  parser_sha256,
  operation_registry_sha256,
  tokenizer_sha256
}

serialization = {
  encoding,
  ensure_ascii,
  sort_keys,
  separators,
  line_ending,
  training_fields
}

split = {
  algorithm,
  salt,
  train_buckets,
  dev_buckets,
  sealed_buckets,
  registry_sha256
}

training = {
  loss_mask,
  jsonl_bos_token_id,
  context_length,
  data_shuffle
}

counts = {
  source,
  train,
  dev,
  sealed,
  rejected
}

files = {
  <固定目录中每个文件名>: {sha256, bytes, lines}
}
```

值固定为：`schema_version="rwkv-lh.g1j-per-stage-state-dataset-manifest.v1"`、`dataset_version="1"`、`encoding="UTF-8"`、`ensure_ascii=false`、`sort_keys=false`、`separators=[",",":"]`、`line_ending="LF"`、`training_fields=["prompt","target","text"]`、`loss_mask="target_suffix"`、`jsonl_bos_token_id=0`、`context_length=4096`、`data_shuffle=0`、`rejected=0`、`status="frozen"`。`files` 必须完整覆盖第 4 节目录中除 `manifest.json` 自身以外的文件，不能出现未登记文件；`manifest.json` 的 SHA-256 只登记到对应实验目录的 `DATA_REGISTRY.json`，禁止在自身内部登记自身哈希。

### 4.7 `split_registry.json` 与三个汇总报告

`split_registry.json` 顶层字段固定为：

```text
schema_version, algorithm, salt, train_buckets, dev_buckets,
sealed_buckets, family_assignments, cross_split_family_overlap
```

`family_assignments` 是以 project family ID 为 key、`train|dev|sealed` 为 value 的按 key 排序 object；`cross_split_family_overlap=[]`。

`generation_validation.json` 顶层字段固定为：

```text
schema_version, dataset_id, source_rows, generated_rows,
rejected_rows, parser_pass_rate, schema_pass_rate,
semantic_pass_rate, role_boundary_pass_rate, execution_pass_rate,
evidence_binding_pass_rate, family_split_pass_rate, passed
```

`leakage_audit.json` 顶层字段固定为：

```text
schema_version, dataset_id, prompt_target_leak_count,
label_leak_count, mutation_identity_leak_count,
cross_split_parent_count, duplicate_sample_count,
maximum_cross_split_similarity, similarity_algorithm,
similarity_threshold, passed
```

`tokenizer_target_suffix_audit.json` 顶层字段固定为：

```text
schema_version, dataset_id, rows, bos_token_id, context_length,
maximum_total_tokens_with_bos, truncated_rows,
first_target_alignment_rate, supervised_prompt_tokens,
supervised_target_tokens, serving_training_token_match_rate, passed
```

三个汇总报告的 `passed` 都必须为 `true`；`rejected_rows`、全部 leak/overlap/duplicate count、`truncated_rows` 和 `supervised_prompt_tokens` 必须为 `0`；全部 pass/match/alignment rate 必须为 `1.0`。

## 5. 固定切分与生成算法

先按完整 `project_family` 切分，再生成同族变体。固定 salt 为：

```text
rwkv-lh-g1j-per-stage-state-tuning-v1-family-split
```

固定算法为：

```python
bucket = int(sha256((salt + "\0" + project_family).encode("utf-8")).hexdigest()[:8], 16) % 100
split = "train" if bucket < 80 else "dev" if bucket < 90 else "sealed"
```

同一个 project family、source record、trajectory 和 counterfactual parent 必须处于同一 split。输出按 `sample_id` 的 UTF-8 字节升序排列。生成器不得随机切分、随机丢行或按运行结果改 split。

样本数不由复制模板凑整。冻结后的 `source_registry.jsonl` 与确定性变换注册表共同决定唯一行数；任一来源行生成失败时整次生成失败，不允许跳过。Manifest 写入最终 train/dev/sealed 行数和全部文件 SHA 后，行数即成为该数据集版本的固定值。

数据来源优先级固定为：

```text
生产一致真实 trace
> 可执行 fixture
> 同 split 的确定性 counterfactual
> 人工双审记录
```

Strong Model 可以提出候选，但不能成为 label authority。RWKV 原始错误输出只能作为 failure evidence，不能作为训练 target。所有 target 必须由生产合同、真实执行、确定性 verifier 或两名审阅者共同签署的事实生成。

相似度算法固定为 `utf8-byte-5gram-cosine.v1`。只对第 6 节列出的 task-dependent source 字段做原始 UTF-8 byte 5-gram cosine，不含公共 renderer 文本和 target。Train/dev、train/sealed、dev/sealed 的最大跨 split 相似度都必须小于 `0.95`。

## 6. 五个环节的唯一 source payload 与 target

### 6.1 Selector / Intent

`payload` 字段集合和顺序固定为：

```text
stage_objective, stage_role, progress, eligible_labels,
selected_operation, selection_authority, selection_verifier_id
```

类型固定为：

- `stage_objective`: 非空 string，只包含当前 frontier；
- `stage_role`: 非空 string；
- `progress`: object，字段严格为 `completed_stage_count,action_index,succeeded_operations,failed_operations,protocol_rejection_count`；
- `eligible_labels`: array[string]，按生产 operation registry 顺序排列；
- `selected_operation`: string，必须是 `eligible_labels` 成员；
- `selection_authority`: enum `planner_contract`、`executed_fixture`、`human_double_review`；
- `selection_verifier_id`: 非空 string。

Task-dependent similarity fields 固定为 `stage_objective,stage_role,progress,eligible_labels`。

生成过程固定为：

1. 从真实 Goal trace 的 Selector boundary 或可执行 fixture 抽取当前 frontier；
2. 通过运行时 operation policy 计算有序 `eligible_labels`；
3. 由工具职责和 fixture 计算唯一 `selected_operation`；
4. 调用 `selector_intent.render_prompt(payload)`；
5. 调用 `selector_intent.render_target(payload)`；
6. `parse_target` 必须只得到一个 operation label；
7. 使用同一冻结分类 Head 对 zero State 和 tuned State 做逐样本配对评估。

`selector_intent.render_target(payload)` 的返回值固定为下面两个字面片段的直接拼接：

```python
"\nSelectorIntentV1: " + payload["selected_operation"]
```

Target 不含参数、函数调用、final text、理由或审核结论。在线 Selector 仍由分类 Head 读取 hidden feature；State Tuning 期间 Head 的文件和 SHA 保持不变。更换 Head 会使整轮实验失效。

完成态样本的 `eligible_labels` 必须严格等于 `["final_answer"]`。非完成态不得选择 `final_answer`。`ABSTAIN` 只用于运行时确实无法唯一选择 operation 的边界，不能替代缺失标签。

### 6.2 Executor-Args

`payload` 字段集合和顺序固定为：

```text
current_requirement, selected_operation, selected_tool_contract,
committed_fact_refs, executor_history, command,
fixture_id, execution_verifier_id
```

类型固定为：

- `current_requirement`: 非空 string，字节等于当前 frontier objective；
- `selected_operation`: 非空 string，不能是 `final_answer` 或 `ABSTAIN`；
- `selected_tool_contract`: 生产 registry 中该 operation 的完整 object；
- `committed_fact_refs`: array[string]，去重并排序；
- `executor_history`: array[object]，只含该 Executor lane 已提交事件；
- `command`: object，字段严格为 `function,params`；
- `fixture_id`: 非空 string；
- `execution_verifier_id`: 非空 string。

Task-dependent similarity fields 固定为 `current_requirement,selected_operation,selected_tool_contract,committed_fact_refs`。

生成过程固定为：

1. 从当前 frontier 和金标 operation 建立隔离 workspace fixture；
2. 从生产 registry 读取完整 tool contract；
3. 由 fixture 生成完整 params；
4. 在隔离 fixture 中真实执行 command；
5. verifier 证明 command 满足当前 frontier 且没有推进其他 step；
6. 调用 `executor_args.render_prompt(payload)`；
7. 调用 `executor_args.render_target(payload)`；
8. target 必须通过生产 command parser 和 operation schema。

Target 固定为 `ModelCommand(selected_operation, params).canonical` 返回的一行 canonical direct-call JSON。所有参数必须显式出现；不得依赖 Controller 补默认值。Executor 数据不能含 operation 选择、下一 frontier、审核 verdict 或 user-facing final text。

### 6.3 Step Auditor

`payload` 字段集合和顺序固定为：

```text
boundary, active_step, available_evidence_refs, evidence_records,
decision, completion_verifier_id
```

类型固定为：

- `boundary`: enum `observation_complete`、`mutation_transaction_complete`、`tool_failure`、`stagnation`；
- `active_step`: object，字段来自冻结 Goal plan step schema；
- `available_evidence_refs`: array[string]，去重并排序；
- `evidence_records`: array[object]，每条由生产 evidence projector 生成；
- `decision`: object，字段严格为 `verdict,step_id,step_complete,evidence_refs,gaps,reason`；
- `completion_verifier_id`: 非空 string。

Task-dependent similarity fields 固定为 `boundary,active_step,evidence_records`。

`decision.verdict` 只允许 `continue` 或 `repair`：

- `continue`: `step_id` 等于 active step ID，`step_complete=true`，`evidence_refs` 非空，`gaps=[]`；
- `repair`: `step_id` 等于 active step ID，`step_complete=false`，`gaps` 非空；
- 两类 decision 的 evidence refs 都必须是 `available_evidence_refs` 的子集。

生成过程固定为：收集真实 action evidence，按 mutation registry 的 ID 顺序构造缺失、冲突、失败、截断和版本错误 counterfactual；每次 mutation 后重新执行 completion verifier；再调用 `auditor_step.render_prompt` 和 `auditor_step.render_target`。Target 是 `audit_decision` 的 canonical direct-call JSON。

Step Auditor 数据禁止 `ready_for_final`、final candidate、其他 plan step 和 user-facing answer。

### 6.4 Finalizer

`payload` 字段集合和顺序固定为：

```text
immutable_goal, completed_steps, committed_facts, evidence_records,
format_contract, final_text, fact_verifier_id
```

类型固定为：

- `immutable_goal`: 非空 string；
- `completed_steps`: 非空 array[object]，每个 step 有已提交 evidence refs；
- `committed_facts`: 非空 array[object]，每条字段严格为 `fact_id,value,evidence_refs`；
- `evidence_records`: 非空 array[object]；
- `format_contract`: object，字段严格为 `format_id,language,required_sections`；
- `final_text`: 非空 string；
- `fact_verifier_id`: 非空 string。

Task-dependent similarity fields 固定为 `immutable_goal,completed_steps,committed_facts,format_contract`。

生成过程固定为：从 evidence-complete Goal fixture 建立 committed fact registry；由人工双审或确定性 formatter 生成 `final_text`；fact verifier 检查每个事实、数值、路径、失败说明和格式；再调用 `finalizer_answer.render_prompt` 和 `finalizer_answer.render_target`。

Target 固定为 `ModelCommand("final_answer", {"text": final_text}).canonical`。Finalizer 数据不能含未提交事实、未完成计划、审核 verdict 或 Controller completion 事件。Finalizer 只生成 candidate，没有终止权限。

### 6.5 Final Auditor

`payload` 字段集合和顺序固定为：

```text
immutable_goal, completed_steps, committed_facts,
available_evidence_refs, evidence_records, final_candidate,
decision, final_verifier_id
```

类型固定为：

- `immutable_goal`: 非空 string；
- `completed_steps`: 非空 array[object]；
- `committed_facts`: 非空 array[object]；
- `available_evidence_refs`: 非空 array[string]，去重并排序；
- `evidence_records`: 非空 array[object]；
- `final_candidate`: object，字段严格为 `function,params`，function 固定为 `final_answer`，params 只含非空 `text`；
- `decision`: object，字段严格为 `verdict,step_id,step_complete,evidence_refs,gaps,reason`；
- `final_verifier_id`: 非空 string。

Task-dependent similarity fields 固定为 `immutable_goal,completed_steps,committed_facts,final_candidate`。

`decision.verdict` 只允许 `ready_for_final` 或 `repair`：

- `ready_for_final`: `step_id=""`、`step_complete=false`、`gaps=[]`，所有 required facts 均被 candidate 忠实覆盖；
- `repair`: `step_id=""`、`step_complete=false`、`gaps` 非空；
- evidence refs 必须是 `available_evidence_refs` 的子集。

生成过程固定为：从合法 final candidate 开始，按 mutation registry 的 ID 顺序分别执行删除事实、替换数值、替换路径、加入无依据事实、绑定失败 evidence、破坏格式和制造计划未完成；每次 mutation 后重新运行 final verifier；再调用 `auditor_final.render_prompt` 和 `auditor_final.render_target`。Target 是 `audit_decision` 的 canonical direct-call JSON。

Final Auditor 数据禁止 `continue`，禁止让 `step_complete=true`，禁止向模型披露 mutation ID。

## 7. 生成器与校验命令

必须实现且只使用以下五个生成器：

```text
scripts/generate_g1j_selector_intent_state_tuning_v1.py
scripts/generate_g1j_executor_args_state_tuning_v1.py
scripts/generate_g1j_auditor_step_state_tuning_v1.py
scripts/generate_g1j_finalizer_answer_state_tuning_v1.py
scripts/generate_g1j_auditor_final_state_tuning_v1.py
```

每个脚本只接受两个模式：

```text
--build --source-registry <absolute-path> --output <absolute-path>
--validate-existing --output <absolute-path>
```

`--build` 只能写一个全新的空目录；目录已存在即失败。`--validate-existing` 只读，不重写任何文件。所有命令只在 WSL `UbuntuRecovered` 中从项目根执行；临时验证脚本放在 `/home/chase/GitHub/RWKV-LH/temp/` 并使用绝对路径。

每个生成器必须执行以下固定检查，任一失败即非零退出：

1. source schema 与字段集合完全相等；
2. project family split 算法和 salt 相等；
3. production renderer、parser、registry、verifier SHA 相等；
4. 训练行字段集合严格等于 `prompt,target,text`；
5. prompt、target 非空且 text 为字节级拼接；
6. target 可被生产 parser 严格解析；
7. target 通过对应 semantic verifier；
8. 无角色越界字段；
9. 无 target 或 label 泄漏到 prompt；
10. 无跨 split family、source、trajectory 或 counterfactual parent；
11. 跨 split 最大 byte 5-gram cosine 小于 `0.95`；
12. 训练 tokenizer 与服务 tokenizer token IDs 完全相等；
13. BOS 为 0；
14. 总 token 数不超过 4096；
15. 第一枚 target token 由最后一枚 prompt token 预测；
16. 无截断、无静默跳行、无自动 repair、无格式转换；
17. 文件行数、字节数和 SHA 与 manifest 相等。

## 8. 固定训练参数

五个环节共同参数：

```text
peft: state
op: fla
data_type: jsonl
loss_mask: target_suffix
jsonl_bos_token_id: 0
ctx_len: 4096
micro_bsz: 1
accumulate_grad_batches: 1
epoch_count: 1
epoch_steps: manifest.train_rows
data_shuffle: 0
vocab_size: 65536
precision: bf16
strategy: deepspeed_stage_1
grad_cp: 1
num_workers: 2
lr_schedule: cos
beta1: 0.9
beta2: 0.99
adam_eps: 1e-8
state_init: none
require_state_init: 0
```

分环节参数：

| State | `n_layer` | `n_embd` | `lr_init` | `lr_final` | seed |
|---|---:|---:|---:|---:|---:|
| `selector-intent-2p9-v1` | 32 | 2560 | `1e-5` | `1e-6` | 26090201 |
| `executor-args-v1` | 61 | 4096 | `3e-6` | `3e-7` | 26090202 |
| `auditor-step-v1` | 61 | 4096 | `3e-6` | `3e-7` | 26090203 |
| `finalizer-answer-v1` | 61 | 4096 | `3e-6` | `3e-7` | 26090204 |
| `auditor-final-v1` | 61 | 4096 | `3e-6` | `3e-7` | 26090205 |

`warmup_steps = max(20, floor(manifest.train_rows * 0.02))`。保存点固定为训练行数的 25%、50%、75%、100%，各位置使用向下取整，重复位置去重。不得追加训练、继承旧 State、改 seed、改学习率或根据中途结果增加 checkpoint。

训练前远端 preflight 必须校验基础权重 SHA、训练器全部源码 SHA、数据 SHA、tokenizer SHA、GPU UUID、State tensor key/shape、空输出目录和上述全部参数。Preflight 失败不得启动训练。

## 9. Zero baseline、选择与发布门禁

顺序固定为：

1. Gate 0 架构整改；
2. 五个 source registry 冻结；
3. 五个生成器与 evaluator 实现；
4. 五套数据一次生成并 content-address；
5. 五个 zero-State Dev baseline；
6. 全 zero 的固定 Agent Ladder；
7. 逐环节训练；
8. 单变量 Dev 选择；
9. 候选与代码 SHA 冻结；
10. 每个环节 sealed 只打开一次；
11. A-I 组合消融；
12. 固定 Agent Ladder release run；
13. 最后才更新默认 profile。

若某环节 zero State 已通过该环节全部门禁，该环节保持 zero，不训练。

单变量消融固定为：

| Run | Selector | Executor | Step Auditor | Finalizer | Final Auditor |
|---|---|---|---|---|---|
| A | zero | zero | zero | zero | zero |
| B | tuned | zero | zero | zero | zero |
| C | zero | tuned | zero | zero | zero |
| D | zero | zero | tuned | zero | zero |
| E | zero | zero | zero | tuned | zero |
| F | zero | zero | zero | zero | tuned |
| G | tuned | tuned | zero | zero | zero |
| H | tuned | tuned | tuned | zero | zero |
| I | tuned | tuned | tuned | tuned | tuned |

所有 run 使用相同样本顺序、采样参数、服务身份、Head、parser、verifier 和阈值；只允许表中 State 变化。

共同硬门禁：

```text
parser/schema validity = 1.0
role-boundary violations = 0
invented evidence = 0
controller-generated semantic fields = 0
hidden retry = 0
silent sample skip = 0
empty metric denominator = 0
zero-correct critical row regressions = 0
```

分环节接受条件：

- Selector：`macro-F1 >= zero macro-F1 + 0.02`；每类 recall 不低于 zero；提前 `final_answer` 为 `0`；完成态漏选为 `0`。
- Executor-Args：operation 保持率 `1.0`；`semantic execution pass rate >= zero + 0.02`；workflow 越界为 `0`。
- Step Auditor：false-continue 为 `0`；active/final boundary 混淆为 `0`；`macro-F1 >= zero macro-F1 + 0.02`。
- Finalizer：required-fact recall 为 `1.0`；unsupported fact rate 为 `0`；格式通过率不低于 zero。
- Final Auditor：false-ready 为 `0`；计划未完成、事实缺失、冲突 evidence 三类 recall 均为 `1.0`；macro-F1 不低于 zero。

Sealed 任一硬门禁失败，该环节不发布，也不得用 sealed 错误回填本版本 train。组合 run I 必须通过全部硬门禁和固定 Agent Ladder；否则逐边界定位最早回退，不允许通过 retry、parser repair 或 Controller 特判补偿。

## 10. 留档与停止条件

正式实验根固定为：

```text
data/experiments/G1J_PER_STAGE_STATE_TUNING_V1_<YYYYMMDD>/
```

每个生成、zero、训练、Dev、sealed 和组合 run 必须保存：

```text
RUN_PROTOCOL.json
SOURCE_MANIFEST.json
SERVICE_IDENTITY.json
REQUESTS.jsonl
RAW_GENERATIONS.jsonl
DERIVED_EVALUATION.jsonl
SUMMARY.json
STATE_ATTESTATION.jsonl
```

Raw generation 必须在解析前持久化；derived record 只引用 raw SHA。所有模型、基础权重、Head、State、数据、renderer、parser、verifier、tokenizer、训练器和服务配置均记录绝对路径与 SHA。失败和排除必须显式记录，不能静默跳过。

出现以下任一情况立即停止：

- 生产协议或 renderer SHA 与数据 manifest 不一致；
- 发现旧 Head、旧 State、旧 checkpoint 或父 State 被加载；
- 五个角色中任意两者共享 State profile；
- 训练行出现三个正式字段以外的字段；
- target、标签、mutation 身份或 verifier 结论进入 prompt；
- family 跨 split 或 sealed 在冻结前被读取；
- tokenizer、BOS、context 或 target suffix 对齐不一致；
- evaluator 跳样本、空分母或运行后改变口径；
- tuned 收益依赖更换 Head、prompt、parser、retry、repair 或 postprocess；
- 非 `final_answer` 路径写入 terminal；
- Finalizer 或 Controller 获得终止权限；
- Final Auditor false-ready；
- loss 改善但冻结能力指标不改善。

在所有发布条件满足前，五个 runtime State 配置保持 zero identity，状态保持 `DATASETS_BUILT_HEAD_RETRAIN_REQUIRED` 或对应环节的实验中状态。State 二进制不得提交 Git。
