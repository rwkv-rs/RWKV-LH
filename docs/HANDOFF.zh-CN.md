# RWKV-LH 当前交接

更新时间：2026-09-04（Asia/Shanghai）

本文是当前人工交接入口，覆盖运行位置、推理引擎、完整控制链、已知缺陷和 StateTune 格式边界。`AGENTS.md` 单独保存工作规范；历史设计和实验过程从 Git 历史或归档分支读取，不再作为当前实现依据。

## 1. 当前结论

项目的确定性控制链已经收口为 `rwkv-stateful-goal-loop.v3`，但当前不能作为可靠 Agent 发布，也不应立即开始 StateTune：

1. 远端 13.3B Executor 服务健康，native recurrent State 能力可用，尚未发现推理引擎传输缺陷。
2. 远端 2.9B Selector 服务仍加载旧 Head；它与本地期望身份不一致，运行时会按设计 fail closed。
3. 新 Head v2 在合成 dev 为 1.0，但真实中文多工具 frontier 首次选择 `ABSTAIN`，不能发布。
4. 13.3B zero-State 在短输入上表现明显更好，但生产完整事实输入仍会重复已经完成的路径。
5. 现有五套 G1J StateTune v1 数据没有证明与实际 serving transcript 字节一致，其中三套的 renderer SHA 已过期。训练前必须先修复这一门禁。

这里没有证据证明“RWKV 架构能力不行”。当前证据只能说明具体 Head、输入合同和 zero-State 角色配置还不够。

## 2. 机器、目录和端口

项目命令只在 WSL `UbuntuRecovered` 中执行。本地和远端项目根目录当前相同：

```text
/home/chase/GitHub/RWKV-LH
```

进入远端服务器：

```bash
ssh rwkv-8222
cd /home/chase/GitHub/RWKV-LH
```

`rwkv-8222` 由本机 `~/.ssh/config` 解析。不要把 IP、私钥或 API key 写入仓库。

当前端口和 GPU：

| 角色 | 远端监听 | 本地转发 | GPU | 状态 |
|---|---:|---:|---:|---|
| 13.3B Executor | `127.0.0.1:18234` | `127.0.0.1:29613` | 0 | 健康 |
| 2.9B Selector | `127.0.0.1:18231` | `127.0.0.1:29621` | 3 | 进程存在，但 Head 身份过期 |

双端口临时隧道：

```bash
ssh -N \
  -L 127.0.0.1:29613:127.0.0.1:18234 \
  -L 127.0.0.1:29621:127.0.0.1:18231 \
  rwkv-8222
```

检查本地运行身份：

```bash
cd /home/chase/GitHub/RWKV-LH
uv run rwkv-lh-stack status
```

当前 `RWKV_RUNTIME_MODE=external`。管理器可以检查或采用已经存在的服务/隧道，但不会凭空修复远端 Selector Head。Selector 身份不匹配时不要绕过检查。

## 3. 推理引擎与启动

锁定文件：

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

本地和远端当前引擎目录：

```text
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50
```

引擎 Python：

```text
/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python
```

准备锁定引擎：

```bash
cd /home/chase/GitHub/RWKV-LH
uv run rwkv-lh-stack prepare
```

### 3.1 Executor

当前模型目录：

```text
/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1
```

当前服务身份：

```text
served model: rwkv7-g1j-13.3b-zero-state-capability-ctx16384
model SHA-256: 559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65
state: zero
max model length: 16384
```

远端前台启动命令与当前进程参数一致：

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

不要同时在相同端口启动第二个服务。正式常驻方式应放进服务器自己的进程管理器；当前项目 `.env.local` 没有登记远端 systemd unit，因此 `rwkv-lh-stack` 只负责连接和验明身份。

### 3.2 Selector

当前模型目录：

```text
/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-2.9b-vllm-v1
```

固定模型身份：

```text
model: rwkv7-g1j-2.9b-vllm-v1
model SHA-256: c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c
feature protocol: rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1
input protocol: rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1
```

本地配置期望的 Head v2：

