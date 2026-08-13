# Round18 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 102 across 46 cases.
- Appended tasks: 431.
- Semantically repeated task instances: 250 across 33 cases.
- Exactly repeated semantic proposal multisets: 21 across 15 cases.
- Final obligation states: `{"blocked": 8, "exhausted": 20, "resolved": 1, "unresolved": 17}`.
- Cases with persisted CriterionEvidence: 6.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
