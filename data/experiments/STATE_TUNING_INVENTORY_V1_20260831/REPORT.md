# RWKV-LH State Tuning 配置、Loss 与数据谱系清单

日期：2026-08-31（Asia/Shanghai）

## 1. 口径

本清单只统计真正更新 RWKV 初始 WKV state 的 `peft=state` 训练。使用冻结 RWKV hidden/WKV 特征再训练 selector MLP/head 的 `TRAINING_HISTORY.json` 属于 head 训练，不和 state loss 混算。

扫描结果：

- 27 个已执行的纯 WKV state 训练族：13.3B Executor 15 个，2.9B Selector 12 个。
- 25 个训练族保留了可恢复的逐 step loss：23 个 `loss_data.jsonl`，G4/G8 仅有原始训练日志。
- G5/G6 有 checkpoint 与校验记录，但仓库没有逐 step loss 文件。
- 另有 2 个本地消融预注册配置，没有发现与之对应的独立训练 loss，不计入“已执行训练族”。
- 34 个带 `rwkv_state_tuning.train*.jsonl` 的数据目录，均进入数据谱系清点；其中部分只有数据，尚无 state 训练记录。

只保留下文可由当前仓库复核的事实；缺失字段写“未留档”，不作推测。

## 2. 当前实际部署状态

### 13.3B Executor

`/v1/capabilities` 当前返回：

- model：`rwkv7-g1i-13.3b-exe-g3-g6-deterministic-cmix-r7-multiprofile-ctx2496`
- `prompt_replay=false`
- `max_model_len=16384`
- native state：create/resume/fork/commit/rollback/export/import 均为 true
- state 不是 authority：`authoritative=false`
- state 角色：`cache_role=disposable_acceleration`
- pending-token 语义：`state_before_exactly_one_pending_token`
- 每 worker cache 容量：16

当前 Worker 配置使用 G3 general profile（step 2000）和 G6 network profile（step 1500）。G3 profile SHA256 为 `13f6586951666962405286dda8e45c1eae82a37c68c21b3b75dbbb04c6e54f12`，G6 profile SHA256 为 `611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b`；服务模型整体 SHA256 为 `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。

### 2.9B Selector

当前 29621 服务使用：

- model：`rwkv7-g1i-2.9b-vllm-v1`
- selector head：S60 requirement-byte-tail H64
- profile manifest：S31 step 2000 的 profile manifest
- **实际 profile-id：`zero`**

因此，本地虽保存 S1/S2/S12/S19/S25/S27/S31/S54/S61/S67/S70/S71 等 state profile，当前 2.9B Selector 在线链路没有施加这些 tuned state。在线效果主要来自基础 2.9B + S60 head，不是 2.9B state tuning。

## 3. State 参数与共同训练配置

| 模型 | 层数/state tensor 数 | 单 tensor shape | BF16 checkpoint 量级 |
|---|---:|---|---:|
| 13.3B | 61 | `[64,64,64]` | 约 32,001,xxx bytes |
| 2.9B | 32 | `[40,64,64]` | 约 10,496,xxx bytes |

基础权重：

- 13.3B：`rwkv7-g1i-13.3b-20260805-ctx16384.pth`，SHA256 `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`。
- 2.9B：`rwkv7-g1i-2.9b-20260805-ctx16384.pth`，SHA256 `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。

所有已记录字段一致、且没有相反配置的共同项：

- `peft=state`，base weights 校验为不变。
- `op=fla`，BF16，DeepSpeed stage 1，gradient checkpointing。
- micro batch 1、gradient accumulation 1、单卡、1 epoch。
- Adam β1=0.9、β2=0.99、eps=1e-8，cosine LR。
- 训练目标统一为 `target_suffix`；历史 assistant 内容不应进入监督 mask。
- train JSONL 作为优化输入；dev/test 作为下游选择与回归集。纯 state 训练日志没有逐 step `dev_loss`。

## 4. 13.3B Executor 全部 state 配置