```text
path: data/experiments/RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904/selector_intent/head/selector_head.json
file SHA-256: 49538a32162941a256f1075ea465b52bda5ddc07e9e4001f94268f7c4368892a
logical hash: ef83fd7bf9340977f2ae16d95899690addf3446467ea43a138c61f0926c69bdd
```

这个 Head v2 已被真实 canary 判定不可发布；远端当前服务加载的又是更旧的 Head。因此现在不要启动或切换成任何一个作为产品默认值。新 Head 通过固定真实 holdout 后，使用以下入口并替换三个 Head 占位值：

```bash
cd /home/chase/GitHub/RWKV-LH
CUDA_VISIBLE_DEVICES=3 \
data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python \
  -m rwkv_lh.exact_tool_selector.network_service \
  --host 127.0.0.1 \
  --port 18231 \
  --engine-root /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50 \
  --engine-revision 67f0c5996c50dca0ad779da545cb491527de988f \
  --engine-python /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python \
  --model-artifact /home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-2.9b-vllm-v1 \
  --model-name rwkv7-g1j-2.9b-vllm-v1 \
  --model-sha256 c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c \
  --head '<validated-head.json>' \
  --head-sha256 '<validated-file-sha256>' \
  --head-hash '<validated-logical-hash>' \
  --input-protocol rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1 \
  --profile-id zero \
  --profile-sha256 0000000000000000000000000000000000000000000000000000000000000000 \
  --state-dir /home/chase/GitHub/RWKV-LH/data/runtime/selector_state \
  --runtime-temp /home/chase/GitHub/RWKV-LH/temp/selector_runtime
```

如果使用非零 Selector State，还必须同时传 `--profile-manifest` 和正确的 manifest SHA；不能只改 profile ID。

## 4. 完整控制链和职责

```text
Immutable Goal / Causal Ledger
  -> Strong Planner: 只拆 stage/step 和声明证据要求
  -> 2.9B Selector: 当前 frontier 只选一个 operation
  -> 13.3B Executor: 只为已选 operation 填完整参数
  -> Harness: 授权、执行、保存结果和副作用
  -> Controller Mechanical Evidence Gate: 机械验证 read/write roots
  -> Step Auditor: 机械条件满足后判断语义证据
  -> Evidence Kernel: 复核引用、revision、operation 和完成权限
  -> Strong Stage Checker: 整个 stage 的 advance/repair
  -> Finalizer: 只写 final candidate
  -> Final Auditor: 唯一终局审核
```

Planner 中“将读取”“将验证”“需要读取”的文本不是证据，也不能使 step 完成。`read_roots`、`write_roots` 和 `success_evidence` 都只是要求。完成顺序固定为：成功 Action 事实 -> Controller 机械覆盖 -> Step Auditor 语义判断 -> Evidence Kernel。

## 5. 全局状态和局部状态

全局权威是 append-only causal ledger，保存 immutable goal、rolling plan、step revision、Action、Artifact、audit boundary、机械 gap、协议拒绝以及模型/Head/State/工具身份。WKV、模型文本和 Planner 声明都不能直接改写完成事实。

每个小任务的局部状态是 `(step_id, step_revision)`，只投影该 revision 的 Action、直接依赖步骤已接受的 evidence，以及最新 mechanical/semantic gap。

一次循环的状态变化：

1. Planner 创建或修订当前 step；revision 改变会形成新局部边界。
2. Selector 在同一 `(step_id, step_revision)` 内继承自己的上一份 `_next_state`，选择一个 operation；跨 step、revision、Final 或角色时重置。
3. Executor 为每个新 selected action 从该角色的初始 State 干净启动，不继承上一个 action 的 WKV；它接收局部事实和唯一工具 schema，只填写参数。
4. Harness 执行后把参数、结果、错误、副作用和 Artifact 写入全局账本。
5. Controller 重新计算局部 coverage。缺口仍在则反馈给下一次 Selector/Executor；覆盖完整才打开 Step Auditor。
6. Auditor、Finalizer 和 Final Auditor 每个边界使用相互隔离的 clean State，输出不 merge 回 Executor 或 Selector。

同一 Selector State 持续增长不等于状态正确。旧轨迹中 State digest 和 token position 一直更新，但 Head 仍持续选择错误工具；必须同时评估状态内容和决策结果。

## 6. Selector 的当前合同

