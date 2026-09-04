# StateTune 下一步

## 1. 这次训练具体解决什么

这次只解决两个已经定位到 RWKV 输入分布和状态遵循的问题，不训练整个 Agent。

### 第一优先级：2.9B Selector

当前真实链路把同一 Planner step 的多次 Selector 调用接成了持续 WKV 会话，单条菜单顺序的 token position 已从 `1322` 累计到 `5268`。这是职责错误，不是本轮要训练模型适应的目标。Selector 只负责判断当前分子任务属于哪个 operation；全局进度、Action 结果和 Audit 状态由 Controller 保存，必要时由 Planner/Auditor 形成新的当前分子任务。

因此这次 Selector StateTune 要解决：

- 让 2.9B 从一份独立、完整的当前分子任务和当前 eligible menu 中选择 operation。
- 每次选择都从同一个训练后 Selector 初始 State 开始，不继承上一次选择的运行时 WKV。
- 区分最容易混淆的 `read_file/read_json/search_text/file_digest`，以及其余相邻工具。
- 降低菜单顺序对选择结果的影响。

这里的 StateTune 是每次调用都会重新加载的 Selector 角色先验，不是跨 Action 保存的任务记忆。Selector 的生产输出来自 hidden feature 后面的 MLP Head。因此只训练 State 不够：StateTune 完成后，必须在该 State 上对独立 current-subtask 输入重新提取 hidden feature，再重训与该 State 匹配的 Head。旧 zero-State Head 不能直接和新 State 组合发布。

完成门槛：固定 dev 上 accuracy 和 macro-F1 均不低于 `0.90`，每个有监督的可执行类别 recall 不低于 `0.75`；同一当前分子任务的三种菜单顺序应得到同一 operation；真实 Python 文件场景必须选择 `read_file`。最多训练或真实运行三个预登记候选，三者都未达标时保留固定指标最好的一个，不临时改变评价口径。

### 第二优先级：13.3B Executor

Executor StateTune 不负责选工具，只解决已经选定工具后的参数填写：

- `function` 始终等于 Selector 已选 operation。
- `params` 满足唯一工具 schema，必填字段完整。
- 只输出 canonical JSON，不输出 Python dict、解释或多个调用。
- 使用当前 step 的局部事实，不重复上一 action 的参数和已完成工作。

先训练一个覆盖全部 phase 的 Executor State 作为基线，再从同一冻结数据按 `observe/mutate/execute/derive_evidence` 派生四份 State 做固定对照。phase 已经由 Planner 给出，后续只需要确定性映射，不训练新的分类器。

完成门槛：固定 dev 上 operation identity、JSON 协议和参数 schema 三项通过率均为 `1.0`，并且多 action 样本不重复已完成操作。

### 本轮不做

- 不训练 Planner。
- 不训练 Step Auditor、Finalizer 或 Final Auditor。
- 不用 StateTune 掩盖工具实现、Controller 状态或数据 renderer 的工程错误。
- 不读取 90-case sealed/holdout 结果来改训练数据。

顺序固定为：先完成 Selector StateTune 与匹配 Head；Selector 通过后，再开始 Executor StateTune。

## 2. 去哪里做

数据生成、合同校验和实验记录在 WSL：

```text
/home/chase/GitHub/RWKV-LH
```

训练在服务器进行：

```bash
ssh rwkv-8222
cd /home/chase/chase/RWKV-PEFT
```

训练环境：

```text
/home/chase/chase/RWKV-PEFT/.venv/bin/python
```

G1J 原始模型：

```text
2.9B:  /mnt/nas-model/g1j/rwkv7-g1j-2.9b-20260831-ctx16384.pth
SHA:   966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239

13.3B: /mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth
SHA:   559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65
```

服务器训练数据放在：

```text
/home/chase/chase/RWKV-PEFT/data/<dataset_id>/
```

训练产物放在：

```text
/home/chase/chase/RWKV-PEFT/out/<run_id>/
```

`/home/chase/chase/RWKV-PEFT` 当前不是 Git worktree。每次训练前必须记录训练代码摘要，不能只记录目录名：

