# Round153 Split Reasoning + Literal Review B04 分析

日期：2026-08-23

## 结论

Round153 **PASS**。B04 strict、external、agent completion 和 Final non-intervention 全部通过，可恢复固定
13 题 Contract Graph canary。

原始目录：`data/experiments/Round153_split_reasoning_literal_review_B04_20260823/`。

## 量化结果

- GPT：2 logical calls / 2 physical HTTP attempts；Planner、Reviewer 各一次，无 semantic repair/HTTP 500。
- Planner：1542 prompt / 880 completion / 64 reasoning tokens，18.3 秒。
- Reviewer：8583 prompt / 899 completion / 551 reasoning tokens，18.1 秒。
- RWKV：12 requests、6 actions、0 protocol rejection；6 outcomes、4 deterministic batches。
- exact checks：source/destination SHA256 均为 `40c095...af16`；manifest exact
  `archive/2026/source.txt\n`。
- Final byte-exact raw RWKV；GPT tools=0；controller_rewritten=false。

说明“低推理 Planner + 中推理证据 Reviewer”在不增加常规调用数的前提下，同时满足网关时限和精确
审核。全项目回归：151 passed。