当前代码是 25 类，不是 26 类：23 个可执行 operation，加 `final_answer` 和 `ABSTAIN`。

```text
list_directory  search_text  read_file  read_json  file_digest
write_file      write_json   patch_json replace_text remove_line
append_file     make_directory copy_file move_file   delete_file
bind_evidence   check_command run_command web_search connector_lookup
calculator      date_diff    current_time final_answer ABSTAIN
```

Selector 只输出其中一个精确 label，不填写参数，不输出 `name()`，不输出 schema/role 名称。`read_file` 当前确实存在于固定类别、服务菜单和真实 frontier；真实 canary 的问题是 Head 把合法输入分类成 `ABSTAIN`，不是工具缺失或“缺少身份”。

Head v2 的真实失败更像训练分布/输入分布问题，而不是已经证明 2.9B 基座能力不足：合成数据只有英文、模板化两轮轨迹；线上是中文 Strong Planner frontier、多工具竞争和真实因果内容。

### 6.1 计划中的四类 Executor State

这只是待消融方案，当前没有接入产品：

| Executor State 类 | operation |
|---|---|
| `local_observation` | `list_directory, search_text, read_file, read_json, file_digest, bind_evidence` |
| `workspace_mutation` | `write_file, write_json, patch_json, replace_text, remove_line, append_file, make_directory, copy_file, move_file, delete_file` |
| `command_execution` | `check_command, run_command` |
| `external_deterministic` | `web_search, connector_lookup, calculator, date_diff, current_time` |

`final_answer` 进入 Finalizer，`ABSTAIN` 直接阻断；它们不应加载 Executor State。Selector 已经给出精确 operation 后，operation 到类的映射是确定性的，不需要再增加一个学习型“小分类器”。直接用冻结字典选择 profile，才能避免第二个分类错误源。

当前 `RWKV_EXECUTOR_PROFILE_ROUTING=disabled`，运行时只按角色固定 profile，不会根据 operation 动态加载上述四类 State。不要按“四类已上线”的假设制作数据。

## 7. Executor 的当前合同和缺陷

Selector handoff 固定 operation 后，Executor 当前输入字段为：

```text
current_requirement
selected_operation
selected_tool_contract
committed_fact_refs
executor_history
```

生产 renderer：

```text
rwkv_lh/goal_state_protocols/executor_args.py
schema: rwkv-lh.g1j-per-stage-state-tuning.executor-args.v1
```

Executor 每个 action clean start 是正确边界，但当前 v1 输入仍没有通过真实完整事实链：第二次输入已经明确只有 `verify_project.py` 未完成，13.3B 仍重复 `read_file(pricing.py)`。这不是截断：该次输入 725 tokens，远低于 16,384。

E5 是目前最好的实验布局，但没有接入生产：42 次 zero-State 跨类调用严格通过 33 次；本地观察 9/9，外部/确定性 15/15，本地修改 9/12，命令 0/6。失败集中在：

- `replace_text` 输出 Python dict 字面量，使用单引号或 `False`，不是严格 JSON；
- `check_command` / `run_command` 参数内容正确，但函数名误写成 schema/role 名称。

因此 StateTune 数据必须包含长 supporting fact 后服从尾部 remaining state、completed/remaining 对照、命令 operation identity、严格 JSON、中文/英文与路径顺序交叉。不能靠输出后处理改函数名、补语义参数或把 Python 字面量转换成 JSON来掩盖模型失败。

## 8. 函数调用格式

唯一训练目标和推荐输出是 canonical direct-call JSON：

```json
{"function":"read_file","params":{"path":"a.txt","start_byte":0,"max_tokens":4096}}
```

函数名必须是固定 operation label。`read_file()`、`name()`、`executor_args` 或协议 schema 都不是合法函数名。

运行时兼容层可以把以下常见 envelope 规范化为 canonical 形式，但 StateTune target 不得使用这些兼容格式：

```json
{"name":"read_file","arguments":{"path":"a.txt"}}
{"tool":"read_file","parameters":{"path":"a.txt"}}
{"function_call":{"name":"read_file","arguments":{"path":"a.txt"}}}
{"read_file":{"path":"a.txt"}}
```

