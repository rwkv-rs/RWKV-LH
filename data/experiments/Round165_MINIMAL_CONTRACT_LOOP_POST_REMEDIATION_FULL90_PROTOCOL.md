# Round165：Minimal Contract Loop Post-Remediation Full90 协议

日期：2026-08-24

## 性质与目的

用户明确要求后续质量判断统一以完整 90 例为标准，不再以局部 Canary 代替整体结论。因此本轮
直接运行固定 RWKV-E2E-90，完整覆盖 B30/M30/H18/LH12；运行开始后不得按局部结果停止、改代码、
更换模型、修改阈值或改变 external acceptance。

本轮验证 Round164 minimal contract loop 以及 Canary 后三项通用整改：JSON pointer digest
relation、review-gated frozen finalizer、JSON numeric value semantics。强模型仍只作 Planner/Reviewer，
RWKV g1i-13.3 仍是唯一工具参数生成者、工具操作者和 Final 作者。

## 固定数据和不可见边界

- Suite：`data/datasets/rwkv_e2e_90_v1/`，runner `--suite all`，固定 90 例。
- visible tasks 与 hidden acceptance 沿用数据集 v1；hidden acceptance 只允许 runner 在任务结束后
  评价，Planner、Reviewer、RWKV 和控制器运行时均不可见。
- Codex reference answers 运行时禁止读取，仅可在全量结束后进行总体差异分析。
- source hashes 由 runner 的 `RUN_PROTOCOL.json` 和 `source_tree_manifest.json` 固化。
- 输出：`data/experiments/Round165_minimal_contract_loop_full90_20260824/`。

## 固定架构与参数

- 主循环：`Plan -> deterministic batch -> parallel RWKV transaction -> typed evidence ->
  Review -> Complete/Correct`。
- Supervisor primary=`gpt-5.6-terra`，fallback=`gpt-5.6-sol`；circuit failures=2，cooldown=30s。
- Planner/Reviewer reasoning=`medium/medium`，transport retry=3，semantic repair=2，GPT 跨进程串行。
- case concurrency=4；每题 RWKV atom concurrency=4；atom transitions=40；case transitions=200。
- graph patches/reviews/atoms/stagnation=`8/8/48/2`；tool disclosure=`full`。
- contract plan/review token 上限=`4000/2400`；RWKV temperature=`0.05`。
- 使用新的空 plan cache；不得命中 Round162/Round164 旧计划。
- strong Reviewer payload 不含 node graph 或 RWKV prompt/transcript/reasoning/retry；GPT tool calls=0；
  Final 必须与 accepted RWKV finalizer candidate byte-exact。

## 固定统计口径

- TP：agent completed 且 external passed。
- FP：agent completed 且 external failed。
- FN：agent 非 completed 且 external passed。
- OTHER：agent 非 completed 且 external failed。
- 必须报告 90/90 完整性、B/M/H/LH 分层、全部 external checks、terminal reason、Planner/Reviewer
  调用、terra/sol/repair/retry/cache、token、RWKV atoms/actions/rejections/overlap。
- 必须用同一 typed assertion/evidence replay 检查 artifact binding、content shadow、transaction
  integrity、terminal supersession；不得在运行后修改 replay 口径改善结果。
- 所有问题按 contract equivalence、evidence compiler、RWKV transaction、correction/finalizer、
  acceptance、relay/runtime 六类跨用例共同根因聚合；禁止 case-id 特判。

## Full90 晋级门

1. 90/90 有结果，running=0，未捕获 runtime failure=0，authoritative terminal=90/90。
2. strict TP>`41`，FP<=`9`，FN<=`1`；R126 36 个 TP 至少保留 34 个。
3. 分层 TP 至少 B/M/H/LH=`24/11/3/1`；不得用 basic 完成率掩盖 hard/LH 塌缩。
4. artifact inheritance=0、non-content shadow=0、completed transaction integrity violation=0。
5. logical strong calls<`373`，GPT total tokens<`1,727,942`；同时报告每 strict TP 成本。
6. Reviewer node/process fields=0，GPT tools=0，completed Final byte-exact=100%。

任一门失败，仍必须完成 90 例并保留全部结果；失败轮不得替换 R126 canonical baseline。
