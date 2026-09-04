# S66 × S61 2.9B state 兼容性消融预注册

- 冻结日期：2026-08-30（Asia/Shanghai）
- 实验编号：`NET-SEL-2P9-S66-STATE-COMPAT-V1`
- 目的：在不重训、不修改 S66 Soft-MoE head 的前提下，比较 zero state 与既有 2K state-tuning 的 500/1000/1500/2000 四个 checkpoint，确认 2.9B Selector 是否应加载独立 state。
- 约束：只评估固定 dev；test 在候选确定前保持关闭；不生成 RWKV 文本；不修改、删除、隐藏、重排、裁剪、修复或替换 raw hidden、25 个 raw logits 或 argmax。

## 因果问题与固定五臂

唯一因变量是送入同一个 S66-M1 head 的 mean+last hidden。head、标签顺序、输入协议、相似度/分类指标与 argmax 均不变。

| 臂 | 2.9B state | checkpoint step | head |
|---|---|---:|---|
| Z | zero | 0 | 固定 S66-M1 |
| T500 | `selector-transaction-s61-step500-v1` | 500 | 固定 S66-M1 |
| T1000 | `selector-transaction-s61-step1000-v1` | 1000 | 固定 S66-M1 |
| T1500 | `selector-transaction-s61-step1500-v1` | 1500 | 固定 S66-M1 |
| T2000 | `selector-transaction-s61-step2000-v1` | 2000 | 固定 S66-M1 |

state 是 S61 预注册 2000 条 train、seed 1061、target-only loss 的既有编号产物。不得根据本次结果追加 checkpoint、改变 state、重训 head 或重新构造数据。

## 冻结输入

| 输入 | SHA-256 |
|---|---|
| S66 dev selection | `28655511f43b68411a41771ad9cf4eb8fee492658177998125d8b641d5794fe2` |
| S66-M1 head | `858982e45822b975c3c4cf0badf4a89c12b2c85a76e7157da85809a246b7c304` |
| S61 cases | `0ef53380f6dad937dd8c05237d77fa996ca73f12af24927ac754f80fcb6b9c98` |
| S61 manifest | `a52bb2e736736bf7abba2815f4557c11cb06d9198f4435c20d65c22ee38fe5a8` |
| S60 cases | `3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf` |
| S60 manifest | `16d05f9a7e4e5c94f3f314ec5848384b96b95045609fde25d92cfb3d497be76f` |
| zero-state S61 feature manifest | `ad70695ec2cd79614ba5e8d0c16afa1f84365bc38675b7c58bda15ec208bd451` |
| zero-state S60 feature manifest | `be329509a245d6ae387e0ce8813f1905320ed4a9b099d0ea25d8a3cd3b83b419` |
| T500 feature manifest | `be06f3797af1f283a701d9c0db9f3e6fad66295d6d8649e19edb3f3c29b7600b` |
| T1000 feature manifest | `e056114e04ea58cc06ca9d090521551d56932e7dd17c47bc19d82a91baa239f5` |
| T1500 feature manifest | `85f842b85991d0e8e338519813663e4e3ed215795e85e6c554c8aa8cd6a94a4d` |
| T2000 feature manifest | `364532b598cf41050ccdee14fa4f85bc3f1fe6a74826bb70ddaf8e65a69385bd` |
| 固定 S61/S60 指标实现 | `6a133a98c14f2e10e4539632be9a53b2ce1a54891b4a12d51d00ba34d23595d9` |

每个 feature manifest 内登记的全部 shard SHA-256 必须逐一验证。固定模型为 RWKV-7 G1I 2.9B（权重 SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`），引擎 revision `67f0c5996c50dca0ad779da545cb491527de988f`，输入协议 `rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail`，特征为同一 current forward 的 hidden mean+last（5120 维）。既有特征均必须证明在物理 GPU0 `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48` 提取，且生成文本与 sampling 次数均为 0。

## 数据隔离

- S61：只解析 dev 500 条标签；train 仅跳过，test 500 条在 JSON parse 前跳过。
- S60：只解析 dev 2571 条标签；train 13143 与 test 2579 条在 JSON parse 前跳过。
- 特征 loader 只读取上述 dev sample ID；即使 manifest 含 train feature，也不用于评价。
- 本次不读取任何 S61/S60 test feature 或 test raw logits，不运行 locked test；只有 dev 候选通过后才允许另行冻结 test 运行。

## 固定指标和门槛

使用冻结的 25 类顺序与直接 `argmax(raw_logits)`，统一计算混淆矩阵、accuracy、supported macro-F1、每类 recall、S61 continuation-vs-final boundary、S60 各历史 source 指标，以及相对 Z 的 changed/rescued/regressed sample ID。

每个 state 臂必须同时满足：

1. S61 overall accuracy `>= 0.96`；
2. S61 focus accuracy `>= 0.95`；
3. continuation-vs-final boundary accuracy `>= 0.97`；
4. S61 focus 中每个有支持类别 recall `>= 0.90`；
5. 相对 Z：changed decisions `>= 1` 且 focus net rescue `> 0`；
6. S60 固定绝对门：S28 accuracy/macro-F1 `>= 0.99`，S39/S52/S53 `>= 0.96`，S55 accuracy/macro-F1 `>= 0.98` 且 minimum supported recall `>= 0.90`；
7. S60 每个 source accuracy 相对 Z 回归不超过 0.01；
8. 为避免旧功能消失，Z 上正确的 S60 dev 样本不得被 state 改错；
9. raw logits 未修改，logit postprocessing、RWKV text generation、sampling 均为 0。

最小状态发布规则沿用 S61：只有在上述门全过且 S61 focus accuracy 相对 Z 增益 `>= 0.02` 时，state 才在 dev 上获得发布资格。若只过基础门但 focus 增益 `< 0.02`，只能标为 `real-canary-conditional`，还必须在冻结真实 canary 中至少增加一个 strict/transaction-complete case 才能启用。多个合格 state 选择最早 step；一次 run 内绝不切换 state。

如果没有 state 获得资格，结论必须是保留 S66 zero state，不为追求“存在 state”而重新训练。此结论只针对 2.9B Selector，不取消 13.3B Executor 的 G3/G6 独立 state；13.3B 仍按选对工具后的参数/内容/修复/总结残差单独处理。

## 输出与完成条件

结果必须落在本实验目录的新 run 中并包含：五臂完整指标、全部 raw logits、changed/rescued/regressed ID、每项 gate、输入/脚本/结果哈希、test 隔离证明、feature shard 校验、产品服务前后健康状态。不得覆盖既有 S61/S66 文件；评价结束后不得修改门槛或评价口径。