兼容层只改 envelope 拼写和已闭合的 Markdown fence，不选择工具、不填参数、不改函数名。

生成 prompt 末尾以三个反引号和 `json` 组成的开放围栏是续写锚点，模型返回内容通常从 JSON 对象开始；它本身不是“未闭合围栏”错误。若模型输出自己又创建 Markdown 围栏，则输出必须包含闭合围栏。历史 654 次围栏错误中，496 次是服务 stop suffix 被剥离后的误分类，158 次才是真实 length 截断；当前 transport 只在 raw token IDs 能证明 stop suffix 时恢复它。

## 9. 五个 StateTune 角色的数据格式

五个角色必须独立训练、独立 profile、独立评估，不能合并或互相继承 WKV：

| 角色 | schema | prompt 业务字段 | target |
|---|---|---|---|
| Selector Intent | `...selector-intent.v1` | `stage_objective, stage_role, progress, eligible_labels` | `\nSelectorIntentV1: <exact-label>` |
| Executor Args | `...executor-args.v1` | `current_requirement, selected_operation, selected_tool_contract, committed_fact_refs, executor_history` | canonical selected operation call |
| Step Auditor | `...auditor-step.v1` | `boundary, active_step, available_evidence_refs, evidence_records` | canonical `audit_decision` |
| Finalizer Answer | `...finalizer-answer.v1` | `immutable_goal, completed_steps, committed_facts, evidence_records, format_contract` | canonical `final_answer` |
| Final Auditor | `...auditor-final.v1` | `immutable_goal, completed_steps, committed_facts, available_evidence_refs, evidence_records, final_candidate` | canonical `audit_decision` |

完整 schema 前缀都是：

```text
rwkv-lh.g1j-per-stage-state-tuning.<role>.v1
```

### 9.1 source registry

每行 UTF-8 JSONL 的公共字段和顺序为：

```json
{
  "schema_version":"<role-source-schema>",
  "source_id":"<stable-id>",
  "stage":"<role-state-id>",
  "project_family":"<family-id>",
  "source_kind":"production_trace|executable_fixture|deterministic_counterfactual|human_double_review",
  "source_path":"<repository-relative-path>",
  "source_sha256":"<64-lowercase-hex>",
  "record_locator":"<stable-locator>",
  "parent_source_ids":[],
  "payload":{}
}
```

label 必须由真实执行、确定性 verifier、生产合同或双人复核产生。RWKV 的错误输出只能作为 failure evidence，不能直接成为 target。

### 9.2 训练行

训练器只读取：

```text
rwkv_state_tuning.train.requires_target_suffix.jsonl
```

Dev 只读取对应 dev 文件，sealed 不能被训练或选 checkpoint 的过程读取。每行字段必须严格等于以下三个：

```json
{"prompt":"<exact UTF-8 prefix>","target":"<exact target suffix>","text":"<prompt+target byte concatenation>"}
```

固定要求：UTF-8、LF、`ensure_ascii=false`、JSON separators 为 `,` 和 `:`、BOS token ID 为 0、context length 为 4096、只对 target suffix 计算 loss、`text == prompt + target`。不得在训练 loader 中二次加空格、换行、fence、chat template、BOS 或 EOS；不得排序/改名字段；不得截断。

`manifest.json` 必须固定 dataset/version、source/generator/verifier SHA、renderer/parser/tokenizer SHA、operation registry SHA、split、行数、文件字节数和每个文件 SHA。family split 固定为 SHA-256 bucket：train 0–79、dev 80–89、sealed 90–99；同一 trajectory 和 counterfactual parent 不得跨 split。

### 9.3 当前五套 v1 数据的兼容性审计

2026-09-04 用当前五个 renderer/parser 对全部公开 train+dev source 重验：

| 角色 | 行数 | 当前 source 可验证 | 当前 render 与冻结训练行完全相同 | manifest renderer SHA |
|---|---:|---:|---:|---|
| Selector Intent | 400 | 400 | 400 | 匹配 |
| Executor Args | 253 | 253 | 253 | **不匹配** |
| Step Auditor | 78 | 78 | 0 | **不匹配** |
| Finalizer Answer | 52 | 52 | 52 | 匹配 |
| Final Auditor | 80 | 80 | 0 | **不匹配** |