```bash
cd /home/chase/chase/RWKV-PEFT
sha256sum train.py rwkvt/state_tuning.py rwkvt/dataset/dataset.py
.venv/bin/python -c 'import torch,lightning,deepspeed; print(torch.__version__, lightning.__version__, deepspeed.__version__)'
```

当前环境已确认是 Python venv、Torch `2.9.0+cu128`、Lightning `2.5.5`、DeepSpeed `0.18.1`。

## 3. 现在还不能直接训练的原因

当前仓库中没有可用于本轮 G1J 的正式 StateTune v2 数据。仓库内旧数据和旧生成器已经删除；服务器旧数据也不能用于本轮训练：

- `data/datasets/rwkv_lh_g1j_selector_persistent_head_v2/`：这是旧 Head 数据，不是当前 StateTune 数据。
- 服务器 `/home/chase/chase/RWKV-PEFT/data/` 下的 `g1i-*` 和旧 `rwkv_lh_*`：基础模型和线上协议都不是本轮 G1J 合同。
- 五角色 v1 生成器：它只保存内部 renderer 片段，没有保存完整 serving token stream；旧 source freezer 也包含普通 frontier 不应使用的 `ABSTAIN` target。

开训前必须先在 RWKV-LH 中生成并冻结：

```text
data/datasets/rwkv_lh_g1j_selector_intent_state_tuning_v2/
data/datasets/rwkv_lh_g1j_executor_args_state_tuning_v2/
```

每个目录至少必须有：

```text
manifest.json
source_registry.jsonl
sample_index.jsonl
verification_records.jsonl
tokenizer_records.jsonl
rwkv_state_tuning.train.requires_target_suffix.jsonl
rwkv_state_tuning.dev.requires_target_suffix.jsonl
generation_validation.json
leakage_audit.json
tokenizer_target_suffix_audit.json
```

只有三个校验报告均为 `passed=true`，且 manifest 中的文件 SHA 全部匹配，才进入服务器训练。

## 4. v2 数据集具体怎样构造

一句话定义：**一条 v2 训练样本，是模型在一个真实决策时刻实际收到的完整输入字节，加上这个时刻唯一正确的输出；不是把若干内部 JSON 字段单独拼成问答。**

本轮只构造下面两份数据：

| 数据集 | 输入回答的问题 | 监督目标 |
| --- | --- | --- |
| Selector v2 | 当前 Planner 分子任务和当前可选工具下，应选哪个 operation | 一个 operation 名称 |
| Executor v2 | operation 已经选定、参数 schema 已经披露后，应填写什么参数 | 一个完整 canonical JSON 调用 |

### 4.1 先冻结语义轨迹，不直接手写训练 prompt

源数据的基本单位是完整任务轨迹。每条轨迹至少保存：

```json
{
  "episode_id": "唯一任务轨迹 ID",
  "project_family": "用于隔离 train/dev/sealed 的任务族",
  "immutable_goal": "原始用户目标",
  "workspace_fixture_id": "可复现工作区",
  "plan_steps": ["当前协议的 Planner step"],
  "events": ["按发生顺序保存的 Action、结果、错误和 Audit 事件"],
  "decisions": [
    {
      "step_id": "所属 Planner step",
      "step_revision": 1,
      "event_cursor": 0,
      "expected_operation": "read_file",
      "expected_command": {
        "function": "read_file",
        "params": {"path": "src/pricing.py", "start_byte": 0, "max_tokens": 1024}
      },
      "authority": "executed_fixture",
      "verifier_id": "固定验证器 ID"
    }
  ]
}
```

这里的 `event_cursor` 表示这个决策发生前已经提交到 `RunState` 的最后一个事件。生成器只能回放到该位置，不能把后续 Action、Audit 结论或最终答案放进输入。

完整轨迹用于复核标签和构造 Executor 事实，但 Selector renderer 必须忽略 `events` 和 `event_cursor`，只读取当前 Planner 分子任务。

标签来源只允许四种：

