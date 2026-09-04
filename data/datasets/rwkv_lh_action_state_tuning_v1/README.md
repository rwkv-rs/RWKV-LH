# RWKV-LH Action State Tuning v1

这是第一次可训练的 Action State Tuning Phase A 数据包，不是 Web Retrieval factory 数据。

- verified trajectory：480（train 400 / dev 80）
- progressive stage SFT：1464（train 1220 / dev 244）
- seed：20；semantic family：120
- 当前协议：progressive G1i；prompt 来自真实 Controller/ModelSession 回放。
- 网络：只使用冻结 `.invalid` evidence；生成过程没有真实联网。
- 隐私：只使用 `SYNTH_SECRET_DO_NOT_EGRESS_` 合成哨兵，Gate rejection 的后端执行数为 0。

## 训练文件

- `rwkv_state_tuning.train.jsonl` / `rwkv_state_tuning.dev.jsonl`：官方 `{"text":"..."}` 格式。
- `stage_sft.train.jsonl` / `stage_sft.dev.jsonl`：附带 trajectory、stage、operation 和摘要的审计格式。
- `semantic_candidates.jsonl`：公开候选语义；不含私有 prelude oracle。
- `private/oracle_trajectories.jsonl`：私有动作真值，只用于生成/验收，不应拼入模型 prompt。
- `validation.jsonl`：逐 trajectory 回放验收。
- `rejected_attempts.jsonl`：协议纠错的 malformed hard negative，不得作为正向 SFT。
- `manifest.json`：来源、摘要、固定口径与污染指标。

## 使用

先将 train/dev JSONL 转成 RWKV binidx。RWKV-PEFT state tuning 使用与部署模型严格匹配的
RWKV-7 13.3B 基座、词表、层数和 embedding 维度，并采用 `--peft state --op fla`。训练时不得
把 dev、private oracle 或 frozen holdout 混入 train。

本包 480 条属于 State Factory Phase A。完整建议量仍是 1824 条 verified trajectory；后续扩展
必须复用当前 Controller/Harness verifier 和 UTF-8 byte 5-gram cosine `<0.75` 污染闸门。
