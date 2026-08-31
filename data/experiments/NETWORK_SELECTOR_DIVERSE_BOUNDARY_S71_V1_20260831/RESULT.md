# Network Selector S71 diverse-boundary 2K V1 — 结果

日期：2026-08-31（Asia/Shanghai）

## 结论

S71 已按预注册口径完成 zero state 和四个 state checkpoint 的开发集消融。所有候选均未达到
`accuracy >= 0.96`、`macro-F1 >= 0.96`、每类 recall `>= 0.90` 的联合门，因此 S71 整体拒绝：

- 未选择任何 state/head；
- 未读取、解析或评估 S71 locked test；
- 未接入产品 Selector；当前正式绑定继续保持 S60 zero-state；
- 不允许用 S71 的 train 指标、局部类别指标或最优 epoch 代替开发门结论。

## 固定开发集结果

| 候选 | train acc / F1 / min recall | dev acc | dev macro-F1 | dev min recall | 结论 |
|---|---:|---:|---:|---:|---|
| Zero | `1.0 / 1.0 / 1.0` | `0.922` | `0.920506` | `0.50` | reject |
| S71-ST500 | `1.0 / 1.0 / 1.0` | `0.920` | `0.918819` | `0.50` | reject |
| S71-ST1000 | `1.0 / 1.0 / 1.0` | `0.918` | `0.916891` | `0.50` | reject |
| S71-ST1500 | `1.0 / 1.0 / 1.0` | `0.916` | `0.915165` | `0.50` | reject |
| S71-ST2000 | `1.0 / 1.0 / 1.0` | `0.918` | `0.916862` | `0.50` | reject |

最佳 state 仍比 zero state 低 `0.2` 个百分点；500→2000 步不存在单调收益。主要稳定混淆为
`write_json -> patch_json`、`move_file <-> copy_file`、`delete_file -> remove_line`、
`append_file -> replace_text`。证据只支持以下边界：继续增加同一训练目标的步数不能解决问题；下一版应先
验证 state 的目标/读出位置能否让这些语义效果边界可分，而不是直接扩大步数或打开 locked test。

## 完整性与运行现场

- 数据固定为 train/dev/locked `2000/500/500`，25 类，中英文平衡；只有 train 参与 state/head 梯度。
- 远端 state run 完成 2000/2000；500/1000/1500/2000 四个状态均为 32 个有限非零张量、
  5,242,880 个元素，基础权重未改变。
- 四个候选均用同一 2.9B 权重、输入 V7、one-forward `global_mean + suffix_mean + final_last`、
  `DualViewGatedH128`、seed 和 raw argmax；唯一实验变量是 state checkpoint。
- 没有生成/采样 RWKV 文本，没有修改、删除、隐藏、重排、截断、修复或替换 RWKV state、hidden、
  raw logits、trainer log 或模型输出。
- 仅使用 GPU0。训练与消融进程已退出，实验端口 18075 未监听；`rwkv-8222:18070` 验证健康，
  GPU1/2 未被本实验使用。

## 可复核证据

- zero result：`run_zero_state_head/RESULT.json`，SHA-256
  `8d2695a53f8d53e785a9f3d0077fab7f232828d64c22fe2b6b3c25e3de422e62`
- checkpoint collection：`run_s71_state_training_remote_checkpoint/COLLECTION_MANIFEST.json`，SHA-256
  `74d7f0bf60e6dad408d34625755b76691bdf3c4c743b427734f7348b2c98c5ec`
- state dev comparison：`run_state_dev_comparison/RESULT.json`，SHA-256
  `94863230e34285e71753a57a5fbb49a441cc16b17d276003cf4eaca7931baddd`
- 四个 state feature manifest SHA-256：
  `f8440cc562f7b6e31d18ae1a1bb7530694a96218a50c520d8d9a3783aee9cd67`、
  `2d33c0d05877a31f4418eeb83a30c8ebfdaa1f10437e0c1d1df7a95a9488c84e`、
  `5090bb63048d736916b2d5cacd1100371045cb18a1066b2959ade8f5348269cd`、
  `8ccc32cb8a065095dfc8b59524adddc3464bf80119cd4c0018c0e91d29cdb473`

## 交接建议

不要从 S71 locked test 继续，也不要上线四个 S71 state。最快的后续因果实验是保持 S71 test 封存，另建
新编号数据/实验，固定比较：同一输入下的 target-suffix next-token state 目标与直接工具边界/对比目标，
并先在可见 dev 上量化 hidden 类间 margin 是否真正提高；只有开发联合门通过才允许一次 locked test。
