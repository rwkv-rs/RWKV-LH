# RWKV-LH State Router 阶段 0 结果

- 日期：2026-08-27
- 协议：`rwkv-lh.state-router-metrics.v1`
- 数据：`rwkv-lh.state-router-2k.v1`，train/dev/test = 1400/300/300
- test SHA-256：`2d69f65491ac3379e8cb22658212c2ad3ae4761fa028dd40fdf7f62323a0fb35`
- 运行：WSL `UbuntuRecovered`，项目内本地 RWKV-FLA/Transformers，CUDA bfloat16
- 模型：`fla-hub/rwkv7-0.4B-g1@b84a6a3e9f51168241c733058098cb6354d3fc04`

## 结论

阶段 0 的工程实现、固定 2k 数据、真实本地 RWKV 前向、A/B/C 消融和全量失败审计均已完成。
A、B 均通过首轮离线分类门槛；C 未通过。三者均未通过正式安全门禁，因此本轮
`selected_candidate=null`，不得进入 Shadow/主 Harness。

唯一阻止 A/B 正式通过的指标是 `evidence-missing` 时提前 `final`：阈值 `<=0.01`，
A 为 `0.028571`，B 为 `0.021429`。安全优先排序不允许用更高的 macro-F1 覆盖该失败。

## 固定 test 结果

| 候选 | 特征 | route acc | route macro-F1 | phase macro-F1 | network recall | connector recall | ECE | 提前 final | 首轮 | 正式 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| A | 最终层 hidden mean + MLP | 0.986667 | 0.985986 | 0.992048 | 0.970370 | 1.000000 | 0.006332 | 0.028571 | 通过 | 未通过 |
| B | 最后一层 WKV stats + train-only PCA + MLP | 0.990000 | 0.989605 | 0.992116 | 0.977778 | 1.000000 | 0.007368 | 0.021429 | 通过 | 未通过 |
| C | 单 token 约束 logits | 0.100000 | 0.034790 | 0.180200 | 1.000000 | 0.000000 | 0.152359 | 0.000000 | 未通过 | 未通过 |

A/B 的 Summary 一致率、OOD abstain recall 和高置信 route accuracy 均为 `1.0`；A/B 的
policy-rejected 继续率、connector 降级 web 和错误联网率均为 `0`。C 的 policy-rejected
继续率和错误联网率均为 `1.0`，不能作为候选。

## 全路径失败审计

审计覆盖 train/dev/test，而非只看发现问题的单个 test 用例：

- A：train 提前 final `0`；dev `0.022059`；test `0.028571`。test 的 4 个 route 错误全部为
  `mixed->final`，样本为 `RTR2K-1602/1610/1618/1634`。
- B：train 提前 final `0`；dev `0.014706`；test `0.021429`。test 的 3 个 route 错误全部为
  `mixed->final`，样本为 `RTR2K-1602/1626/1634`。
- 所有错误都属于 continuation、evidence missing、仍需取得外部或混合证据的同类场景。
  这说明风险位于 route/phase 的共享表示边界，不是 Connector Gate、Policy Gate 或单一模板。
- 本轮不依据 test 修改标签、门槛、切分或加样本特判。后续整改必须登记新数据版本与新的
  未见 holdout，再处理 `mixed/final` 与 evidence completeness 的联合边界。

机器可读逐样本记录见 `failure_analysis.json`；固定安全优先排序见 `ablation.json`。

## 本地引擎与资源

本地后端直接作为 `rwkv_lh.state_router` 的一部分加载模型，不经过远端推理 API：

- A：hidden extraction `41.235s`，head training `0.710s`，总计 `41.945s`；CUDA peak allocated
  `1,157,440,512` bytes。
- B：WKV extraction `54.821s`，PCA `0.168s`，head training `0.667s`，总计 `55.656s`；
  CUDA peak allocated `1,214,359,552` bytes。
- C：全量 2k 推理 `57.821s`，`34.590 samples/s`；CUDA peak allocated
  `1,358,781,440` bytes。
- 额外真实探针验证了 A `[1,1024]` hidden、B `[1,4096]` WKV stats、C `[1,7]` route logits
  均有限值；项目入口对一个未见请求因 route confidence `0.783 < 0.92` 正确回退为
  `abstain + S_base`。

第一次 A 运行因 cuBLAS 未在首次 CUDA 操作前设置 deterministic workspace 而作废，保留于
`STATE_ROUTER_STAGE0_HIDDEN_MLP_V1_20260827/INVALIDATED.md`。R2 在共享本地后端导入 Torch 前固定
`CUBLAS_WORKSPACE_CONFIG=:4096:8`，随后重新完成 A/B/C；旧运行未参与上述结果或选择。

## 产物与复核入口

- 预注册：`PREREGISTRATION.md`
- 冻结实现：`FROZEN_CODE_MANIFEST_R2.json`
- 消融：`ablation.json`
- 失败审计：`failure_analysis.json`
- 本地 CLI 实测：`LOCAL_RUNTIME_SMOKE.json`
- 部署态代码与回归：`DEPLOYMENT_CODE_MANIFEST.json`
- A：`../STATE_ROUTER_STAGE0_HIDDEN_MLP_V1_R2_20260827/results.json`
- B：`../STATE_ROUTER_STAGE0_WKV_PCA_MLP_V1_20260827/results.json`
- C：`../STATE_ROUTER_STAGE0_CONSTRAINED_LOGITS_V1_20260827/results.json`

训练脚本默认输出目录在正式运行后仅作了一项操作性修正：由已作废目录切换到 R2 目录；
算法、依赖、数据和评测逻辑没有改变。正式结果仍以 R2 冻结清单中的运行时代码 hash 为准。

最终全仓库回归为 `343 passed in 37.88s`；`uv lock --check` 与 `git diff --check` 均通过。