| 训练 | 初始化 | train/dev | ctx | LR init → final | warmup | seed | save | loss 留档 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Round1 | exact zero | 2000/200 | 2496 | 2e-5 → 2e-6 | 50 | 826 | 250 | JSONL |
| Stage1 | Round1 continuation | 500/79 | 2496 | 5e-5 → 1e-5 | 20 | 827 | 100 | JSONL |
| Stage2 | Stage1 continuation | 640/96 | 2496 | 3e-5 → 6e-6 | 24 | 828 | 160 | JSONL |
| Stage3 | **Stage1 step 500 branch** | 1400/176 | 2496 | 2e-5 → 4e-6 | 40 | 829 | 350 | JSONL |
| Stage4 | **Stage1 step 500 branch** | 1140/240 | 2496 | 1e-5 → 2e-6 | 40 | 830 | 285 | JSONL |
| Stage5 | **Stage1 step 500 branch** | 1220/240 | 2496 | 7e-6 → 1.4e-6 | 40 | 831 | 305 | JSONL |
| Stage6 | **Stage1 step 500 branch** | 1300/240 | 2496 | 5e-6 → 1e-6 | 40 | 832 | 325 | JSONL |
| Stage7 | **Stage4 step 1140 continuation** | 2000/400 | 2496 | 3e-6 → 6e-7 | 20 | 833 | 500 | JSONL |
| G3 multistage | exact zero | 2000/480 | 2496 | 2e-5 → 2e-6 | 未留档 | 1055 | 250 | JSONL |
| G4 true workflow | exact zero | 2000/480 | 2496 | 2e-5 → 2e-6 | 未留档 | 1059 | 250 | 原始 log |
| G5 G3→workflow | G3 step 2000 | 2000/480 | 2496 | 5e-6 → 5e-7 | 40 | 1063 | 250 | **缺失** |
| G6 network recovery | G4 step 2000 exact parent | 2000/480 | 2496 | 2e-6 → 2e-7 | 未留档 | 1067 | 250 | **缺失** |
| G7 network retention | G6 step 1500 parent | 1200/— | 2496 | 1e-6 → 1e-7 | 24 | 1071 | 150 | JSONL |
| G8 engineering retention | G6 step 1500 parent | 2000/— | 2496 | 2e-6 → 2e-7 | 40 | 1079 | 250 | 原始 log |
| G9 stable schema | G6 step 1500 parent | 2000/— | 2496 | 5e-7 → 5e-8 | 40 | 1091 | 250 | JSONL |

注意：Stage2、Stage3、Stage4、Stage5、Stage6 都从同一个 Stage1 step 500 checkpoint 分叉，并非按编号串行训练；Stage7 才从 Stage4 step 1140 继续。G5/G6 checkpoint 是真实存在且通过 keys/shapes/finite/nonzero 校验，但 loss 轨迹没有被收集回当前仓库。

## 5. 2.9B Selector 全部 state 配置

| 训练 | 初始化 | train/dev | ctx | LR init → final | warmup | seed | save | loss 留档 |
|---|---|---:|---:|---:|---:|---:|---:|---|
| S1 broad selector | zero | 6000/750 | 1024 | 2e-5 → 2e-6 | 100 | 830 | 1000 | JSONL |
| S2 residual | zero | 2000/276 | 1408 | 2e-5 → 4e-6 | 40 | 831 | 500 | JSONL |
| S12 gate | zero | 1467/275 | 512 | 2e-5 → 4e-6 | 30 | 843 | 489 | JSONL |
| S19 connector/function | zero | 2000/926 | 512 | 2e-5 → 4e-6 | 40 | 857 | 500 | JSONL；manifest 缺失，配置来自 train log |
| S25 current harness | zero | 2000/276 | 1216 | 2e-5 → 4e-6 | 40 | 863 | 500 | JSONL |
| S27 persistent trajectory | zero | 2000/500 | 1536 | 2e-5 → 4e-6 | 40 | 887 | 500 | JSONL |
| S31 true trajectory | zero | 2000/500 | 1536 | 2e-5 → 4e-6 | 40 | 1031 | 500 | JSONL |
| S54 multistage request-last | exact zero | 2000/500 | 2496 | 2e-5 → 4e-6 | 未留档 | 1054 | 500 | JSONL |
| S61 transaction continuation | exact zero | 2000/500 | 2496 | 2e-5 → 4e-6 | 未留档 | 1061 | 500 | JSONL |
| S67 V2 contract | exact zero | 2000/500 | 2496 | 2e-5 → 4e-6 | 40 | 1067 | 500 | JSONL |
| S70 uniform 25-op | exact zero | 2000/500 | 2496 | 2e-5 → 4e-6 | 40 | 1067 | 500 | JSONL |
| S71 diverse boundary | exact zero | 2000/500 | 2496 | 2e-5 → 4e-6 | 40 | 1067 | 500 | JSONL |

## 6. 全部有效纯 state 训练 loss

