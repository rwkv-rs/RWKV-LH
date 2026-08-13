# Round19 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 112 across 45 cases.
- Appended tasks: 461.
- Semantically repeated task instances: 293 across 39 cases.
- Exactly repeated semantic proposal multisets: 19 across 14 cases.
- Final obligation states: `{"blocked": 9, "exhausted": 28, "unresolved": 8}`.
- Cases with persisted CriterionEvidence: 5.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
