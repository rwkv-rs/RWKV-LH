# S58：可辨识首操作与 V5 最短路径 Head 预登记

登记时间：2026-08-29（Asia/Shanghai）。本登记发生在 S58 数据生成、训练、
locked-test 特征提取或 test 指标读取之前。

## 根因证据

S57 按固定网格运行了 hidden 64/128/256/512 与两个学习率的 8 个候选；全部
候选在 S55 dev 上最高均为 234/240（97.5%），容量增加没有改善。冻结结果
`DEV_ABLATION_RESULT.json` SHA-256 为
`29af303f9820310e3a5d0865740b99418bc6b910f7b0df73fcf6f1cb69333ea3`。

逐类、逐位置和生成器全路径排查确认：`discount_ledger_release` 与
`failed_check_dual_output_recovery` 的首步输入具有相同的可见结构，完整请求都
明确列出源文件、规则文件和校验程序路径，progress 也完全相同；但前者由生成器
不可见的 Python `recovery=False` 标成 `list_directory`，后者由不可见的
`recovery=True` 标成 `read_file`。Selector 输入中不存在该标志，也不应该存在。
S57 的 6 个剩余错误全部是 position 0 的 `read_file -> list_directory`；8 个容量
候选的共同上限证明这是监督标签不可辨识，不是 Hidden+MLP 容量不足。

按照当前 Harness 的职责与性能目标，请求已经给出精确路径时无需先枚举整个
workspace；可辨识且更短的规范首操作是 `read_file`。这也是全局规则，不依赖任何
token、路径名、split 或单个测试样例。

## S58 数据修正

冻结源：

- S56 cases SHA-256：
  `8bd02a2368f29657bbd87d8ba103a410ec92fd04cc5c99a8286ac49064548697`；
- S55 cases SHA-256：
  `f183b5ef6389dd4549d245f05be2e9933f9b5efb8bbecaf23ae2184a75de02fe`；
- S56 feature manifest SHA-256：
  `04f1f234a480cf168b13e4db620a252e058a3b01c2efaa0ed586716ded37aa1c`。

只执行以下一个全局注释规则：对原 S55 family 为
`discount_ledger_release`、`trajectory_position == 0`、原标签为
`list_directory` 的全部记录，将标签统一为 `read_file`。预期 train/dev/test
分别修正 20/6/6 行。其它 18,261 行的标签不变；全部 18,293 行的 bootstrap、
step、prior steps、rendered input、split、轨迹和 sample id 字节不变。每行记录
原标签、修正原因和源 family，生成 manifest 记录逐 split/逐来源/逐标签计数、
文件摘要与生成脚本摘要。

因为模型输入字节完全不变，既有零-state 2.9B mean/last 特征可以按 sample id
逐行复用；特征中没有标签。S58 loader 必须验证每个 sample id、split、source、
position 与冻结 feature shard 顺序完全一致。

## 固定 Head 训练与选择

S57 中最小的 h64/lr0.001 候选除上述 6 个矛盾标签外，dev 已达到：S28 1.0、
S39 0.976663、S52 0.979950、S53 1.0。S58 因此只运行一个最小候选，不再扩大
容量：

- fresh Xavier-uniform h64 单隐层 MLP；
- 5,120 维 train-only 标准化输入；
- `Linear -> GELU(tanh approximation) -> LayerNorm -> Dropout(0.05) -> Linear(25)`；
- seed 1059、physical GPU0、AdamW、learning rate 0.001、weight decay 0.0001、
  batch 128、cosine schedule、最多 160 epoch、patience 30、gradient norm 1.0；
- 每个 `(source_dataset, label)` 支持组合拥有相同总训练权重；
- epoch 选择仍按全部门槛、最小归一化门槛裕量、五来源平均 accuracy、最早 epoch
  的固定顺序。

门槛与 S56/S57 完全相同：S28 accuracy/macro-F1 >=0.99；S39/S52
accuracy/macro-F1 >=0.96；S53 accuracy/supported-macro-F1 >=0.96；S55
accuracy/supported-macro-F1 >=0.98 且各支持类 recall >=0.90；portable replay
argmax 相同且最大绝对 logit 差 <=0.005。

只在 dev 全部通过后提取一次 locked-test 特征并计算一次同口径结果。仍然只使用
2.9B RWKV 零 state 的 same-forward Hidden mean+last 与 MLP raw argmax；不生成
Selector 文本，不做类别 mask、规则覆盖、阈值改写、重试、投票或输出后处理。
