# Round21 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 76 across 37 cases.
- Appended tasks: 342.
- Semantically repeated task instances: 177 across 23 cases.
- Exactly repeated semantic proposal multisets: 14 across 12 cases.
- Final obligation states: `{"blocked": 6, "exhausted": 23, "unresolved": 8}`.
- Cases with persisted CriterionEvidence: 1.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
