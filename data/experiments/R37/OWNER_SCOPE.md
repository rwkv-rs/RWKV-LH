# R37 scope — 2026-09-21

Owner: “清理代码…入口都存在问题…完成之后进行数据管线的完成，完成之后就开始”.

Implement and test current direct actor entrypoints and offline DeepSeek pipeline, then start a bounded real pilot. Single reviewer plus real execution evidence is authorized; always label nonindependent. No training/evaluation restart, no duplicated zero baseline. Pilot uses 3 distinct existing production boundaries, at most 6 provider requests, shared estimated budget USD 2.00. Input peak cache-miss USD 0.30/M and output USD 1.20/M conservatively; official page verified 2026-09-21. A timeout retains its cost reservation and has no implicit retry.

This one-family retained trace is a pipeline pilot, not a complete training dataset. Source collector/server attestation, source isolation, immutable regression and registered coverage remain required before freeze. Do not invent these identities or lower the coverage thresholds to publish the pilot.

Final labels: one named semantic reviewer audits claims against exact visible input. Validator records actually executed ancestral tool events, requires grounded claims, and verifies snapshot integrity. A quoted span proves location, not truth or completeness; this is not two independent reviews. Labels are never marked execution-complete merely because generation returned.
