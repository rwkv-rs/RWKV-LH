# S64 Selector 冻结基线 + 学习式门控残差消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 实验编号：`NET-SEL-2P9-S64-GATED-RESIDUAL-ZERO-STATE`
- 设备：仅物理 GPU0

## 目标与架构边界

保持现有职责架构不变：strong model 只做 Planner/Reviewer；2.9B RWKV 只做一次 Hidden(mean+last) 提取并选择 25 类 operation；13.3B 只接收已选 schema 后生成参数/推进/总结。Selector 继续使用 zero state，不增加第二次 RWKV 调用、规则路由、关键词 gate、类别屏蔽或 Controller 补偿。

S62 证明单 h64 可把 S61 focus 做到 0.96–1.00，但出现旧函数漂移；S63 用参数插值和功能信赖损失保护单路径时，focus 最高仅 0.896，仍有旧 dev 回归。S63 结果 SHA-256：`9bdc90f23e6b39cf0a91b87e400931c9f3b38c532cb8fc098ab46585a3b77149`。

因此本轮只改变小分类器内部的参数隔离方式：冻结发布 S60 h64 基线分支，增加一个 h64 residual MLP 和一个由同一 hidden feature 学到的连续 sigmoid gate。25 个 raw logits 定义为：

`raw_logits = frozen_s60_raw_logits + sigmoid(gate_logit) * residual_logits`

这是单个确定性神经分类头的一次 raw forward，不是 ensemble 投票或 logit 后处理；完整 25 logits 在 argmax 前原样记录。RWKV hidden/state/text 均不修改。

## 冻结输入与隔离

- S60 完整 train/dev zero-state 特征：manifest `be329509a245d6ae387e0ce8813f1905320ed4a9b099d0ea25d8a3cd3b83b419`；test 不加载。
- S61 focus train 与完整 dev zero-state 特征：manifest `ad70695ec2cd79614ba5e8d0c16afa1f84365bc38675b7c58bda15ec208bd451`；test 不加载。
- 发布 S60 head SHA `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`，logical hash `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`；其参数永久冻结。
- 训练仍为 S60 train 13,143 + S61 focus train 1,000，S60/S61 域各占 0.5，域内支持类别等质量。
- S61/S60 已打开 test 不用于训练、epoch/candidate 选择或阈值。Agent Ladder 仍为冻结真实 holdout。

## 固定模型与训练

- residual：`5120 -> h64 -> 25`，GELU(tanh approximation) + LayerNorm(eps 1e-5) + dropout 0.05；residual output 层零初始化，使 epoch0 与发布 S60 raw logits byte-level数值路径等价。
- gate：复用 residual h64 hidden，`h64 -> 1 -> sigmoid`；S60 domain target=0，S61 focus target=1。
- frozen S60 branch 不参与反向传播。
- AdamW、LR `3e-4`、weight decay `1e-4`、batch 256、cosine 120 epoch、seed 1064、确定性 cuBLAS。
- 基础 loss 是 25 类监督 CE + gate BCE。S60 上另加 candidate-vs-frozen raw-logit MSE 与 frozen-class margin hinge；margin target 为冻结 margin 截断到 `[0,4]`。

固定三个候选：

| ID | gate BCE | S60 MSE | S60 margin |
|---|---:|---:|---:|
| `S64-G1` | 2 | 0.10 | 1 |
| `S64-G2` | 5 | 0.25 | 2 |
| `S64-G3` | 10 | 0.50 | 5 |

候选内选择最早过门 epoch；候选间固定 G1→G2→G3。不得根据 dev 或历史 test 追加权重、结构、LR 或候选。

## 固定 dev 门

必须同时满足：

1. S61 overall `>=0.96`、focus `>=0.95`、continuation/final `>=0.97`、focus 每个支持类 recall `>=0.90`；
2. 相对冻结 S60 head，S61 focus net rescue `>0` 且 changed decisions `>=1`；
3. S28/S39/S52/S53/S55 原绝对门全部通过；
4. S60 dev 中冻结 head 原本正确的行，candidate 回归数为 0；每个 source accuracy 不低于冻结 head；
5. S60 train teacher argmax agreement 为 1.0；
6. JSON artifact 重放 8 条 raw logits 最大绝对误差 `<=0.005` 且 argmax 一致；
7. generated RWKV text、sampling、postprocessing、raw 修改均为 0。

若无候选合格，本轮拒绝。若有唯一候选，先实现并测试通用 gated-residual artifact/runtime（不能写用例特判），再生成新的独立静态 holdout，并运行已知历史回归、三例 canary、十例 Agent Ladder、检索 R2 与全项目测试。
