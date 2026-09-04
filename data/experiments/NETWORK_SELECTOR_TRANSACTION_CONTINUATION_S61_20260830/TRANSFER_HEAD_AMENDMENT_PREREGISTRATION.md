# S61 B1 受约束迁移 Head 消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 父协议：`PREREGISTRATION.md`，SHA-256 `53f5ae53f2459d760631aa93f9cf7fd693ee43274dc767455b9634fdfda5d8b0`
- 触发证据：B0 随机初始化 h64 的 `DEV_SELECTION.json`，SHA-256 `75b84721b79493de199b925c3d4a4a778ea540efcb2042200a25144dd2fe59d9`
- B0 head：SHA-256 `9e70fb18c5fac4d807570bb7e78d6c3deabe30e418d01b3106da74be8547875d`

## 为什么增加 B1

B0 在 zero state 下证明新轨迹可由 Hidden(mean+last)+h64 学会：S61 focus `0.456 -> 1.000`，overall `0.728 -> 0.988`。但随机初始化破坏了 S60 全分布泛化，完整 S60 dev 的 S39/S52/S53/S55 均未过门，因此 B0 已拒绝且不得发布。

这不是扩大数据或改评价口径。本补充只比较从已发布 S60 h64 参数开始的最小迁移方式，训练/开发样本、特征、标签、门槛和 locked-test 隔离均保持父协议不变。

## 冻结输入

| 输入 | SHA-256 |
|---|---|
| S61 cases | `0ef53380f6dad937dd8c05237d77fa996ca73f12af24927ac754f80fcb6b9c98` |
| S61 manifest | `a52bb2e736736bf7abba2815f4557c11cb06d9198f4435c20d65c22ee38fe5a8` |
| S61 zero-state feature manifest | `ad70695ec2cd79614ba5e8d0c16afa1f84365bc38675b7c58bda15ec208bd451` |
| S60 head file | `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441` |
| S60 logical head hash | `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e` |
| S60 zero-state feature manifest | `be329509a245d6ae387e0ce8813f1905320ed4a9b099d0ea25d8a3cd3b83b419` |

## 固定候选

全部候选：

- 从 S60 head 的全部参数与 S60 feature mean/std 初始化；
- 架构仍是 5120 -> h64 -> 25，不增加 gate、规则或后处理；
- S61 train 2,000 条为唯一监督训练行，S60 full dev 和 S61 dev 只用于选择；
- 监督 loss 保持 focus/retention 各 0.5 总质量，各 cohort 内支持类别等质量；
- 对 S61 retention train 加入权重 1.0 的 S60 teacher-logit KL，以保持已有决策几何；teacher 不参与 focus；
- batch 128、weight decay `1e-4`、dropout `0.05`、cosine schedule、最多 120 epoch、patience 30、seed 1061、GPU0、确定性 cuBLAS。

四个候选固定为：

| ID | 可训练参数 | LR |
|---|---|---:|
| `B1-H1` | 仅六个 focus 类的 output weight/bias 行 | `3e-4` |
| `B1-H2` | 仅六个 focus 类的 output weight/bias 行 | `1e-3` |
| `B1-H3` | 完整 output weight/bias，shared 与 LayerNorm 冻结 | `3e-4` |
| `B1-H4` | 全部 h64 参数 | `3e-5` |

六个 focus 类固定为 `write_file`、`write_json`、`patch_json`、`replace_text`、`check_command`、`final_answer`。训练时对其他 output 行的梯度置零属于参数冻结，不改变推理 logits，也不屏蔽任何类别。

## 选择与拒绝

每个候选独立从同一 S60 head 初始化并完整运行。候选 epoch 必须同时通过父协议全部 S61 dev 与 S60 full-dev 门；相对 A 的每个 S60 source accuracy 回归仍不得超过 1 个百分点。

候选内选择最早过门 epoch；候选间先选可训练参数最少者，再选较低 LR，再选最早 epoch。若没有候选全部过门，B1 整体拒绝，不打开 S61 test，不修改门槛。

报告必须保留 B0、四候选所有 epoch 指标、原始 25 logits、changed/rescued/regressed ID、teacher 使用边界和 test 未访问证明。若 B1 过门，它才成为父协议中的正式 B 臂，与 C/D state 臂继续比较。
