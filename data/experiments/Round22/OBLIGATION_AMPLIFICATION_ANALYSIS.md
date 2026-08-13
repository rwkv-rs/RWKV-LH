# Round22 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 50 across 26 cases.
- Appended tasks: 214.
- Semantically repeated task instances: 119 across 15 cases.
- Exactly repeated semantic proposal multisets: 4 across 3 cases.
- Final obligation states: `{"blocked": 1, "exhausted": 15, "unresolved": 10}`.
- Cases with persisted CriterionEvidence: 0.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
