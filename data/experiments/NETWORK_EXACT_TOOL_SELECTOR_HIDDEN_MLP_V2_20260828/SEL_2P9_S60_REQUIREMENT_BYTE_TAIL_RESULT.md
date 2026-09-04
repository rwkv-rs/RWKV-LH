# SEL-2P9-S60 Requirement Byte-Tail 锁定结果

日期：2026-08-29。状态：`eligible_for_harness_ablation=true`；尚不代表产品发布。

## 冻结身份

- 输入协议：`rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`。bootstrap 只含 25 个名称/描述与任务 SHA；每一步顺序固定为 progress、stage role、current question，嵌套最后字段为 literal immutable requirement。
- 模型：2.9B G1i，显式 zero state；特征为同一 forward 的 Hidden concat(mean,last)，Head 为 h64 MLP、25 个原始 logits 直接 argmax；生成文本、sampling 和 logit 后处理调用均为 0。
- 数据：train 13,143、dev 2,571、locked test 2,579；cases SHA-256 `3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf`，manifest SHA-256 `16d05f9a7e4e5c94f3f314ec5848384b96b95045609fde25d92cfb3d497be76f`。
- train/dev 特征 manifest SHA-256 `be329509a245d6ae387e0ce8813f1905320ed4a9b099d0ea25d8a3cd3b83b419`；locked 特征 manifest SHA-256 `4edd8da1c0f49ab52ed81b6362fa1745ef00518244dd6c5bf6926d5c37a95d37`。
- Head 文件 SHA-256 `721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441`；Head identity `205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e`；dev selection SHA-256 `5b40a8c0ea02430db4e6fedc8bb6190298f3f4ef0e2539e8e515d11f9f2a17dc`。

## 固定指标

选定 epoch 89。dev：S28 `0.998667`、S39 `0.969662`、S52 `0.977444`、S53 `0.996923`、S55 `0.991667`。

锁定 test 在 dev gate 通过后一次读取：

| 切片 | accuracy |
|---|---:|
| S28 | 0.997333 |
| S39 | 0.962660 |
| S52 | 0.980344 |
| S53 | 1.000000 |
| S55 | 0.983333 |

全部预注册 accuracy/F1/每类 recall 与 portable replay 门槛通过；portable replay argmax 完全一致，数值最大误差约 `1.7e-5`。locked result SHA-256 为 `57e29bb78f1a75deacd23ad92f5c1689ed14e1e13aab7d6e9e8ad66efef6ae4c`。

本结果只允许 S60 进入预注册 S53/S60 × G3/G5 真实 Harness 因子实验；是否发布由真实 canary、联网、检索、Full90 和全量回归共同决定。
