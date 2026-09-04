# S63 Selector 功能信赖域保留消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 实验编号：`NET-SEL-2P9-S63-FUNCTIONAL-TRUST-ZERO-STATE`
- 设备：仅物理 GPU0
- 目标：保持 2.9B Hidden(mean+last)+h64、25 类 raw argmax 与 zero state，不增加规则路由；在学会 S61 续作边界时严格保留发布 S60 head 的旧决策几何。

## 已知证据与诚实边界

S62-U1 dev 通过，但已打开的 locked regression 被拒绝：S61 overall/focus/boundary 为 `0.996/0.992/1.000`，S39/S55 为 `0.948658/0.979167`。结果 SHA-256 为 `51356a7b3fbd819dc9e6aa92ee341a4110ede2594237bd2b69c3732d3830abc9`。

S62 train/dev 几何分析显示：13,143 条 S60 train 的 teacher argmax 变化为 0，但 2,571 条 S60 dev 已变化 24 条，说明 train 分类正确不足以约束旧函数；需要保留 raw-logit/margin 几何，而不是继续增加 state。分析文件为 `data/experiments/NETWORK_SELECTOR_FULL_RETENTION_S62_20260830/RETENTION_GEOMETRY_ANALYSIS.json`。

S61 test 与 S60 历史 locked test 已经打开，S63 不把它们重新称为盲测，也绝不用于训练、epoch/candidate 选择或阈值修改。它们只作为已知历史回归。最终未见能力由冻结 Agent Capability Ladder 和在候选冻结后生成、登记的新独立 holdout 验证。

## 冻结训练/选择输入

- S60 完整 train 13,143 行与 dev 2,571 行；test 不由本 runner 读取。
- S61 focus train 1,000 行与完整 dev 500 行；S61 retention train 不重复加入；test 不由本 runner 读取。
- S60 发布 head SHA `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`，logical hash `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`。
- S62-U1 head SHA `f764841340aeb65b674f8fef81a016f351db3c25d78470f6a8dfdf2c290b12af`，只作为固定参数插值端点，不把其 test 结果送入选择器。
- zero-state S60/S61 train/dev 特征 manifest 分别为 `be329509a245d6ae387e0ce8813f1905320ed4a9b099d0ea25d8a3cd3b83b419` 与 `ad70695ec2cd79614ba5e8d0c16afa1f84365bc38675b7c58bda15ec208bd451`。

## 固定候选

所有候选输出仍是单一 `5120 -> h64 -> 25` MLP 的 25 个 raw logits；不做 logit blending、postprocessing、类别屏蔽或 Controller 特判。

### P：参数信赖线段

在发布 S60 参数 `theta0` 与冻结 S62-U1 参数 `theta1` 之间，固定计算 `theta(alpha)=theta0+alpha*(theta1-theta0)`。固定网格为 `0.10, 0.15, ..., 1.00`；按最小 alpha 选择首个同时过全部 dev 门的值。插值在参数内完成，运行时仍只有一个 h64 head；不是双模型 ensemble。

### T：功能信赖域训练

若 P 无合格值，按下表从同一 S60 head 初始化训练。监督 sampling 与 S62 相同：S60/S61 focus 各占 0.5，域内支持类别等质量；batch 256，LR `3e-4`，AdamW weight decay `1e-4`，dropout `0.05`，cosine 180 epoch，seed 1063，确定性 cuBLAS。

S60 sampled row 的功能保留损失为：teacher KL + raw-logit MSE + teacher-class margin hinge；hinge target 是发布 head 原 margin 截断到 `[0,4]`。三项只作用于 S60，不作用于 S61 focus。

| ID | KL 权重 | MSE 权重 | margin 权重 |
|---|---:|---:|---:|
| `S63-T1` | 2 | 0.05 | 2 |
| `S63-T2` | 5 | 0.10 | 5 |
| `S63-T3` | 10 | 0.25 | 10 |

候选内选择最早过门 epoch；候选间按 P 优先且 alpha 最小，否则 T1→T2→T3、再按最早 epoch。不得根据结果追加权重、LR、epoch 或候选。

## 固定 dev 门

除 S61 父门（overall `>=0.96`、focus `>=0.95`、continuation/final `>=0.97`、focus 支持类 recall `>=0.90`、相对 S60 head 的 focus net rescue 为正）与全部 S60 绝对门外，增加严格信赖门：

1. S60 dev 中发布 head 原本预测正确的行，candidate 回归数必须为 `0`；
2. S60 dev 每个 source accuracy 不低于发布 head；
3. S60 train 的 teacher argmax agreement 必须为 `1.0`；
4. generated RWKV text、sampling、logit postprocessing、raw 修改均为 0。

dev 只选择，不反向传播。若全部候选失败，本实验拒绝，不打开/重用任何 test 来改选。

## 后续验证

唯一 candidate 冻结后：先生成并冻结新的独立 selector holdout，再运行一次；随后将 S61/S60 已知 test 仅作为历史回归、原三例 bugfix canary、完整十例 Agent Capability Ladder、Retrieval Quality R2 与全项目回归原样运行。只有 Selector 选对后仍存在参数/内容/修复/总结残差，才进入 13.3B state 消融。

任何阶段都不得诱导、修改、删除、截断、补全、重排、隐藏或替换 RWKV 原始输出。
