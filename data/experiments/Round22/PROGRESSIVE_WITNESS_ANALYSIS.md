# Round22 progressive witness analysis

Post-run and score-independent. Reads only model protocol traces, lifecycle events, Goal/task state, witness/proof state, and action paths; hidden acceptance/reference fields are not read.

- Mode requests/commits: 154 / 81; committed modes: `{"catalog_source": 70, "goal_literal": 11}`.
- Runtime-selected mode events: 0.
- Binding requests: 111; outcomes: `{"contract_error": 59, "ok": 52}`.
- Stage cases: `{"binding_compiled": 17, "completed": 0, "evidence_persisted": 0, "mode_committed": 21, "proof_passed": 0, "selection_started": 33}`.
- Proof-pass lineage: `{}`.
- Model-written same-target provenance rejections: 64 events across 12 cases.
- Prompt branch-disclosure violations: 0.

The analyzer reports progressive-protocol stages and provenance outcomes without selecting a mode, altering proof decisions, or rewriting model output.
