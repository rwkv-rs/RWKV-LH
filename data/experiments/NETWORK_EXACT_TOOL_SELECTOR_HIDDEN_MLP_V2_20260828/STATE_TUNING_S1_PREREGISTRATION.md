# Selector 2.9B single-state S1 — 预注册

## 触发条件与目标

- 冻结时间：2026-08-28（Asia/Shanghai），任何 S1 训练前登记。
- S0 的 v2.4 合成 test 已通过；ECRA 45-case 固定回归未通过：last accuracy=0.511111、web recall=0.88、connector recall=0.05，mean accuracy=0.088889。
- S1 只检验一个独立的 Selector state-tuning profile 能否改善 2.9B 在同一最小输入协议上的工具语义表征。
- 不训练或修改 2.9B 权重，不生成 Selector 文本，不修改、截断、替换或删除任何 RWKV 原始输出。

## 固定训练数据

- 唯一来源为已经冻结的 `rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl`，SHA-256 为 `78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc`。
- 只使用原 train split 的 6000 行训练 state；原 dev split 的 750 行只导出用于训练契约检查；原 test split 的 750 行完全不进入 state 训练。
- prompt 等于原始 `rendered_input`，不添加 schema、工具结果、Executor 文本、workspace 内容或推理过程。
- target 固定为 `\nSelectorLabelV2: <exact-label>`；只对 target suffix 计算 loss，BOS=0。标签顺序与 25 类协议完全一致。
- ECRA 120 条均不进入训练、校准、early stopping 或 checkpoint 选择。45 条既有网络边界作为固定已知回归，不再称为未见 holdout。

## 固定训练参数

- base model：`rwkv7-g1i-2.9b-20260805-ctx16384.pth`，SHA-256 `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`。
- RWKV-PEFT 只训练 32 个 `blocks.<layer>.att.time_state`；从全零 state 初始化，不从 13.3B 或任何 Executor state 继续。
- n_layer=32，n_embd=2560，head_size=64，ctx_len=1024，micro_bsz=1，gradient accumulation=1。
- 6000 steps，1 epoch，shuffle=true，seed=830，BF16，DeepSpeed stage 1，FLA，gradient checkpointing=true。
- Adam 参数沿训练器默认 state-tuning 路径；lr_init=2e-5，lr_final=2e-6，cosine schedule，warmup=100，step_save=1000。
- checkpoint 选择固定为 final step 6000；除非其 key/shape/dtype/finite/loss 契约无效，否则不得按 ECRA 结果挑选早期 checkpoint。

## 固定 S0/S1 比较

- S1 checkpoint 必须正好包含 32 个 BF16 `time_state`，每个 shape `(40,64,64)`，全部有限且非零，并记录 SHA、训练 loss 与零状态 delta。
- 推理注入必须同时绑定 manifest SHA、profile ID 和 checkpoint SHA；默认 profile 仍为 zero。
- 同一固定输入以 zero/S1 各前向两次：同 profile 重放稳定，zero 与 S1 hidden 必须发生非零变化；不允许用文本生成证明 state 生效。
- 使用 S1 重新提取原 7500 行 last/mean hidden，并以与 S0 完全相同的 MLP 结构、seed、超参数、split、temperature 与评价代码训练两个新 head。
- 仍使用原 synthetic test 门槛与原 ECRA 45-case 门槛；不得修改阈值。S1 只有在 synthetic 全门槛和 ECRA 全门槛同时通过时才可接入。
- S1 达标即停止，不做 S2。S1 未达标时保留结果；只有出现明确阶段条件交互证据才允许预注册 S2，不能用多 state 掩盖语料/协议缺陷。

## 独立存储

- Selector S1 数据、checkpoint、profile manifest、hidden cache 与 head 均使用独立目录和 SHA。
- Executor 13.3B state、checkpoint lane 和任何生成会话都不读取或继承 Selector S1 state。

