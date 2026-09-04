# S60 胜出架构本地 V1 发布门槛预注册

登记时间：2026-08-29；发生在 S60×G3/G5 真实 Harness 因子结果、任一发布验证运行和本地配置切换之前。

## 固定候选与运行原则

- 候选只能是已预注册因子实验选择的 `S60+G3` 或 `S60+G5`；不得发布 S53、S59、G4 或因发布测试结果而补选的 checkpoint。
- Selector 固定为 2.9B zero-state、V7 literal requirement byte-tail、Hidden concat(mean,last)、h64 MLP、原始 25 logits argmax；不生成 Selector 文本，不做阈值、重选或 logit 后处理。
- Executor 固定为 13.3B、物理 GPU0、temperature 0.1、top-p 1、top-k 0、一次原始生成；每个服务只加载一次选定 state，阶段间不切换 state。
- 原始响应 envelope、raw text/token、Selector logits、state attestation 与 append-only journal 全部保留。不得诱导、修改、删除、重排、隐藏或语义替换 RWKV 原始输出。

## 发布验证顺序与固定门槛

1. 因子实验必须有且仅有一个按既定优先级选出的 S60 arm，且该 arm 在固定 canary6 上 6/6 strict、完整性 valid、每个 Selector checkpoint 的 immutable requirement 均为字节尾部。
2. 固定 live-network V2 的两个用例经 V7 扩展验证器运行，必须 2/2 strict；每个已提交 Selector 输出都要有 V7 requirement-byte-tail 证据；每个网络 action 必须提交可追溯 evidence；Executor 每次输入必须是 current requirement 或 rejection question 位于续写边界。
3. 复跑 `rwkv_lh_retrieval_quality_v1` 固定 9 行数据（SHA-256 `eee343aa311811a349476f4f632b0a4a5e97cc1e6657e4c8c68255124297fd2e`），沿用原预注册 hard gates：9/9 通过、4/4 Tavily-required 无发现回退、请求绑定/快照/span 完整、单 action 不超过 60 秒、零凭据落盘。top-1、host precision、重复率、p50/p95 只报告，不在运行后改变评价口径。
4. Full90 首先运行 `S60+G3` 同轮保留基线；若因子选择 G5，再以完全相同参数运行 `S60+G5`。候选必须分发 90/90、完整性 valid、原始生成数与输入数一致，并且只有 `E2E-LH09/mock_api` 可以登记为明确 unsupported。候选 strict pass 不低于 41、agent completed 不低于 57；该数值冻结自历史最佳完整运行 `Round148_parallel_atom_graph_v4_full90_20260822/results.json`（90/41/57，SHA-256 `7d16f9d3ffdecd4ce8dcf2b2bbf38414f803644947b78ff6ec47f707fce1459a`）。若使用 G5，候选 strict/completed 数不得低于同轮 S60+G3，且 S60+G3 已 strict 通过的任一 case 不得在 G5 下回归。
5. 运行项目 `tests/` 全量测试，并复跑与 Selector、Executor、retrieval、prompt/state 完整性直接相关的固定测试；必须零失败。任何失败要扩展检查同类数据和代码路径，不得做用例特判。

只有以上门槛全部通过，才允许把 S60 与胜出 Executor state 写入忽略的 `.env.local`，启动同一身份的本地服务，并更新状态/交接文档。任一门槛失败则保持现有产品配置，不用“联网已通”替代真实 Harness 发布质量。