指标定义：`mean`/`median` 为全训练序列；`tail μ`/`tail med` 为最后 100 step。因为数据按样本顺序记录且 loss 分布明显尖峰，不能只看最后一个 step。

### 13.3B

| 训练 | steps | first | mean | median | tail μ | tail med | last | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Round1 | 2000 | 0.208008 | 0.0758835 | 1.50681e-4 | 1.50368e-3 | 1.90139e-5 | 4.40598e-4 | 4.38094e-6 | 2.73438 |
| Stage1 | 500 | 3.47900e-3 | 0.0126522 | 4.79221e-5 | 1.02966e-4 | 2.05636e-5 | 1.99080e-5 | 1.23382e-5 | 1.78125 |
| Stage2 | 640 | 2.33650e-5 | 2.91533e-3 | 1.19805e-5 | 5.25057e-6 | 4.50015e-6 | 3.71039e-6 | 2.80142e-6 | 0.757812 |
| Stage3 | 1400 | 1.90735e-5 | 4.98471e-3 | 1.59144e-5 | 1.18009e-3 | 5.93066e-6 | 5.87106e-6 | 3.26335e-6 | 0.773438 |
| Stage4 | 1140 | 0.0771484 | 0.0151959 | 1.13964e-4 | 1.55101e-4 | 5.43594e-5 | 2.18153e-5 | 1.22786e-5 | 1.22656 |
| Stage5 | 1220 | 1.26958e-5 | 0.0282748 | 2.19345e-4 | 6.04288e-3 | 1.90258e-4 | 0.150391 | 1.26958e-5 | 0.898438 |
| Stage6 | 1300 | 0.0224609 | 0.0339058 | 3.24249e-4 | 0.0212228 | 3.04222e-4 | 0.145508 | 1.26362e-5 | 1.20312 |
| Stage7 | 2000 | 2.07424e-5 | 0.0111711 | 1.82986e-5 | 7.85938e-3 | 1.04308e-5 | 1.23978e-5 | 4.88758e-6 | 1.13281 |
| G3 | 2000 | 0.236328 | 0.0292266 | 2.77519e-4 | 1.71435e-4 | 5.93662e-5 | 1.59264e-4 | 9.35793e-6 | 2.23438 |
| G4 (raw log) | 2000 | 0.136 | 0.101469 | 1.34e-3 | 5.81501e-3 | 6.58e-5 | 5.72e-5 | 9.54e-6 | 9.38 |
| G7 | 1200 | 1.37091e-5 | 3.73002e-3 | 9.60827e-5 | 2.21709e-3 | 1.02758e-4 | 1.76430e-4 | 6.49691e-6 | 0.251953 |
| G8 (raw log) | 2000 | 6.72e-5 | 8.35437e-3 | 1.04e-4 | 3.15060e-3 | 8.30e-5 | 7.53e-5 | 7.69e-6 | 0.206 |
| G9 | 2000 | 0.177734 | 0.0525795 | 0.0356445 | 0.0490899 | 0.0495605 | 2.38037e-3 | 9.77516e-6 | 0.220703 |

G5、G6：没有逐 step loss，不能补写数字。

### 2.9B

| 训练 | steps | first | mean | median | tail μ | tail med | last | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S1 | 6000 | 2.18750 | 0.0645477 | 9.35793e-6 | 2.08475e-6 | 1.69501e-6 | 2.23517e-6 | 4.09782e-7 | 3.34375 |
| S2 | 2000 | 3.48438 | 0.183004 | 1.73187e-3 | 0.0141621 | 5.63860e-5 | 1.74046e-5 | 8.64267e-6 | 3.48438 |
| S12 | 1467 | 4.71875 | 0.241036 | 2.46048e-4 | 1.28872e-4 | 3.31402e-5 | 2.92969e-3 | 1.12057e-5 | 4.96875 |
| S19 | 2000 | 4.75000 | 0.177594 | 1.05858e-4 | 7.54532e-5 | 1.97887e-5 | 1.09673e-5 | 5.78165e-6 | 4.75000 |
| S25 | 2000 | 2.54688 | 0.298553 | 0.0321045 | 0.167184 | 7.62939e-4 | 0.396484 | 8.34465e-6 | 3.70312 |
| S27 | 2000 | 2.39062 | 0.149588 | 5.26905e-5 | 2.32807e-5 | 1.00732e-5 | 4.52995e-6 | 2.32458e-6 | 3.21875 |
| S31 | 2000 | 2.45312 | 0.195676 | 2.91443e-3 | 0.0284580 | 1.18732e-4 | 2.71797e-5 | 6.97374e-6 | 3.82812 |
| S54 | 2000 | 2.17188 | 0.266402 | 0.0417480 | 0.167160 | 1.11771e-3 | 1.15625 | 1.60933e-5 | 3.43750 |
| S61 | 2000 | 3.23438 | 0.189536 | 6.96182e-4 | 6.08337e-3 | 4.24385e-5 | 3.33786e-5 | 4.64916e-6 | 3.25000 |
| S67 | 2000 | 2.12500 | 0.131057 | 1.28269e-4 | 7.49344e-5 | 3.43323e-5 | 3.95775e-5 | 4.14252e-6 | 4.37500 |
| S70 | 2000 | 1.99219 | 0.138313 | 1.54972e-4 | 5.16927e-4 | 4.07696e-5 | 1.13964e-4 | 5.33462e-6 | 3.00000 |
| S71 | 2000 | 2.07812 | 0.134079 | 1.72615e-4 | 1.50404e-3 | 3.42131e-5 | 2.59876e-5 | 3.01003e-6 | 3.04688 |