- 当前版本真实 trace 中已由 Harness 和 Audit 验证的成功决策。
- 能在 `temp/` 隔离工作区中真实执行并通过验证的确定性 fixture。
- 从一个已验证 fixture 派生的确定性反事实，例如保持目标不变但把文件类型从 JSON 改为 Python，使标签由 `read_json` 变为 `read_file`；反事实必须记录父样本 ID。
- 无法机械判定时的双人复核；不得使用 Selector 或 Executor 自己的输出给自己打标签。

如果一个当前分子任务存在两个同样合理的 operation，就拆清任务或丢弃该样本，不能用 `ABSTAIN` 掩盖不明确的标签。

只接受当前 G1J 协议生成的 trace。旧 compact protocol、旧模型输出、旧 StateTune 数据都不能混入 v2。

首版固定覆盖 23 个可执行 operation，不把 `final_answer` 和 `ABSTAIN` 当作训练标签：`final_answer` 在线只有 singleton eligible menu，不需要学习比较；`ABSTAIN` 在普通 frontier 中不会获得执行资格。

### 4.2 Selector v2 的构造

每个语义决策点按以下顺序生成：

1. 取 Planner 当前唯一 active step，只保留 `objective`、`phase`、`read_roots`、`write_roots`、`constraints` 和 success criteria。
2. 由生产 Controller 根据 phase 和 roots 计算 eligible operations；源数据不能手写 eligible menu。
3. 使用生产与数据共用的 current-subtask renderer。输入中不包含历史 Selector prompt、历史 WKV、已完成 step、Action 结果列表、计数器或 Audit 事件。
4. 对 `canonical`、`rotate_8`、`rotate_17` 分别创建一次 fresh Selector 调用。三次都从同一个固定 StateTune profile 初始化，三次之间不传 parent State。
5. 用生产 `network_selector_input_protocol(...)` 渲染输入，不在生成器中复制提示词模板。
6. 用 `selector_intent.render_target(...)` 生成唯一 target。

每一次的完整输入都只有一份 bootstrap 和一份当前分子任务：

```text
render_bootstrap(current_input) + "\n" + render_step(current_input)
```

不存在位置 0、位置 1 的累计链，也不生成 `parent_state`。三轮投票只是对同一个当前分子任务做三个菜单排列的独立判断；投票完成后，三个临时 WKV 都丢弃。

发生问题时按职责处理：Executor JSON 或参数失败，由 Executor 保持相同 operation 重试；Harness 执行失败或证据不足，由 Controller 记录并交给 Planner/Auditor 形成新的 step 或 revision。只有产生了新的当前分子任务，才重新调用 fresh Selector。Selector 自己不读取和解释历史失败。

每个决策点最终产生三行训练数据，三行的 target 完全一致：

```json
{"prompt":"<该菜单顺序下截至当前决策的完整生产输入>","target":"\nSelectorIntentV2: read_file","text":"<prompt><target>"}
```

首版配额固定为：每个可执行 operation 80 个独立当前分子任务，其中直接任务、相邻 operation 对照、不同自然表述、phase/root 边界各 20 个；每类按 `64 train / 8 dev / 8 sealed` 冻结。因此共有 1840 个语义决策点；三种菜单顺序展开后是 `4416 train / 552 dev / 552 sealed` 行。任务内容、路径、文件类型和相邻易混淆 operation 必须真实变化，不能只替换随机字符串制造重复样本。

Selector v2 必须额外保存：

```text
menu_variant_registry.jsonl
```

它证明一个语义决策的三种菜单顺序拥有同一个 split、同一个 target，并且三行均为 `parent_state=null`。不再创建 `sequence_registry.jsonl`。

### 4.3 Executor v2 的构造

Executor 样本从同一批语义轨迹的 action handoff 生成，不另造一套不相干的问题：

1. 回放到 Selector 已提交 `expected_operation`、但 Executor 尚未生成参数的时刻。
2. `selected_tool_contract` 必须从当前 `ActionHarness` 注册表读取，不能抄写 schema。
3. `current_requirement` 使用当前 Planner step 的 objective；只投影该 step 和依赖 step 已提交的 Action 事实。
4. 通过生产的 clean Executor bootstrap、assignment 投影和 `executor_args.render_generation_prompt(...)` 构造输入。
5. 捕获 `session.generate(...)` 调用前 checkpoint 的完整 `transcript` 作为训练 `prompt`。不能只保存 `ExecutorArgsPromptV1` 这一小段。
6. 用 `executor_args.render_target(...)` 生成 target，格式只能是 `{"function":"<已选 operation>","params":{...}}`。