即使训练行仍能被当前 parser 解析，只要 manifest SHA 不匹配就必须 fail closed。更重要的是，五套训练 `prompt` 都只保存角色 renderer 的 payload，而真实 serving transcript 还会加入下列内容：

- Selector：`SelectorIntentMenuV1` bootstrap + role marker + step prompt；
- Executor：clean Executor bootstrap + role prompt + Tool Call JSON continuation anchor；
- Auditor/Finalizer：system tool definition + role prompt + Tool Call JSON continuation anchor。

当前 `serving_token_ids_match_training` 只比较两个 tokenizer 对同一个训练 prompt 的编码，没有与上述真实 runtime transcript 做字节/token 对比。因此现有五套 v1 数据一律标记为“研究输入，可审计；不可直接开始生产 StateTune”。

训练前必须完成以下硬门禁：

1. 为每个角色建立唯一的 full serving transcript renderer，数据生成和 runtime 调用同一个函数。
2. 冻结新的协议版本；不要覆盖已有 v1 的含义或只更新 manifest SHA。
3. 对每一行比较 `training prompt bytes == runtime pre-generation bytes`，再比较 token IDs。
4. 重新生成 train/dev/sealed、manifest 和所有 sidecar；旧训练行不能混入。
5. 对新数据运行当前 parser、semantic verifier、真实 Harness/evidence verifier 和跨 split 相似度检查。
6. 先跑相同数据、相同 prompt、相同采样的 zero-State 基线，再开始 StateTune。

如果决定采用 E5 输入布局，应先把 E5 变成新的生产 renderer/schema 并完成 R5 同类全链回归，然后再生成该版本的数据。不能把 E5 训练出的 State 加载到当前 `executor-args.v1` serving prompt。

## 10. State 文件和 profile manifest

引擎接受 `rwkv-peft-time-state.v1` checkpoint。文件必须是 PyTorch dictionary，键集合严格为每一层：

```text
blocks.<layer>.att.time_state
```

每个值必须是有限、非全零的 `torch.bfloat16` tensor，单层形状为：

```text
(total_num_heads, head_size, head_size)
```

引擎会按 tensor parallel rank 切分，并再次校验层数、head 数、shape、dtype 和 SHA。不要在导出后转换 dtype、重命名 key 或保存 optimizer wrapper。

profile manifest 格式：

```json
{
  "schema_version":"vllm.rwkv7-state-profiles.v1",
  "model_artifact":"<exact server model artifact>",
  "model_revision":"<exact model revision used by server>",
  "default_profile":"zero",
  "profiles":[
    {
      "id":"executor-args-v2",
      "format":"rwkv-peft-time-state.v1",
      "path":"executor-args-v2.pth",
      "sha256":"<state-file-sha256>"
    }
  ]
}
```

`model_revision` 是服务加载模型时的 revision，不等于 vLLM-RWKV 引擎 Git revision，不能混写。服务启动前设置：

```bash
export VLLM_RWKV7_STATE_PROFILE_MANIFEST='<absolute-profiles.json>'
export VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256='<manifest-sha256>'
```

客户端每次请求通过 extra args 同时发送 profile ID 和 State SHA。项目 `.env.local` 对应字段是：

```text
RWKV_LH_<ROLE>_STATE_PROFILE_ID
RWKV_LH_<ROLE>_STATE_PROFILE_SHA256
RWKV_LH_<ROLE>_STATE_PROFILE_DELIVERY
```

Selector 还需要 `RWKV_LH_SELECTOR_STATE_PROFILE_MANIFEST_SHA256`。ID 和 SHA 必须成对配置；未训练时使用 `zero` 和 64 个零。

模型、模型 SHA、引擎 revision、完整 input schema、full renderer SHA、parser SHA、tokenizer SHA、State 文件 SHA、manifest SHA、profile ID 必须视为一个不可拆的发布身份。Selector 还必须固定 25 类顺序、菜单 digest、feature protocol、Head 文件 SHA 和 logical hash。任意一项改变都需要重新验证，不能伪装成旧身份。

## 11. 当前缺陷清单