### 观测到的最佳配置

| 口径 | 训练 | LR init → final | train/dev | 最终 train loss | tail-100 mean | 结论 |
|---|---|---:|---:|---:|---:|---|
| 13.3B 最低 loss | Stage2 | 3e-5 → 6e-6 | 640/96（6.67:1） | 3.7103891372680664e-6 | 5.25057315826416e-6 | 仅代表 Stage2 route-boundary continuation 数据上的最低训练 loss |
| 13.3B 下游已选 general profile | G3 step 2000 | 2e-5 → 2e-6 | 2000/480（4.17:1） | 1.5926361083984375e-4 | 1.714348793029785e-4 | G3 ablation `status=selected`，也是当前 general Executor profile |
| 2.9B 最低 loss | S1 | 2e-5 → 2e-6 | 6000/750（8:1） | 2.2351741790771484e-6 | 2.0847469568252564e-6 | 仅代表 S1 短标签训练集拟合 |

2.9B 没有“通过最新 dev gate 的 tuned-state 最优配置”。S70 与 S71 的 500/1000/1500/2000 四个 checkpoint 全部未通过预注册的 accuracy ≥ 0.96、macro-F1 ≥ 0.96、minimum recall ≥ 0.90；因此当前服务保持 zero state。

如果目标是下一轮受控 LR 搜索，现有 run 不能证明全局最优，因为 LR、数据集、初始化 state、样本数同时变化。必须固定同一 dataset、同一 train/dev、同一 parent state 与同一评价阈值后，再比较 LR；不能从跨数据集最终 loss 反推通用最优 LR。

### Loss 的正确解释

- S1/S19/S27/S67 等尾部 loss 很低，说明短目标标签在训练集上被拟合；不等于能完成完整 agent 项目。
- G9 尾部均值和中位数都约 0.05，属于没有稳定收敛。
- S25/S54 尾部均值约 0.167，且最终 step 很高，属于明显不稳定。
- S2/S31/Stage5/Stage6/Stage7/G4/G7/G8/S61/S71 的尾部中位数低、均值高，说明仍有稀疏难例尖峰，不能用最后一个低 loss 掩盖。
- 所有纯 state JSONL 只有 `loss/t_cost/kt_s`，没有 `eval_loss`。S15 等 head 实验存在 dev loss，但它不是 state optimizer 的 dev loss。

## 7. 数据是怎么做的

### 7.1 统一流水线

```text
历史失败/固定协议/工具 schema/真实 Harness 轨迹
  -> 确定性 generator 生成语义 family 与对照组
  -> controller replay 或协议校验得到目标 action/label
  -> 按 semantic family 切 train/dev/test
  -> 精确去重 + family 隔离 + n-gram/cosine 相似度审计
  -> tokenizer/ctx/BOS/target_suffix mask 预检
  -> 固定 manifest（来源、版本、用途、脚本/文件 hash、计数）
  -> peft=state 训练
  -> 下游准确率、边界、保留集和真实 Harness 回归选 checkpoint
```

关键点：绝大多数训练样本不是由强模型自由生成答案，而是由固定 generator、协议标签、controller replay、历史失败/残差构造。当前数据仍以合成/重放/对照数据为主，不是由大量完整真实项目执行日志直接形成。

