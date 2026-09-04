# Network Selector S67 Global + Request-Tail Fusion Ablation V1 — 预注册

日期：2026-08-31（Asia/Shanghai）

## 问题与固定证据

- S67 one-forward request-tail-only 的 `zero/ST500/ST1000/ST1500/ST2000` 已全部被固定门拒绝；最佳 accuracy 仅为 `0.850`，说明只看末端请求会丢失工具描述、阶段与进度形成的全局状态。
- S67 whole-step head geometry 的全部候选也未过门；最佳为 `ST1500 + H2X128`，accuracy `0.926`、macro-F1 `0.9223809507853242`、最低类别 recall `0.40`。
- 这两个已完成实验只用于确定本实验结构，不在本实验运行后修改。本实验仍为诊断，S67 test 已因既有隔离事故永久退役，不得读取、解析或评分。

固定上游结果：

| 输入 | SHA256 |
|---|---|
| S67 cases.jsonl | `0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859` |
| S67 manifest.json | `0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46` |
| head geometry result | `026d23cf38d9ad159f8088843dff73d37df792be74cec9f013f67a0f6bdf94b6` |
| tail-only sequence result | `3d1fead0c99147e8d5d22a0e8db0344195f91275c91d9e9a4572141e85abfc9a` |
| frozen S67 base trainer | `16b5e8ff5ed16d17257880a29f0f0bcf2eaa66eaca150476238472196c4da7d4` |

## 固定候选与输入

只比较两个 state，顺序固定且两者都必须运行：

1. `zero`：无 state tuning；whole manifest `6bc00c202765b6621370e618a7a66244c52232b1e5027c29c86e78ae78d2b64c`，tail manifest `69c8b42db1da3f84c96ef098429f6ca6fcc24d5a75298e7b8dad13142024c18c`。
2. `ST1500`：当前 whole-step geometry 最佳的已编号 state；whole manifest `8cb6e5cbbd7fc90f49af8cd0b66cab5d4b073138e9c7164364356eff920ca6f9`，tail manifest `e85aa2b6d105c354a9a78aab926d81a5305d1c8b261ea67583aabc755291a051`。

每条样本只使用同一次 current-step forward 已保存的三个 view：

- `global_mean`：完整 current-step hidden mean；
- `tail_mean`：末端 `complete_requirement` 请求区间 hidden mean；
- `final_last`：完整 current-step final hidden。

whole 与 tail 的 `final_last` 必须逐元素 bitwise 相等；不相等立即使整个实验失败。融合向量不覆盖、不修复、不截断、不重排任何 RWKV hidden 或 raw output。既有特征已经完成 2500/2500 token、final hidden 和 final state 一致性检查，本实验不再调用 RWKV，不生成文本，不采样。

## 固定模型

唯一 head 为 `DualViewGatedH128`，不在运行后增加备选结构：

1. `global = LayerNorm(GELU(Linear([global_mean, final_last], 5120 -> 128)))`；
2. `tail = LayerNorm(GELU(Linear(tail_mean, 2560 -> 128)))`；
3. `gate = sigmoid(Linear([global, tail], 256 -> 128))`；
4. `fused = LayerNorm(global + gate * tail)`；
5. `fused = fused + Dropout(0.05)(GELU(Linear(fused, 128 -> 128)))`；
6. `logits = Linear(fused, 128 -> 25)`。

三个输入 view 分别只用 2000 条 train 计算 mean/std；dev 不参与归一化统计。初始化为 Xavier uniform/zero bias，LayerNorm weight=1/bias=0。

## 固定训练与评价

- 数据：train `2000`、dev `500`；test 必须在 JSON parse 前跳过，读取/标签访问/评分均为 `0`。
- seed：复用 frozen S67 trainer 的 `SEED`。
- optimizer：AdamW，lr `1e-3`，weight decay `1e-4`。
- batch `256`，max epoch `160`，CosineAnnealingLR `T_max=160`，gradient clip `1.0`。
- checkpoint 选择：最大化 `min(accuracy/0.96, macro_f1/0.96, min_recall/0.90)`，再依次按 accuracy、macro-F1、较早 epoch；连续 `30` epoch 无提升后停止。
- 统一算法：25 类 exact argmax confusion matrix；报告 exact accuracy、支持类 macro-F1、支持类最低 recall，不使用主观相似度。
- 通过门：accuracy `>=0.96`、macro-F1 `>=0.96`、每类 recall `>=0.90`，三者同时满足。
- 不允许后处理 logits、规则修正、ensemble、重采样、修改阈值或修改评价口径。

## 固定选择规则

- 两个候选都通过：选择 `zero`，因为它使用最少 state。
- 仅 `zero` 通过：选择 `zero`。
- 仅 `ST1500` 通过：选择 `ST1500`，并把 state tuning 记为必要。
- 全部失败：本结构拒绝，不选择发布候选；只能记录固定门比率最高者作为后续诊断入口。

即使 S67 通过，也只能进入独立预注册 S68 locked test、旧能力 retention、artifact/service parity 与真实 Harness canary，不能直接发布。

## 运行约束

- 仅 WSL `UbuntuRecovered`、`uv`、物理 GPU0（UUID `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48`）。
- 不停止、不替换远端 `rwkv-8222:18070` 产品服务；不占用用户 GPU1/2。
- 输出写入新的 staging 目录，完成后原子改名；已有输出时拒绝覆盖。
- 保存训练历史、head state、逐样本 raw logits、完整指标与所有输入/输出 SHA256。