正常首次调用的完整边界等价于：

```text
render_independent_executor_bootstrap(current_assignment)
+ "\n\n"
+ executor_args.render_generation_prompt(selected_operation_payload)
```

但生成器必须调用与生产共用的 renderer 并校验 transcript SHA，不能自行复制这段拼接逻辑。协议失败重试也必须从真实 rejection event 回放到新的 generation checkpoint，再捕获完整 transcript。

每个 operation 固定 80 条：

- 20 条干净首次调用。
- 20 条带相关依赖事实。
- 20 条带已完成 Action 和旧参数干扰，正确答案不得复制旧 operation 或旧参数。
- 20 条同一 operation 的协议失败重试；prompt 中可以有被拒绝输出和错误原因，但 target 必须是修正后的合法调用。

每个 operation 按 `64 train / 8 dev / 8 sealed` 冻结，共 `1472 train / 184 dev / 184 sealed` 行。23 个 operation 的所有注册参数都必须显式填写，包括有默认值的参数；验证器随后调用 `ActionHarness.normalize_action(...)`，归一化前后必须完全一致，并在隔离 fixture 中真实执行成功。

先生成一份 combined 数据。四个 phase 视图只按当前固定映射过滤 combined 样本，不重新渲染、不重新切分：

```text
observe:         list_directory, search_text, read_file, read_json, file_digest, web_search, connector_lookup
mutate:          write_file, write_json, patch_json, replace_text, remove_line, append_file, make_directory, copy_file, move_file, delete_file
execute:         check_command, run_command
derive_evidence: bind_evidence, calculator, date_diff, current_time
```

### 4.4 切分、token 和验收

- 先按 `project_family` 使用已登记 SHA-256 bucket 算法切分，再渲染样本。
- 同一 episode、反事实父子、三个菜单顺序和所有 step 必须位于同一 split。
- sealed 文件单独保存，生成训练数据、选 checkpoint 和调参时不可读取。
- 使用生产 `RWKVTokenizer`，每行只在开头加入一次 BOS `0`。Selector 和 Executor 都是 fresh/clean State 单次输入，v2 上限固定为 4096 token；不得截断，manifest 必须记录实际最大值。
- loss 只覆盖 target suffix；第一个 target token 必须由 prompt 的最后一个 token 预测。
- Selector prompt 不得泄漏 `expected_operation`；Executor prompt 中允许出现已提交 operation，但 `function` 必须保持相同。
- 每个源 fixture、renderer、verifier、tokenizer、输出文件都记录 SHA-256。
- `generation_validation.json`、`leakage_audit.json` 和 `tokenizer_target_suffix_audit.json` 必须全部 `passed=true`；任一失败都不能上传训练服务器。

### 4.5 落盘位置和生成命令

语义源和预登记统一放在：

```text
data/experiments/RWKV_LH_G1J_STATETUNE_V2_20260904/
├── PREREGISTRATION.md
├── source_authority/trajectories.jsonl
├── selector_intent/source_registry.full.jsonl
└── executor_args/source_registry.full.jsonl
```

需要新增且只保留三个 v2 脚本：

```text
scripts/freeze_g1j_state_tuning_source_registries_v2.py
scripts/generate_g1j_selector_intent_state_tuning_v2.py
scripts/generate_g1j_executor_args_state_tuning_v2.py
```

脚本及测试完成后，在 WSL 中用绝对路径执行：

```bash
cd /home/chase/GitHub/RWKV-LH

uv run python /home/chase/GitHub/RWKV-LH/scripts/freeze_g1j_state_tuning_source_registries_v2.py \
  --output-experiment /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_LH_G1J_STATETUNE_V2_20260904

uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_g1j_selector_intent_state_tuning_v2.py \
  --build \
  --source-registry /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_LH_G1J_STATETUNE_V2_20260904/selector_intent/source_registry.full.jsonl \
  --output /home/chase/GitHub/RWKV-LH/data/datasets/rwkv_lh_g1j_selector_intent_state_tuning_v2

uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_g1j_executor_args_state_tuning_v2.py \
  --build \
  --source-registry /home/chase/GitHub/RWKV-LH/data/experiments/RWKV_LH_G1J_STATETUNE_V2_20260904/executor_args/source_registry.full.jsonl \
  --output /home/chase/GitHub/RWKV-LH/data/datasets/rwkv_lh_g1j_executor_args_state_tuning_v2
```

