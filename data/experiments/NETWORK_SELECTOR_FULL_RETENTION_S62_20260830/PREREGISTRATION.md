# S62 Selector 完整旧能力保留消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 实验编号：`NET-SEL-2P9-S62-FULL-RETENTION-ZERO-STATE`
- 设备：仅物理 GPU0
- 目标：在不增加 state 的前提下，让 S61 多阶段续作/纠错能力与完整 S60 旧工具能力同时过门。
- 非目标：不修改 Planner/Executor 职责，不让 13.3B 选择工具，不增加规则 gate，不屏蔽类别，不修改、删除、隐藏、重排或修复任何 RWKV hidden/logits/原始输出。

## 触发证据与根因假设

| 证据 | SHA-256 |
|---|---|
| S61 B0 zero-state fresh h64 | `75b84721b79493de199b925c3d4a4a778ea540efcb2042200a25144dd2fe59d9` |
| S61 B1 受约束迁移消融 | `e2c3f1dfb0716abd6981069294413840f025099be5b037f6eec579d0a807c16d` |
| S61 state step500 C/D | `4d95cc1ebf3773f3e6453fceb4c8d2c77363f33a808375ee2291417ea764c80e` |
| S61 state step500 features | `be06f3797af1f283a701d9c0db9f3e6fad66295d6d8649e19edb3f3c29b7600b` |

B0 用 1,000 条 focus + 1,000 条 S60 retention 训练时，S61 focus 达到 `1.000`，证明冻结 2.9B Hidden(mean+last)+h64 能分离新边界；但 S39/S52/S53/S55 明显退化。B1 只在同一 1,000 条 retention 上保持 teacher 几何，旧能力保住但 focus 最高仅 `0.532`。state step500 的 D 臂再次得到 focus `1.000`、旧能力坍塌，而固定旧 head 的 C 臂 focus 仅 `0.448`。

预注册根因假设：失败主要来自 head 更新时旧分布只覆盖 1,000 条抽样 retention，而不是需要更多 state。S60 已存在完整 train 的 13,143 条冻结 zero-state 特征，因此本轮只扩大 head 的旧能力覆盖，不生成新数据、不修改 state，也不访问任何 test。

## 冻结输入

| 输入 | SHA-256 |
|---|---|
| S61 cases | `0ef53380f6dad937dd8c05237d77fa996ca73f12af24927ac754f80fcb6b9c98` |
| S61 zero-state train/dev feature manifest | `ad70695ec2cd79614ba5e8d0c16afa1f84365bc38675b7c58bda15ec208bd451` |
| S60 cases | `3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf` |
| S60 full train/dev feature manifest | `be329509a245d6ae387e0ce8813f1905320ed4a9b099d0ea25d8a3cd3b83b419` |
| S60 released h64 head file | `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441` |
| S60 released logical head | `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e` |
| S61 parent preregistration | `53f5ae53f2459d760631aa93f9cf7fd693ee43274dc767455b9634fdfda5d8b0` |

## 固定训练与候选

训练集只由以下两部分组成：

1. S60 完整 train：13,143 行，25 类，覆盖 S28/S39/S52/S53/S55；
2. S61 focus train：1,000 行，覆盖续作、mutation、check、final 与恢复边界。

S61 retention 不重复加入，因为它的 source row 已属于 S60 train。S61 dev 500 行与 S60 dev 2,571 行只用于选择；S61/S60 test 均保持关闭。

所有候选：

- 仍为 5120 -> h64 -> 25 的单隐层 MLP；
- 从同一个已发布 S60 head 全参数初始化，并冻结 S60 head 的 feature mean/std；
- 监督 loss 中 S60 与 S61 focus 各占 0.5，总质量在各域内按支持类别等质量；
- 对全部 S60 train 加入权重 `1.0` 的 S60 teacher-logit KL，teacher 不参与 S61 focus；
- batch 256、weight decay `1e-4`、dropout `0.05`、cosine schedule、最多 120 epoch、patience 30、seed 1062、确定性 cuBLAS；
- zero state 固定，不训练或加载 S61 state；原始 25 logits 直接 argmax，不做后处理。

预先固定三个候选：

| ID | 可训练参数 | LR |
|---|---|---:|
| `S62-U1` | 全部 h64 参数 | `1e-4` |
| `S62-U2` | 全部 h64 参数 | `3e-4` |
| `S62-U3` | 全部 h64 参数 | `1e-3` |

候选间优先选择较低 LR，再选择最早过门 epoch。不得根据 dev 结果新增候选或改变 loss/门槛。

## 固定门槛与后续

每个候选必须同时满足父 S61 的全部 dev 门：overall `>=0.96`、focus `>=0.95`、continuation/final `>=0.97`、focus 每个支持类别 recall `>=0.90`、相对 A focus net rescue 为正，并且 S28/S39/S52/S53/S55 原 gate 全过、任一 source accuracy 相对发布 S60 head 回归不超过 1 个百分点。

只有选出唯一 dev candidate 后才允许：

1. 打开 S61 test 与 S60 locked test，一次性评估；
2. 重跑三例 bugfix canary、十例 Agent Capability Ladder 与联网检索质量；
3. 与 S61 state 消融比较。若 zero-state S62 已过门，则根据最小 state 原则优先 zero state；state 只有带来父协议要求的额外真实闭环增益才可启用。

报告必须保留每个候选全部 epoch 指标、confusion、raw logits、changed/rescued/regressed IDs、GPU0 身份与 test 隔离证据。若全失败，如实拒绝，不做控制器特判。
