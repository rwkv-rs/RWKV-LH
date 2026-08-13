# Round15 obligation amplification analysis

Post-run and score-independent. Only obligation, task, model-request, action, proof, and persisted-state fields are read.

- Saved replans: 115 across 47 cases.
- Appended tasks: 440.
- Semantically repeated task instances: 263 across 36 cases.
- Exactly repeated semantic proposal multisets: 22 across 18 cases.
- Final obligation states: `{"blocked": 9, "exhausted": 27, "unresolved": 11}`.
- Cases with persisted CriterionEvidence: 5.

The semantic-repeat metric excludes local task IDs and dependencies but preserves title, description, and criterion bindings. It diagnoses repeated RWKV planning intent; it does not merge, suppress, or select tasks at runtime.