freezer 必须拒绝覆盖已有冻结目录；如需改变任一源样本、配额或规则，创建新的 experiment ID 和 dataset version，不能原地改 v2。

### 4.6 一条样本如何流转

以“读取 `src/pricing.py`，确认价格计算规则”为例：

```text
Planner step:
  phase=observe
  read_roots=["src/pricing.py"]
  objective="读取 src/pricing.py 并确认价格计算规则"

决策 0:
  eligible=[list_directory, search_text, read_file, read_json, file_digest]
  Selector target=read_file
  Executor target={"function":"read_file","params":{"path":"src/pricing.py","start_byte":0,"max_tokens":1024}}
```

这个分子任务会分别生成三种菜单顺序的 Selector 行，但只生成一条 Executor 行。三条 Selector prompt 都从相同初始 State 独立开始，不包含此前任何选择。如果执行后仍有工作，Planner/Auditor 必须先形成另一个明确的当前分子任务，再生成另一组三行。

运行时已经改为 fresh current-subtask 输入：请求没有 parent State，三种菜单顺序分别从同一初始 profile 独立前向，Selector 输入不再包含历史 Action/Audit 或进度计数。下一步只实现上述 v2 freezer、generator 和数据全量校验；冻结目录生成且三份报告通过前，不执行第 5 节的数据上传，也不运行第 6、8 节的训练命令。

当前协议回归样本三种菜单顺序分别是 `725 / 725 / 727` token，全部从位置 0 独立开始；线上会在每条 lane 的 `input_token_count` 中记录实际值，不再出现 `1322 -> 2454 -> 3292 -> 4130 -> 5268` 这种跨调用累计。

## 5. 数据完成后运行什么命令

先从 WSL 同步到服务器，不使用 `--delete`：

```bash
cd /home/chase/GitHub/RWKV-LH

rsync -a --checksum \
  data/datasets/rwkv_lh_g1j_selector_intent_state_tuning_v2/ \
  rwkv-8222:/home/chase/chase/RWKV-PEFT/data/rwkv_lh_g1j_selector_intent_state_tuning_v2/

rsync -a --checksum \
  data/datasets/rwkv_lh_g1j_executor_args_state_tuning_v2/ \
  rwkv-8222:/home/chase/chase/RWKV-PEFT/data/rwkv_lh_g1j_executor_args_state_tuning_v2/
```

登录服务器后检查模型、数据和空闲 GPU：

```bash
ssh rwkv-8222
cd /home/chase/chase/RWKV-PEFT

sha256sum /mnt/nas-model/g1j/rwkv7-g1j-2.9b-20260831-ctx16384.pth
sha256sum /mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth
nvidia-smi --query-gpu=index,uuid,memory.total,memory.free --format=csv,noheader,nounits
pgrep -af '/train.py' || true
```

SHA 不匹配、已有训练进程或没有足够显存时停止，不自动更换模型、数据或训练参数。

## 6. 如何训练 Selector

这是一轮从 zero-State 开始的固定基线。`GPU=3` 只是当前服务器上的可用示例；运行前按 `nvidia-smi` 选择空闲 GPU 并登记其 UUID。

