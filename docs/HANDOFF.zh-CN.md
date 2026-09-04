# StateTune 下一步

## 1. 这次训练具体解决什么

这次只解决两个已经定位到 RWKV 输入分布和状态遵循的问题，不训练整个 Agent。

### 第一优先级：2.9B Selector

当前真实链路中，Selector 的 WKV token position 和 state digest 都持续变化，说明 State 确实更新了；但它仍集中选择 `search_text` 和 `read_json`，三种菜单顺序也会产生相关误选。最新例子中，目标是读取 Python 文件，Selector 却两次选择 `read_json`，失败后又重复 `search_text`。

因此这次 Selector StateTune 要解决：

- 让 2.9B 适应当前完整的 `GoalFrontierStateV2`、工具描述、三种菜单顺序和连续 action 结果。
- 根据最新成功、失败和审核缺口改变下一次工具选择，不再重复无进展操作。
- 区分最容易混淆的 `read_file/read_json/search_text/file_digest`，以及其余相邻工具。
- 降低菜单顺序对选择结果的影响。

Selector 的生产输出来自 hidden feature 后面的 MLP Head。因此只训练 State 不够：StateTune 完成后，必须在该 State 上重新提取 hidden feature，再重训与该 State 匹配的 Head。旧 zero-State Head 不能直接和新 State 组合发布。

完成门槛：固定 dev 上 accuracy 和 macro-F1 均不低于 `0.90`，每个有监督的可执行类别 recall 不低于 `0.75`，连续轨迹位置 accuracy 不低于 `0.90`；同一语义的三种菜单顺序应得到同一 operation；真实 Python 文件场景必须先选 `read_file`，失败后不能回到已证明无效的选择。最多训练或真实运行三个预登记候选，三者都未达标时保留固定指标最好的一个，不临时改变评价口径。

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

当前仓库中没有可用于本轮 G1J 的正式 StateTune v2 数据。以下内容不能用于本轮训练：

- `data/datasets/rwkv_lh_g1j_selector_persistent_head_v2/`：这是旧 Head 数据，不是当前 StateTune 数据。
- 服务器 `/home/chase/chase/RWKV-PEFT/data/` 下的 `g1i-*` 和旧 `rwkv_lh_*`：基础模型和线上协议都不是本轮 G1J 合同。
- 当前五角色 v1 生成器：它只保存内部 renderer 片段，还没有保存完整 serving token stream；旧 source freezer 也包含当前普通 frontier 不应使用的 `ABSTAIN` target。

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

## 4. 数据完成后运行什么命令

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

## 5. 如何训练 Selector

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

## 6. Selector State 训练后怎么处理

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
2. 修改 Selector feature extractor，使它显式加载该 profile，而不是当前硬编码的 zero-State。
3. 在三种菜单顺序的冻结 train/dev 轨迹上重新提取 hidden feature。
4. 重训 Head，并把 Head 元数据标记为该 State profile；不得继续使用 `state_tuned=false` 的旧 Head。
5. 同时更新 Selector 服务的 `--profile-manifest`、`--profile-manifest-sha256`、`--profile-id`、`--profile-sha256`，以及 `.env.local` 中对应的三项身份。
6. 通过固定 Selector 门禁后，才开始 Executor 训练。

## 7. 如何训练 Executor

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

## 8. Executor 训练结果如何接入

combined State 可以直接作为一个 Executor profile 接入。项目侧会：

1. 将 `.vllm.pth` 放入稳定 profile 目录并登记 SHA-256。
2. 创建 manifest；`model_artifact` 必须是 `/home/chase/GitHub/RWKV-LH/data/models/rwkv7-g1j-13.3b-vllm-v1`，`model_revision` 必须是 `67f0c5996c50dca0ad779da545cb491527de988f`，`default_profile` 保持 `zero`。
3. 用 `VLLM_RWKV7_STATE_PROFILE_MANIFEST` 和 `VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256` 启动 13.3B 服务。
4. 在 `.env.local` 设置 `RWKV_LH_EXECUTOR_STATE_PROFILE_ID`、`RWKV_LH_EXECUTOR_STATE_PROFILE_SHA256` 和 `RWKV_LH_EXECUTOR_STATE_PROFILE_DELIVERY=request`。
5. 先运行固定 Executor dev，再运行真实链路；每个候选最多三次。

四个 phase State 不能直接写入当前默认配置。它们完成固定对照后，项目侧还需要加入 `phase -> profile_id` 的确定性映射，并保证一个 action 内不切换 profile。没有通过对照前继续使用 combined State 或 zero-State。

## 9. 最终交付格式

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