每行只监督最终目标后缀：历史 request、persistent history、工具观察可以作为输入，但不应进入 loss。Round1 权威审计为 2200/2200 目标精确匹配，历史 assistant supervised tokens 为 0。

### 7.2 34 个数据目录的来源与用途

#### A. 早期 action lane（2）

| 数据 | 规模 | 做法 |
|---|---:|---|
| `action_state_tuning_v1` | 1220 train / 244 dev | 20 seeds、120 semantic families、480 trajectories，第一阶段 action-lane 合成与重放 |
| `action_state_tuning_round1_2k_v1` | 2000/200 | 从 1321 条轨迹、13 类实际 Harness failure signature 扩展；protocol correction/no-progress/observation-binding/coverage/completion/privacy 六簇；controller replay；固定 5-gram cosine holdout |

#### B. Stage 残差递进（10）

| 数据 | 规模 | 来源/目标 |
|---|---:|---|
| Stage1 selector | 500/79 | Round1 dev 残差中 79 个 selector case、77 个错误 outer call，修 selector 协议 |
| Stage2 route boundary | 640/96 | 修 structured connector/web/local dependency 顺序边界 |
| Stage3 natural route stop | 1400/176 | 修 route transfer、natural connector、ordinary web、privacy/local-first 与 stopping |
| Stage4 balanced boundary | 1140/240 | 对 online/connector 过校准加 hard negatives，保留安全/停止边界 |
| Stage5 route stop | 1220/240 | 加 success completion、GitHub connector residual、web counterfactual 与 local anchors |
| Stage6 final balance | 1300/240 | 联合恢复 local-first 与 stopping，抑制 pre-evidence completion |
| Stage7 factory contrast | 2000/400 | 500 个 contrast groups，修 evidence-phase 泄漏、web/connector surface narrowing |
| Stage8 mutation stop | 2000/400 | 从 mutation success、idempotent repeat、verify evidence、investigate scope 构造 stop 对照 |
| Stage8 adaptive round2 | 1800/400 | 只扩充 round1 固定评估中低于阈值的 lane，并保留 matched contrasts/anchors |
| Stage8 adaptive round3 | 1700/400 | 用 round2 固定评估继续扩残差；阈值 0.95，固定 anchor 数；未发现对应 state loss |

Stage8 三套数据当前只有数据/评估资产，没有纳入上面的已执行纯 state loss 清单。

#### C. 13.3B Executor 专用（8）

| 数据 | 规模 | 来源/目标 |
|---|---:|---|
| Executor v2 | 2000/480 | 独立 selector 架构下，覆盖 24 operations 的 first-action/completion 数据 |
| Executor v3 request-last | 2000/480 | request-last 输入消融与 Executor state tuning 输入 |
| G3 multistage | 2000/480 | request-last 多阶段 Executor 初始 state |
| G4 true workflow | 2000/480 | frozen true-workflow generator；完整 immutable request |
| G6 network recovery | 2000/480 | task-level network action 与精确 protocol-rejection recovery |
| G7 network retention | 1200 | 修 network profile workflow retention，同时保留已正确 network 行为 |
| G8 engineering retention | 2000 | 复用 frozen G4 workflow generator，修工程任务 retention |
| G9 stable schema contrast | 2000 | 复用 frozen G4/G8 helper，做 stable schema 对照与正确行 anchor |

G5 没有新数据目录：它从 G3 step 2000 state 继续，在 G4 true-workflow 数据上训练。

#### D. 2.9B Selector 专用（14）

| 数据 | 规模 | 来源/目标 |
|---|---:|---|
| S1 broad state | 6000/750 | 单 profile selector 初始 state 的宽覆盖基线 |
| S2 residual | 2000/276/250 | 失败残差与 head/state 对照；test 隔离 |
| S12 gate | 1467/275 | serving-parity function/gate state |
| S19 connector/function | 2000/926 | CONNECTOR 690 vs OTHER 1310 的 train；function pair 边界 |
| S25 current Harness | 2000/276 + 250 excluded test | 当前 Harness 输入协议下的 state 消融 |
| S27 persistent trajectory | 2000/500 + 500 excluded test | 带 persistent history 的 trajectory |
| S31 true trajectory | 2000/500 + 500 excluded test | production-shaped true trajectory；25 类均衡，短 `SelectorLabelV3` 目标 |
| S54 multistage | 2000/500 | V4 request-last 多阶段 25 类 selector |
| S61 transaction continuation | 2000/500/500 | V7 continuation/final boundary + 25 类 retention |
| S65 lexicon diverse | 2000/500/500 | 去 split-specific lexicon shortcut；只有数据，未发现独立 state loss |
| S67 V2 contract | 2000/500/500 | CurrentDirectStageV2 的 exact 25-class operation selection |
| S68 semantic boundary | 2000/500/500 | 修 5 类已审计语义边界；只有数据，未发现独立 state loss |
| S70 uniform | 2000/500/500 | 25 labels × 80 train，zh/en 均衡；dev/test 每类 20；目标约 9 tokens |
| S71 diverse boundary | 2000/500/500 | 每 label-language 4 semantic cores × 10 rows；替换 S70 重复核心；新 sealed test |