```bash
cd /home/chase/chase/RWKV-PEFT

GPU=3
DATA=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_g1j_selector_intent_state_tuning_v2
RUN=/home/chase/chase/RWKV-PEFT/out/g1j-2p9-selector-intent-state-v2-seed20260904
LOG=/home/chase/chase/RWKV-PEFT/temp/g1j-2p9-selector-intent-state-v2-seed20260904.log
ROWS=$(wc -l < "$DATA/rwkv_state_tuning.train.requires_target_suffix.jsonl")
SAVE=$(( (ROWS + 3) / 4 ))

test "$ROWS" -gt 0
test ! -e "$RUN"

nohup env CUDA_VISIBLE_DEVICES="$GPU" \
  .venv/bin/python train.py \
  --load_model /mnt/nas-model/g1j/rwkv7-g1j-2.9b-20260831-ctx16384.pth \
  --proj_dir "$RUN" \
  --data_file "$DATA/rwkv_state_tuning.train.requires_target_suffix.jsonl" \
  --data_type jsonl \
  --loss_mask target_suffix \
  --jsonl_bos_token_id 0 \
  --data_shuffle 0 \
  --vocab_size 65536 \
  --n_layer 32 \
  --n_embd 2560 \
  --ctx_len 4096 \
  --micro_bsz 1 \
  --accumulate_grad_batches 1 \
  --epoch_steps "$ROWS" \
  --epoch_count 1 \
  --epoch_save 1 \
  --step_save "$SAVE" \
  --lr_init 2e-5 \
  --lr_final 4e-6 \
  --lr_schedule cos \
  --warmup_steps 40 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 20260904 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla \
  >"$LOG" 2>&1 &

echo $! > "$LOG.pid"
tail -f "$LOG"
```

不得为了避免 OOM 把 `ctx_len` 临时降到小于数据 manifest 登记的最大 token 数；如果 OOM，停止并记录，不修改本轮合同。

训练会在 `RUN` 下同时生成 `rwkv-step-<N>.pth` 和可直接用于当前 vLLM profile 的 `rwkv-step-<N>.vllm.pth`。

## 7. Selector State 训练后怎么处理

先用 dev 选择 checkpoint，不读取 sealed。然后校验 `.vllm.pth`：

```bash
cd /home/chase/chase/RWKV-PEFT
STATE=/home/chase/chase/RWKV-PEFT/out/g1j-2p9-selector-intent-state-v2-seed20260904/rwkv-step-<N>.vllm.pth
EXPECTED_LAYERS=32
EXPECTED_HEADS=40

sha256sum "$STATE"
STATE="$STATE" EXPECTED_LAYERS="$EXPECTED_LAYERS" EXPECTED_HEADS="$EXPECTED_HEADS" \
  .venv/bin/python -c 'import os,torch; p=os.environ["STATE"]; n=int(os.environ["EXPECTED_LAYERS"]); h=int(os.environ["EXPECTED_HEADS"]); x=torch.load(p,map_location="cpu",weights_only=True); assert set(x)=={f"blocks.{i}.att.time_state" for i in range(n)}; assert all(v.dtype==torch.bfloat16 and tuple(v.shape)==(h,64,64) and torch.isfinite(v).all() and torch.count_nonzero(v) for v in x.values()); print("state-ok")'
```

把以下内容交回 RWKV-LH 项目侧：

- 选中 State 的绝对路径和 SHA-256。
- run ID、训练日志、GPU UUID。
- 数据 manifest SHA-256。
- 训练代码三个 SHA-256 和依赖版本。
- 选中 checkpoint 的 dev 结果。

项目侧随后必须完成：

1. 把 State 复制到 `data/models/state_profiles/<profile_id>/` 并创建 `vllm.rwkv7-state-profiles.v1` manifest。
2. 使用 Selector 服务现有的 `--profile-manifest`、`--profile-manifest-sha256`、`--profile-id` 和 `--profile-sha256` 参数加载该 profile；运行时已经支持显式 profile，不需要再改 extractor。
3. 在三种菜单顺序的冻结 train/dev 独立 current-subtask 样本上重新提取 hidden feature；每行都从该 State profile 重新初始化。
4. 重训 Head，并把 Head 元数据标记为该 State profile；不得继续使用 `state_tuned=false` 的旧 Head。
5. 同时更新 `.env.local` 中对应的 State 和 Head 身份摘要。
6. 通过固定 Selector 门禁后，才开始 Executor 训练。

## 8. 如何训练 Executor

Selector 通过后再运行。先训练一个包含四个 phase 的 combined State；phase State 只是在同一冻结源上的四份视图，命令相同，只把 `DATA` 换为 `rwkv_lh_g1j_executor_args_state_tuning_v2_<phase>`，并把 `RUN` 换成对应 phase 的新目录。

