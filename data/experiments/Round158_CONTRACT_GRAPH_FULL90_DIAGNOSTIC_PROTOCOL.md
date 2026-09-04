# Round158：Strong Planner/Reviewer + RWKV Contract Graph Full90 诊断协议

日期：2026-08-23

## 性质与目的

本轮是固定 RWKV-E2E-90 的**诊断性全量测试**，不是 canonical baseline 晋级测试。
Round157 的 3-case canary 未达到 3/3，因此本轮不能因为局部结果改善而替换 R126；目的
是一次性测清新架构的真实能力边界、系统性失败簇、成本和并行执行完整性。运行开始后不得
修改代码、任务、hidden verifier、参数、分类规则或阈值来改善本轮结果。

## 数据来源、版本与生成方式

- Suite：`data/datasets/rwkv_e2e_90_v1/`，runner 的 `--suite all`，固定 90 例
  （B30 / M30 / H18 / LH12）。本轮不生成训练数据。
- 用途：比较 Strong Planner/Reviewer + RWKV Contract Graph 架构与 R126 canonical、
  Round148 Full90，并为后续系统性整改与 state-tuning 数据筛选建立原始证据。
- 生成方式：`scripts/run_rwkv_e2e_benchmark.py` 创建逐例隔离 workspace、执行工具与
  hidden external verifier；runner 自动写入 `RUN_PROTOCOL.json`、
  `source_tree_manifest.json`、逐例 `audit.json` 和文件摘要。
- 代码和数据的实际 SHA-256 以输出目录中的上述两个机器记录为准。

## 固定架构与参数

- 架构：`strong-planner-reviewer-rwkv-contract-graph.v1`。
- GPT-5.4：只负责在线 Planner 和独立 Reviewer；只接收 immutable request、contract
  graph 和 result-only capsules，不接收 RWKV 的推理过程；无工具执行权，不改写 Final。
- RWKV g1i-13.3：唯一工具操作者和 Final 主体；atom 并发上限 4。
- Planner/Reviewer reasoning=`medium`；仅当同一逻辑请求出现 HTTP 5xx 时，物理重试
  可回退到 `low`，必须留审计事件。
- transport retry=3；semantic repair=2；plan/review tokens=4000/2400。
- graph patches/reviews/atoms/stagnation=8/8/48/2；atom max transitions=40；
  case max transitions=200。
- case concurrency=4；GPT 请求串行；tool disclosure=`full`；其余采样、工具实现和
  verifier 使用 runner 当前固定配置。
- 输出目录：`data/experiments/Round158_contract_graph_full90_20260823/`。

## 预注册统计口径

- `TP`：agent completed 且 external verifier passed。
- `FP`：agent completed 但 external verifier failed。
- `FN`：agent 未 completed 但 external verifier passed。
- `OTHER`：agent 未 completed 且 external verifier failed。
- 固定报告 strict TP/FP/FN/OTHER、B/M/H/LH 分层、每个 external check、状态与终止原因。
- 固定报告 GPT logical/physical/returned calls、prompt/completion/reasoning/total tokens、
  RWKV actions、protocol rejections、并行 overlap cases、零 action finalizer、raw Final 一致性。
- 与 R126 canonical 和 Round148 使用同一分类口径做对照；不根据本轮输出修改评分定义。

## 诊断门与架构完整性门

1. 完整性：90/90 均有持久化结果，0 running，0 runner/verifier infrastructure failure。
2. 参考能力门：strict TP `>36`、FP `<=24`、FN `<=1`；仅作为能力比较，不能越过
   Round157 canary 的正式晋级前置条件。
3. 分层参考门：B `>=23`、M `>=10`、H `>=2`、LH `>=1` strict TP。
4. GPT tool execution count=0；completed Final 与 raw RWKV Final byte-exact。
5. obligations 在 revision 0 后冻结；deterministic kernel 只能基于公开 result capsules
   否决，不可自行满足义务；所有 replan/fallback/失败均须可审计。
6. 报告完整失败簇：规划契约、RWKV 操作、依赖/状态传递、Reviewer 误判、机械 veto、
   transport、预算/停滞、schema/path/content 精度及其同类场景。

任一门未满足都必须如实保留。错误 acceptance、FP 和未证实轨迹不得直接作为后续
state-tuning 正样本；只能作为负例、纠错候选或人工复核种子。
