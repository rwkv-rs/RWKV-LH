# Round21 progressive witness analysis

Post-run and score-independent. Reads only model protocol traces, lifecycle events, Goal/task state, witness/proof state, and action paths; hidden acceptance/reference fields are not read.

- Mode requests/commits: 265 / 142; committed modes: `{"catalog_source": 120, "goal_literal": 22}`.
- Runtime-selected mode events: 0.
- Binding requests: 210; outcomes: `{"contract_error": 131, "ok": 79}`.
- Stage cases: `{"binding_compiled": 29, "completed": 0, "evidence_persisted": 2, "mode_committed": 39, "proof_passed": 2, "selection_started": 43}`.
- Proof-pass lineage: `{"read_only_same_workspace_target_snapshot": 2}`.
- Model-written same-target provenance rejections: 123 events across 19 cases.
- Prompt branch-disclosure violations: 0.

The analyzer reports progressive-protocol stages and provenance outcomes without selecting a mode, altering proof decisions, or rewriting model output.
