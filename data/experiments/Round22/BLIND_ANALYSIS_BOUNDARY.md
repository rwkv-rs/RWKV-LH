# Round22 盲态分析边界

冻结时间：2026-08-13，RWKV-E2E-90 全部 90 题封存之后、任何 Round22 标准答案对比之前。

- 原始 `results.json` SHA-256：
  `5dab26b4663ec340b29f3fadba8bd641c85b59ebd861c61e581e615ede981288`。
- 90/90 case 均已有 `audit.json`、`event_log.json`、`state_timeline.json` 和 `model_trace.json`。
- 盲态阶段只允许读取：`RUN_PROTOCOL.json`、`runtime_doctor.json`、`source_tree_manifest.json`、每题的
  public audit/event/state/model trace/workspace，以及此前已冻结的 Round21 盲态分析。
- 盲态阶段禁止解析 Round22 `results.json`、`REPORT.md`、任何 acceptance/reference/standard answer、
  `.verifier-private`、Round22 scorer 输出或 post-standard attribution。
- `results.json` 此时只按原始 bytes 计算 SHA-256，没有加载 JSON 内容。
- 盲态结论必须先冻结并记录自身 SHA-256，之后才能运行 `scripts/analyze_rwkv_round.py` 解封标准答案。
