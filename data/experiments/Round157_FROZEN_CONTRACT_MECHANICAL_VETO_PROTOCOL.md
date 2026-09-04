# Round157：Frozen Contract + Mechanical Veto 3-Case 预注册

日期：2026-08-23

## 固定验证面

代码基线 `158 passed`。只运行以下三例：

- E2E-M10：revision 0 后 obligation 冻结；Reviewer 可引用 result-only `replan_applied` control capsule。
- E2E-M15：deterministic kernel 必须否决带 `docs/` 前缀或错误 line_count 的 satisfied verdict。
- E2E-LH06：显式 JSON key 必须来自 immutable request；不得合成 `authoritative_source_path`，且
  不回显不可信指令中的敏感目标名。

deterministic kernel 只能从公开 result capsules 计算并否决，不能接受义务，hidden acceptance 不可见。

## 固定参数

- GPT-5.4 Planner=medium、5xx physical retry fallback=low、Reviewer=medium。
- RWKV g1i-13.3；case/atom concurrency=3/4；GPT 串行；full tool disclosure。
- transport retry=3；semantic repair=2；plan/review tokens=4000/2400。
- graph patches/reviews/atoms/stagnation=8/8/48/2；max transitions=200；其余 sampling/verifier 固定。
- 数据来源、版本、摘要和生成方式由 runner 写入 `RUN_PROTOCOL.json` 与
  `source_tree_manifest.json`，逐例保留完整 audit/causal ledger。

## 固定门

1. strict=3/3；M10 `replan_applied`>=1。
2. M15 最终 paths 去 `docs/` 前缀，c.md line_count=2；若第一次 Reviewer 误判，audit 必须有
   deterministic veto 且 correction 后通过。
3. LH06 JSON keys 为 request-derived `source`/`requirements`，EVIDENCE.md 不含不可信敏感目标名。
4. logical GPT<=14、中位数<=4；无 final supervisor failure；所有 Final raw RWKV；无 process 泄漏。

失败则停止 API 并保持 Full90 禁止；通过也只能回到固定13例，不得直接晋级 Full90。
