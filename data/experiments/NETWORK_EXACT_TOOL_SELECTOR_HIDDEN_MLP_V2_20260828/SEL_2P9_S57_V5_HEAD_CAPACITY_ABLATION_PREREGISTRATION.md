# S57：V5 full-request-last Head 容量消融预登记

登记时间：2026-08-29（Asia/Shanghai）。本登记发生在任何 S57 训练运行、
S56 locked-test 特征提取或 test 标签读取之前。

## 触发证据与不变边界

S56 按预登记完成了唯一的 S53-h64 迁移候选，但 dev 未过门槛，因而没有打开
locked test。冻结证据如下：

- S56 `DEV_SELECTION.json` SHA-256：
  `29acddea63e2a0b658139b8fa15e839559c310e7255b274623302a6b91038de6`；
- S56 Head SHA-256：
  `e9ad912badfac830e1beb39a826274ae3b2f230368eee7db5f08b5cb619b794b`；
- dev accuracy：S28 1.0000、S39 0.928821、S52 0.964912、
  S53 0.996923、S55 0.962500；
- 失败集中在 V5 后的通用 25 类 S39 以及真实联动 S55，S28/S52/S53 已达到
  原门槛。这是 Head 对新表征的容量/优化不足，不允许通过降低阈值、类别 mask、
  logit 修正、规则覆盖或读取 locked test 解决。

S57 只消融 MLP Head 容量和固定学习率。2.9B RWKV、零 state、V5 输入字节、
same-forward `concat(mean,last)` 特征、25 个工具类别、train/dev/test 划分和
所有评价口径保持不变。Selector 仍不生成文本，只采用 25 维原始 logits 的
raw argmax。

冻结输入：

- S56 cases SHA-256：
  `8bd02a2368f29657bbd87d8ba103a410ec92fd04cc5c99a8286ac49064548697`；
- S56 train/dev feature manifest SHA-256：
  `04f1f234a480cf168b13e4db620a252e058a3b01c2efaa0ed586716ded37aa1c`；
- V5 renderer SHA-256：
  `3d19665e4a85d5296b336acf616a087f4d1e272aa8acebfc5855d7a02edab7bf`；
- test 2,579 行继续锁定，不提取特征、不解析标签，除非 dev 选择通过全部门槛。

## 固定候选与训练方式

每个候选均为单隐层 MLP：train-only 标准化后的 5,120 维输入，
`Linear -> GELU(approximate=tanh) -> LayerNorm -> Dropout(0.05) -> Linear(25)`。
使用 fresh Xavier-uniform 初始化，不继承 S53/S56 参数，以隔离 V5 表征下的
Head 容量效应。

候选笛卡尔积固定为：

- hidden dimension：64、128、256、512；
- learning rate：0.0003、0.001；
- 共 8 个候选，全部运行，不根据中途结果增删。

共同参数：seed 1059、physical GPU0、AdamW、weight decay 0.0001、batch 128、
cosine schedule、最多 160 epoch、patience 30、gradient norm 1.0。训练损失令
每个 `(source_dataset, label)` 支持组合拥有相同总权重；任何 test 字段均不参与
归一化、训练、早停或选择。

每个候选的 epoch 选择顺序固定为：先满足全部 dev gates；再最大化所有门槛的
最小归一化裕量；再最大化五个来源 accuracy 的算术均值；再选择更早 epoch。
最终候选选择顺序固定为：通过全部门槛的最小 hidden dimension；同 hidden 下
选择较低 learning rate；若仍并列，使用上述 dev key。若 8 个候选均失败，则
S57 失败且 locked test 保持关闭。

## 不变门槛与发布规则

- S28 accuracy/macro-F1 >= 0.99；
- S39、S52 accuracy/macro-F1 >= 0.96；
- S53 accuracy/supported-macro-F1 >= 0.96；
- S55 accuracy/supported-macro-F1 >= 0.98，且每个有支持类别 recall >= 0.90；
- portable raw-logit replay argmax 完全一致、最大绝对 logit 差 <= 0.005；
- 不做阈值路由、类别 mask、重试、投票或输出后处理。

只有 dev 选择满足全部条件才提取一次 S56 locked-test 特征并执行一次测试。
locked test 使用完全相同门槛；通过后才允许进入真实 Harness 四臂联动消融。
所有失败候选、原始 logits、raw argmax、训练历史和身份散列均保留。
