# Round17 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 115 across 48 cases.
- Appended tasks: 448.
- Semantically repeated task instances: 295 across 38 cases.
- Exactly repeated semantic proposal multisets: 23 across 18 cases.
- Final obligation states: `{"blocked": 9, "exhausted": 29, "unresolved": 10}`.
- Cases with persisted CriterionEvidence: 1.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
