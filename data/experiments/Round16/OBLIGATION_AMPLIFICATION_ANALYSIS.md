# Round16 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 129 across 48 cases.
- Appended tasks: 496.
- Semantically repeated task instances: 329 across 43 cases.
- Exactly repeated semantic proposal multisets: 26 across 22 cases.
- Final obligation states: `{"blocked": 3, "exhausted": 38, "unresolved": 7}`.
- Cases with persisted CriterionEvidence: 1.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
