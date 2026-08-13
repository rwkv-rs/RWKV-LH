# Round20 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 91 across 43 cases.
- Appended tasks: 451.
- Semantically repeated task instances: 275 across 31 cases.
- Exactly repeated semantic proposal multisets: 9 across 8 cases.
- Final obligation states: `{"blocked": 9, "exhausted": 25, "resolved": 1, "unresolved": 8}`.
- Cases with persisted CriterionEvidence: 6.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
