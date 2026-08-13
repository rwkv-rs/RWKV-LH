# Round21 标准答案解封前因果综合

## 分析边界

Generated after frozen Round21 E2E-90 termination and before standard-answer scoring. Inputs are limited to lifecycle, protocol, task graph, action, memory, obligation, witness, proof, state, lineage, and suppression artifacts. No external_passed, verifier observation, delivered answer, reference answer, or standard answer is read.

## 结论

Round21 rejected 33 proof events whose expected side was a read snapshot taken after an audited model mutation to the same target, in addition to 90 direct model-mutation lineage events. Two read-only same-target assertions without an established earlier mutation still passed.

No run reached completion and only two cases persisted proof evidence. This rule improves completion provenance but is not a producer-capability improvement. It must not be counted as better task solving before external scoring.

Across 14 cases, all 26 dependent same-target mutation chains transferred the prior write through dependency memory only as 'JSON written' or 'file written'. The later RWKV task receives an artifact id but not the written value in its dependency observation. This is an architectural information-loss candidate, not a statement about answer correctness.

The unchanged gate suppressed 22 complete RWKV proposals across 12 cases. Compared with Round20, saved replans fell by 15, appended tasks by 109, duplicate instances by 98, and model requests by 324; nevertheless 25 cases still exhausted the obligation budget and proof feedback produced 123 lineage reject events.

## Round20 → Round21 阶段变化

- selection started：41 → 43。
- binding compiled：28 → 29。
- proof passed：6 → 2。
- evidence persisted：6 → 2。
- completed：1 → 0。
- model requests：2960 → 2636（-324）。

## 下一项能力假设（未实现）

Preserve observable write-result state across task boundaries without generating or changing values: after a successful workspace mutation, capture the exact post-action artifact snapshot/hash as an audited observation and make its bounded content available to dependent RWKV producer tasks. RWKV must still choose every later action and value. Validate first against all 26 chains and only then run a new fixed E2E-90 round.

该假设不把 artifact 内容当成答案，也不替 RWKV 选择后续写入；它只让 RWKV 看见自己已完成动作的真实可审计结果。
