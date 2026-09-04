# S66 Selector 多词根 Soft-MoE 消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 实验编号：`NET-SEL-2P9-S66-DIVERSE-SOFT-MOE-ZERO-STATE`
- 设备：仅物理 GPU0

## 固定目标

在不丢失发布 S60 工具能力的前提下恢复多阶段续作。2.9B RWKV 每次仍只提取一次 zero-state Hidden(mean+last)；小分类器输出一次完整 25 类 raw logits。Planner/Executor 职责、25 类名称/描述、V7 问题末端与 state 身份均不变。

S65 已把原先单一 split 词根改为 train/dev/test 的 16/8/8 个互斥词根池；每个 focus 场景在 train 覆盖全部 16 个词根。cases SHA `28cbec6cce980e1835ff04529a6b6f555557e3514f8c9f259b65ee6478a23830`，manifest SHA `dc1c166dbad6f5283a6cfc4571b6e17ca107d329b12456d330e18eabfa4bd582`。

## 冻结专家与模型公式

- old expert：发布 S60 h64，SHA `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`；永久冻结。
- continuation expert：S62-U1 h64，SHA `f764841340aeb65b674f8fef81a016f351db3c25d78470f6a8dfdf2c290b12af`；它在任何 locked test 打开之前由 dev 固定，永久冻结。
- 两个 expert 使用相同 zero-state feature 与 S60 normalization。

唯一可训练部分是独立 gate MLP。raw logits 固定为：

`old_logits + sigmoid(gate_logit) * (continuation_logits - old_logits)`

这是单个确定性 soft mixture head 的 raw forward，不做投票、阈值切换、关键词规则、类别屏蔽或输出修补。完整 25 logits 先记录再 argmax。

## 固定 train/dev

- gate train：S60 完整 train 13,143 行，target=0；S65 focus train 1,000 行，target=1。两个域等质量，域内类别等质量。
- dev：S60 完整 dev、S65 完整 dev；另把已知 S61 dev 作为跨数据分布回归，不能单独用于挑有利 candidate。
- S60/S61/S65 test 均不由 runner 读取；S65 locked test 只在唯一 candidate 与通用 runtime 冻结后打开一次。
- S65 zero-state feature manifest 在提取完成后以显式 SHA 参数冻结；特征必须记录 test pre-parse skip=500、test labels accessed=0。

## 固定候选

gate 为 `5120 -> h -> 1`，GELU(tanh approximation)+LayerNorm(eps 1e-5)+dropout 0.05。loss 为 balanced BCEWithLogits 加权重 1.0 的 confidence hinge：target=1 要求 logit `>=6`，target=0 要求 logit `<=-6`。

| ID | hidden h | LR |
|---|---:|---:|
| `S66-M1` | 64 | `3e-4` |
| `S66-M2` | 128 | `3e-4` |
| `S66-M3` | 256 | `3e-4` |

batch 256、AdamW weight decay `1e-4`、cosine 120 epoch、seed 1066、确定性 cuBLAS。候选内最早过门；候选间按 M1→M2→M3。不得看到 dev 后增加数据、hidden、loss、LR 或候选。

## 固定门槛

候选必须同时满足：

1. S65 dev 与 S61 dev 各自 overall `>=0.96`、focus `>=0.95`、continuation/final `>=0.97`、focus 支持类 recall `>=0.90`；
2. 两套 dev 相对 old expert 的 focus net rescue `>0` 且 changed decisions `>=1`；
3. S28/S39/S52/S53/S55 原绝对门全部通过；
4. S60 dev 中 old expert 原正确行回归数=0、每个 source accuracy 不低于 old；S60 train teacher argmax agreement=1.0；
5. JSON artifact 重放 8 行 raw logits误差 `<=0.005` 且 argmax 一致；
6. 每次请求 RWKV hidden extraction=1；rule gate、text generation、sampling、logit postprocessing、raw 修改均为0。

若 continuation expert 本身在 S65 dev 不足以达到 focus 0.95，或所有 gate 失败，本实验直接拒绝，不用 test 修改 expert。若通过，先实现通用 Soft-MoE artifact/service 并补齐单元、边界、身份测试，再打开 S65 locked test。