S70/S71 的目标本质是 `SelectorLabelV7: <tool>` 这样的 7–9 token 短标签。它们适合训练“工具类别偏置/边界”，不承担 planner、检查、重规划或完整项目生成能力。

### 7.3 数据完整性措施

- generator 与数据 manifest 固化脚本路径和 SHA256；较新的数据同时固化冻结父 generator/helper SHA256。
- train/dev/test 按 semantic family 隔离，不只做随机逐行切分。
- 检查 exact prompt duplicate、family overlap、target parse、target truncation。
- Round1 使用 byte 5-gram cosine，阈值 0.75，观测最大 holdout 相似度 0.2003。
- S71 对 S70 的生成集最大相似度 0.8956，预注册阈值 0.95；ladder 最大 0.2659。
- S70 原 test 被隔离，S71 visible dev 与新 sealed test 分开。
- 训练前验证 BOS、tokenizer、最大 token、ctx 与 target_suffix mask。

## 8. 当前最关键的缺陷

1. **2.9B tuned state 没有在线使用。** 当前 profile-id 是 zero；所以 S67/S70/S71 等训练是否有效，前端链路无法体现。
2. **训练目标和 agent 能力错位。** 2.9B 多数数据只预测一个短 tool label；低 loss 只能证明分类后缀拟合，不能证明 planner→执行→检查→重规划。
3. **纯 state 训练没有 dev loss。** 所有 JSONL 只有 train loss、耗时和吞吐；checkpoint 选择依赖另跑 downstream eval，无法从同一训练轨迹判断泛化。
4. **数据以合成/重放为主。** 真正完整项目的多文件执行、错误恢复、跨 15+ progress 的 state 轨迹占比不足，和用户要测的项目实现能力存在明显分布差距。
5. **尖峰被最后一步掩盖。** 多个 run 的 tail median 很低但 tail mean 高两个数量级，说明难例仍失败；当前若只展示 final loss 会误判。
6. **训练留档不完整。** G5/G6 缺 loss，G4/G8 只有原始 log，S19 缺 pretrain manifest；不能形成统一可重放训练账本。
7. **Stage lineage 不直观。** Stage2–Stage6 都从 Stage1 step 500 分叉；Stage7 从 Stage4 继续。若只按编号理解为线性递进，会错误归因。
8. **数据资产多于被使用资产。** Stage8、S65、S68 等已生成但没有纯 state 训练/部署闭环，数据演化与线上 profile 之间缺统一 registry。

## 9. 建议的统一登记结构

每个 state run 以后固定一个目录并一次性写齐：

```text
run_manifest.pretrain.json
dataset_manifest.snapshot.json
loss.train.jsonl
loss.dev.jsonl
checkpoint_validation.json
downstream_eval.json
deployment_attestation.json
```

`deployment_attestation.json` 必须明确 model SHA、state profile SHA、profile id、selector head SHA、capabilities 与启动命令。这样可以区分“工程支持 state”“checkpoint 存在”“服务加载 state”“请求实际使用 state”四件不同的事。

## 10. 复核入口

- 机器扫描脚本：`temp/inventory_state_tuning_20260831.py`
- 数据 manifest：`data/datasets/*/manifest.json`
- 训练配置：`data/experiments/**/*manifest*pretrain*.json`
- 逐 step loss：`data/experiments/**/loss_data.jsonl`、`remote_loss_data.jsonl`
- G4/G8 loss：对应 checkpoint 目录的 `EXE_G4_TRAIN.log`、`EXE_G8_TRAIN.log`
- 13.3B checkpoint 校验：`run_exe_g6_state_training_remote_checkpoint/CHECKPOINT_VALIDATION.json`
- 2.9B checkpoint 校验：S70/S71 checkpoint 目录的 `CHECKPOINT_VALIDATION.json`