```bash
cd /home/chase/chase/RWKV-PEFT

GPU=3
DATA=/home/chase/chase/RWKV-PEFT/data/rwkv_lh_g1j_executor_args_state_tuning_v2
RUN=/home/chase/chase/RWKV-PEFT/out/g1j-13p3b-executor-args-combined-state-v2-seed20260904
LOG=/home/chase/chase/RWKV-PEFT/temp/g1j-13p3b-executor-args-combined-state-v2-seed20260904.log
ROWS=$(wc -l < "$DATA/rwkv_state_tuning.train.requires_target_suffix.jsonl")
SAVE=$(( (ROWS + 3) / 4 ))

test "$ROWS" -gt 0
test ! -e "$RUN"

nohup env CUDA_VISIBLE_DEVICES="$GPU" \
  .venv/bin/python train.py \
  --load_model /mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth \
  --proj_dir "$RUN" \
  --data_file "$DATA/rwkv_state_tuning.train.requires_target_suffix.jsonl" \
  --data_type jsonl \
  --loss_mask target_suffix \
  --jsonl_bos_token_id 0 \
  --data_shuffle 0 \
  --vocab_size 65536 \
  --n_layer 61 \
  --n_embd 4096 \
  --ctx_len 4096 \
  --micro_bsz 1 \
  --accumulate_grad_batches 1 \
  --epoch_steps "$ROWS" \
  --epoch_count 1 \
  --epoch_save 1 \
  --step_save "$SAVE" \
  --lr_init 2e-5 \
  --lr_final 4e-6 \
  --lr_schedule cos \
  --warmup_steps 40 \
  --beta1 0.9 \
  --beta2 0.99 \
  --adam_eps 1e-8 \
  --random_seed 20260904 \
  --accelerator gpu \
  --precision bf16 \
  --devices 1 \
  --strategy deepspeed_stage_1 \
  --grad_cp 1 \
  --num_workers 2 \
  --my_testing x070 \
  --peft state \
  --op fla \
  >"$LOG" 2>&1 &

echo $! > "$LOG.pid"
tail -f "$LOG"
```

Executor checkpoint 校验与 Selector 相同，但必须使用 `EXPECTED_LAYERS=61`、`EXPECTED_HEADS=64`。

## 9. Executor 训练结果如何接入

combined State 可以直接作为一个 Executor profile 接入。项目侧会：

1. 将 `.vllm.pth` 放入稳定 profile 目录并登记 SHA-256。
2. 创建 manifest；`model_artifact` 必须是 `/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1`，`model_revision` 必须是 `67f0c5996c50dca0ad779da545cb491527de988f`，`default_profile` 保持 `zero`。
3. 用 `VLLM_RWKV7_STATE_PROFILE_MANIFEST` 和 `VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256` 启动 13.3B 服务。
4. 在 `.env.local` 设置 `RWKV_LH_EXECUTOR_STATE_PROFILE_ID`、`RWKV_LH_EXECUTOR_STATE_PROFILE_SHA256` 和 `RWKV_LH_EXECUTOR_STATE_PROFILE_DELIVERY=request`。
5. 先运行固定 Executor dev，再运行真实链路；每个候选最多三次。

四个 phase State 不能直接写入当前默认配置。它们完成固定对照后，项目侧还需要加入 `phase -> profile_id` 的确定性映射，并保证一个 action 内不切换 profile。没有通过对照前继续使用 combined State 或 zero-State。

## 10. 最终交付格式

训练完成后只需要提供下面这组信息：

```text
role:
phase: combined | observe | mutate | execute | derive_evidence
base_model_path:
base_model_sha256:
dataset_id:
dataset_manifest_sha256:
run_id:
selected_checkpoint_path:
selected_checkpoint_sha256:
train_log_path:
gpu_uuid:
train_py_sha256:
state_tuning_py_sha256:
dataset_loader_sha256:
torch_version:
lightning_version:
deepspeed_version:
dev_result_path:
```

不要把 `.env.local`、API key、sealed 数据结果或未选中的临时 checkpoint 上传到 GitHub。