| 环节 | 缺陷 | 类型 | 当前处理 |
|---|---|---|---|
| StateTune 数据 | full serving transcript 与训练 prompt 未建立同函数、逐字节一致；三套 renderer SHA 过期 | 工程缺陷，未解决 | 训练前硬阻断 |
| Selector Head | 合成 dev 1.0，真实中文多工具 frontier 选择 `ABSTAIN` | 当前 Head/分布缺陷，未解决 | 新真实轨迹 + 固定 holdout；不能直接归因 2.9B |
| Selector 部署 | 29621 实际 Head 与 `.env.local` 期望 Head 不同 | 部署身份不一致，未解决 | fail closed；不绕过 |
| Executor 输入 | 完整上次文件内容压过尾部 remaining state，重复旧路径 | 输入合同/zero-State 输入敏感，未解决 | E5 仅作后续候选，生产未替换 |
| Executor JSON | `replace_text` 生成 Python dict | 模型输出格式缺陷，未解决 | 进入新数据；不做语义修补 |
| Executor identity | 命令参数正确但函数名变成 schema/role | 模型 operation 遵循缺陷，未解决 | 进入新数据；不重写函数名 |
| 四类 State 路由 | operation 到 profile 的动态路由尚未实现 | 计划能力，不是当前功能 | 先冻结映射并消融；用确定性查表 |
| 推理引擎 | native State、身份、token、transport | 未发现缺陷 | 保持锁定 revision，继续回归 |

已经修复的工程问题：相同失败第 5 次阻断、相同只读零进展第 3 次阻断、纯读取 step 排除所有副作用 operation、`ABSTAIN` 保持合法且不计 action 协议拒绝、Selector State 按 step revision 隔离、Executor 每个 action clean start、机械证据 gate 在 Auditor 之前执行。

控制器的 action 协议拒绝上限仍是 12。这个数字是熔断阈值，不表示 12 种错误。旧链路会对同一 selection 反复解析/校验失败直到达到阈值；当前一次 handoff 最多一次参数修复，达到阈值后持久化 `run_blocked`。最新修复后 canary 的协议拒绝为 0。

## 12. 训练返回后的接入顺序

1. 不改生产配置，先记录模型、数据、renderer、训练器、State 和 manifest 的绝对路径与 SHA。
2. 用新协议的 full transcript 逐字节/token 对齐测试验证 State。
3. 对每个角色跑固定 zero/StateTune A-B；失败样本不重跑，最多按预注册三次后选择指标最好的候选。
4. Executor 四类 profile 分别跑类内矩阵，再跑全 23 operation 交叉矩阵；`final_answer/ABSTAIN` 单独验证。
5. Selector Head 跑真实中文/英文、多工具、停止、恢复和长轨迹 holdout；不能只看合成 dev。
6. 再跑全 Agent Ladder，检查首次偏离、工具分布、step 完成、停止率和最终任务完成率。
7. 全部通过后才更新 `.env.local`，随后 `rwkv-lh-stack status` 验证服务返回身份完全一致。

## 13. 当前证据入口

- `data/experiments/G1J_TRACE_CHAIN_REMEDIATION_V1_20260904/RESULT.md`：原始 20-case 链路和工程整改。
- `data/experiments/G1J_TRACE_CHAIN_REMEDIATION_V1_20260904/RESPONSIBILITY_BOUNDARY_ADDENDUM.md`：Planner/Controller/Selector/Executor/Auditor 权限边界。
- `data/experiments/RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904/RESULT.md`：Head v2、真实 canary、Executor 反事实和引擎判断。
- `data/experiments/RWKV_EXECUTOR_INPUT_CONTRACT_V5_20260904/RESULT.md`：E5 跨类 42 次结果。
- `data/experiments/RWKV_EXECUTOR_INPUT_CONTRACT_V5_20260904/R5_CONTROLLER_COUNTERFACTUAL_RESULT.md`：生产完整事实链路仍重复旧路径。

验证命令：

```bash
cd /home/chase/GitHub/RWKV-LH
uv run pytest -q
uv run rwkv-lh-runtime-smoke
uv run rwkv-lh-e2e --suite all --validate-only
git diff --check
```
