# S66 × S61 2.9B state 兼容性消融结果

结论：四个既有 2K state checkpoint 全部拒绝，2.9B Selector 保留 `S66-M1 + zero state`。

## 固定 dev 结果

| arm | step | S61 overall | S61 focus | focus 相对 Z | boundary | S60 zero-correct 回归 | 发布资格 |
|---|---:|---:|---:|---:|---:|---:|---|
| Z | 0 | 98.0% | 96.0% | — | 100% | — | 当前基线 |
| T500 | 500 | 98.4% | 96.8% | +0.8pp | 100% | 2 | 拒绝 |
| T1000 | 1000 | 98.6% | 97.2% | +1.2pp | 100% | 3 | 拒绝 |
| T1500 | 1500 | 98.8% | 97.6% | +1.6pp | 100% | 1 | 拒绝 |
| T2000 | 2000 | 98.4% | 96.8% | +0.8pp | 100% | 3 | 拒绝 |

四个 state 都对 S61 新阶段样本产生了部分净救援，但同时改变并破坏了 S60 历史正确决策；最大 focus 增益 T1500 为 1.6pp，仍低于预注册的 2pp 最小状态收益门。所有 state 均未通过 `s60_zero_correct_regressions_zero`，也没有进入 real-canary-conditional 分支。

S60 各 source 的总体 accuracy 仍落在旧宽松阈值内，但这不足以发布，因为用户要求防止“网络做好、其他功能消失”；逐样本保留门直接发现了 1–3 个原本正确样本被改错。这说明 state 与 head 的联动确实存在，但当前联动不是无损增益。

## 完整性和隔离

- S61 只解析 dev 500 条；train 2000 与 test 500 均在 JSON parse 前跳过。
- S60 只解析 dev 2571 条；train 13143 与 test 2579 均在 JSON parse 前跳过。
- 五臂共保存 15,355 行、每行 25 个 raw logits；SHA-256 `b7d93ff28190e8b18e41fa9bc4c1737eb6d30ba2f8d8cbd85e06b0134f7437f9`。
- RWKV text generation、sampling、logit postprocessing 均为 0；raw hidden/logits 未修改。
- 所有 feature manifest 与其声明的全部 shard SHA-256 均验证；特征来自物理 GPU0 `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48`。
- 本地产品 29610 与远端产品 18070 在实验前后均 HTTP 200。

权威结果是 `run_dev_compatibility_v1/RESULT.json`（SHA-256 `ce8b1b98fea7976ea1e1e78b80f5734492080e8b4f3a8d51f8a7b61d6c84c367`）。本结论只决定 2.9B Selector state，不预设真实 Harness 中其他层的错因，也不取消 13.3B G3/G6 的独立 state 设计。
