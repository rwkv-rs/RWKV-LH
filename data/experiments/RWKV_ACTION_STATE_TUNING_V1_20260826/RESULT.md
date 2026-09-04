# RWKV Action State Tuning v1 结果

日期：2026-08-26（Asia/Shanghai）

## 结论

第一次微调的 Phase A 数据已生成，并达到预注册的训练包导出条件。

- 480 条 trajectory，480 accepted，0 rejected。
- train/dev 为 400/80，按 120 个 semantic family 隔离；无 family 跨 split。
- 1464 个 progressive G1i stage：1220 train / 244 dev。
- 720 个 selector target，744 个 direct-call target。
- 24 个 protocol malformed attempt 仅保存在 rejected/filter 数据，不进入正向 SFT。
- 隐私用例的 retrieval backend execution 总数为 0。
- 全项目回归：`265 passed in 56.44s`。

训练包：`data/datasets/rwkv_lh_action_state_tuning_v1/`

## 与 RWKV-state-factory 的结合方式

本轮复用了 `/home/chase/GitHub/RWKV-state-factory` 的工程方法：

1. 私有 oracle 与公开 instruction/environment 隔离；
2. 候选先做静态检查；
3. 在冻结环境中 fresh replay；
4. 只导出 verifier 全通过的正样本；
5. 失败只作为 filter/preference 候选；
6. 先按 semantic family 切分，再做污染/多样性闸门；
7. 输出 manifest、来源摘要和可重复验收入口。

没有复用 Web Retrieval factory 的任务 schema、网页 verifier、renderer 或 token-Jaccard
污染实现。Action 数据的 Observation、Gate、工具合同和 prompt 字节均由 RWKV-LH 当前
Controller/Harness 产生。

首批使用 State Factory bootstrap 同类的确定性私有 oracle，不让强模型充当 operation/params
真值生成器。因此已配置的强模型 API 本轮没有被调用，也没有 credential 进入数据或审计文件。
后续递归扩展时，强模型可以生成新的表面候选，但仍必须通过本轮相同 verifier 才能进入训练集。

## 数据构成

### trajectory

- 20 个系统行为 seed，每个 24 条；
- 每个 seed 6 个 entity family，每个 family 4 个变体；
- 每个 family 内中文 2 条、英文 2 条；
- 每个 seed 的第 6 个 family 固定进入 dev；其余进入 train。

### stage

| target operation | stage 数（selector 与 direct 合计） |
|---|---:|
| `read_file` | 312 |
| `read_json` | 192 |
| `web_search` | 192 |
| `connector_lookup` | 192 |
| `final_answer` | 240 |
| `list_directory` | 96 |
| `calculator` | 48 |
| `date_diff` | 48 |
| `current_time` | 48 |
| `patch_json` | 48 |
| `check_command` | 24 |
| `run_command` | 24 |

`ST-ACT-016` 的 24 条纠错 target 只有 direct-call stage，因为当前 progressive runtime 在
协议拒绝后保留已经披露的 contract，不要求重新 selector。这是实际 Controller 行为，不是合成器
仿写。

### 上下文长度

使用当前项目 token counter 对 1464 个 `prompt + target` 统计：

- min：1079 tokens；
- p50：1431；
- p95：4504；
- max：6341；
- mean：2300.12。

因此训练 `ctx_len` 至少应覆盖 6341；建议第一轮使用 8192。部署仍可维持 16384。

## 回放与 verifier

每条候选均创建一次性 workspace，并通过当前以下组件真实回放：

- `LongHorizonController`；
- `LongHorizonModel`；
- progressive `ModelSession`；
- authoritative `ActionHarness`；
- 冻结 `.invalid` external evidence backend；
- 当前 Network Gate 与 provenance policy。

验收包括 operation/完整 params、authoritative defaults、真实 action 数、Observation literal
binding、inspect→mutate→fresh read、Gate typed rejection、provider unavailable、协议纠错、
完成决策、零进展重复和每个 generation prompt/target 一一对应。

其中发现一个生成期 verifier 缺陷：最初把 JSON 修改前后参数相同的两次 `read_json` 误判为重复。
根因是重复检查忽略了中间 `patch_json` 带来的状态变化。修正为只拒绝“无中间状态变化的相邻完全
相同动作”，随后重新检查全部同类场景。JSON transaction 的 fresh read 保留并验证更新字段与未
指定字段。

## 污染与多样性

冻结评价集仍是 ECRA route120 + canonical RWKV-E2E-90，共 210 条 request。

- exact holdout overlap：0；
- 最大 holdout UTF-8 byte 5-gram cosine：`0.3289936294775451`；
- 内部 exact request duplicate：0；
- 最大跨 semantic-family cosine：`0.7296801606997213`；
- 固定阈值：严格 `< 0.75`；两项均通过。

训练候选中没有真实联网、真实 secret、真实 API key 或真实 private key。隐私用例只使用
`SYNTH_SECRET_DO_NOT_EGRESS_` 前缀的合成哨兵。

## 导出文件

- `rwkv_state_tuning.train.jsonl`：1220 条官方 `{"text":"..."}`；
- `rwkv_state_tuning.dev.jsonl`：244 条官方 `{"text":"..."}`；
- `stage_sft.train.jsonl` / `stage_sft.dev.jsonl`：含 prompt/target 边界的审计格式；
- `semantic_candidates.jsonl`：公开候选语义；
- `private/oracle_trajectories.jsonl`：私有 oracle；
- `validation.jsonl`：480 条逐 trajectory 验收；
- `rejected_attempts.jsonl`：24 条 malformed negative；
- `manifest.json`：全部数据、生成器和 holdout 摘要。

数据包合计 41,869,220 bytes。每个训练产物的 SHA-256 和字节数均在 manifest 中登记。

## 验证命令

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/generate_rwkv_action_state_tuning_v1.py --validate-existing
uv run pytest -q -s tests/test_action_state_tuning_dataset.py tests/test_state_tuning_seed_dataset.py
uv run pytest -q -s
git diff --check
```

结果：

- dataset/seed targeted：6 passed in 7.04s；
- project full suite：265 passed in 56.44s；
- `git diff --check`：通过。

## 第一轮训练建议

1. 先以 `rwkv_state_tuning.train.jsonl` 转 binidx，dev 单独转换；禁止拼接 private oracle。
2. 使用与当前部署严格同构的 RWKV-7 13.3B 基座、词表、`n_layer`、`n_embd`。
3. RWKV-PEFT 使用 `--peft state --op fla`；第一轮 `ctx_len=8192`。
4. 若训练器支持 response loss mask，使用 `stage_sft.*.jsonl` 的 `prompt`/`target` 边界，只监督
   selector/direct/final target；否则官方 `text` 文件可直接进入标准 binidx 流程。
5. 不以 train loss 判定完成；训练后必须重新运行 ECRA route canary/route120、E2E-90 以及
   privacy/protocol/provider-unavailable 定向回归。

这 480 条足够进行第一次 Phase A state-tuning，不等于完成 1824 条建议全量。第一轮结果用于判断
各 behavior family 的增益与退化，再按固定 verifier 递归扩展缺口，而不是修改评价口径。

