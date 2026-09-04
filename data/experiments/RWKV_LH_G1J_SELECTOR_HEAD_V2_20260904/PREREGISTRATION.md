# G1J Selector Head v2 持久因果实验预注册

日期：2026-09-04（Asia/Shanghai）

## 目标与起点

- 源提交：`9abb43ec`。
- 只创建缺失的 `rwkv_lh_g1j_selector_intent_head_v2`；不训练、生成、加载或选择任何 StateTune。
- 基础模型：`rwkv7-g1j-2.9b-vllm-v1`。
- 原生权重 SHA-256：`966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239`。
- 服务 artifact 权重 SHA-256：`c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c`。
- 执行环境：WSL `UbuntuRecovered`，物理 GPU 0，UUID `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48`，NVIDIA GeForce RTX 5070 Ti 16,303 MiB。
- 推理引擎 revision：`67f0c5996c50dca0ad779da545cb491527de988f`。
- 输入协议：`rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1`。
- 轨迹模式：`persistent-causal-sequences.v1`；每个 sequence 从 zero role State 加同一个 bootstrap 开始，第二个 prompt 必须继承第一个 prompt 返回的 `_next_state`，sequence 之间重置。
- 状态作用域与线上一致：一个 sequence 等于一个 `(step_id, step_revision)`；不跨步骤、revision、Final 或角色继承 WKV。

## 固定数据

- 数据集 ID：`rwkv_lh_g1j_selector_persistent_head_v2`。
- 250 个 sequence，每个恰好 2 个 Selector prompt，共 500 行。
- 10 个语义 variant；variant `0-5` 为 train、`6-7` 为 dev、`8-9` 为 sealed。一个 sequence 不得跨 split。
- 固定 25 类顺序：23 个生产 operation、`final_answer`、`ABSTAIN`。
- 每类总计 20 行；train/dev/sealed 每类分别为 `12/4/4`，总计 `300/100/100`。
- 23 个 operation 使用一个固定有向语义环。每个 variant 中，每个 operation 各作为一次首动作和一次成功前驱后的第二动作，避免 Head 只学习“第一轮意图”或“沿用上一工具”：

```text
current_time -> date_diff -> calculator -> make_directory -> write_file
-> append_file -> remove_line -> replace_text -> read_file -> bind_evidence
-> file_digest -> copy_file -> move_file -> list_directory -> search_text
-> read_json -> patch_json -> write_json -> check_command -> run_command
-> delete_file -> web_search -> connector_lookup -> current_time
```

- `final_answer` 使用完成态 singleton eligible menu 的两轮 Final scope；`ABSTAIN` 使用无法唯一决定下一操作的两轮同 scope 恢复边界。
- operation 与 `ABSTAIN` 的 `stage_objective` 必须是当前生产 `GoalFrontierStateV1` 形状；`final_answer` 使用当前 `CurrentDirectStageV1` 终态投影。第二轮必须包含上一轮 Harness action或协议拒绝的有界事实。不得包含 target 字段、答案、参数建议或模型生成的理由。
- operation target 由上述固定环、完成态 singleton 合同或歧义边界合同机械生成；Strong Model 与旧 Selector 输出都不是 label authority。
- 相似度算法：`utf8-byte-5gram-cosine.v1`。只比较 source 的 `stage_objective,stage_role,progress,eligible_labels` 原始 UTF-8 串；train/dev、train/sealed、dev/sealed 最大值均须 `< 0.95`。生成后不得修改字段选择、阈值或算法。

## 固定特征

- 模型初始 State：zero，SHA-256 为 64 个 `0`；这不是 StateTune。
- 每个 prompt 只做一次 current-segment forward，同时取 final-layer real-token mean 与 last，按 `[mean,last]` 拼接为 5120 维 `float32`。
- bootstrap 只在 zero State 上计算一次并可字节级复用；每个 sequence 的第一轮继承 bootstrap State，第二轮继承第一轮 `_next_state`。
- feature manifest 顶层和 portable identity 都必须声明 `persistent_history_replayed=true`、`training_trajectory_mode=persistent-causal-sequences.v1`、sequence 数和长度分布。
- 只抽取 train/dev 400 行；sealed 的 source、prompt、token、feature、label 均不得被特征提取或 Head 训练入口读取。

## 固定 Head

- 结构：`Linear(5120,64) -> GELU -> LayerNorm(64) -> Linear(64,25)`。
- 标准化：只使用 train feature 的逐维 mean/std，std 下限 `1e-6`。
- 初始化：全新 Xavier uniform；seed `20260904`；禁止加载旧 Head 参数。
- 优化器：AdamW；learning rate `0.001`；weight decay `0.0001`。
- batch size `64`；epoch 固定 `200`；dropout `0.05`；temperature 固定 `1.0`。
- 只有一个候选，不 early-stop、不做网格搜索、不使用 dev 选 checkpoint 或调参；发布固定第 200 epoch。
- artifact 必须写入 Head ID、模型 SHA、输入协议、25 类顺序、feature protocol、zero profile 和持久轨迹身份，并通过依赖轻量 replay 与服务身份门。

## 固定门槛与后续测试

- 数据结构、类平衡、sequence 连续性、split 隔离、prompt renderer parity 和相似度审计全部通过。
- dev raw argmax accuracy 与 macro-F1 均 `>= 0.90`；每类 recall `>= 0.75`；第二位置 transition accuracy `>= 0.90`；`final_answer` 与 `ABSTAIN` 均不得误选。
- 若任一门槛失败，Head 标记为未通过且不写入 `.env.local`，不得改变参数或评价口径补跑。
- Head 通过后，只更新本机 Selector Head 文件 SHA 与逻辑 hash，保持 State profile 为 zero；先运行服务身份/父 State/argmax smoke，再使用既有固定 Agent Capability Ladder 运行工程基线。Ladder 结果只报告，不因结果修改本实验 Head。
- 所有源码、数据摘要、特征摘要、训练指标、服务 smoke 与 Ladder 结果写入本实验目录。
