# Round20 progressive witness analysis

Post-run and score-independent. Reads only model protocol traces, lifecycle events, Goal/task state, witness/proof state, and action paths; hidden acceptance/reference fields are not read.

- Mode requests/commits: 281 / 171; committed modes: `{"catalog_source": 131, "goal_literal": 40}`.
- Runtime-selected mode events: 0.
- Binding requests: 291; outcomes: `{"contract_error": 235, "ok": 56}`.
- Stage cases: `{"binding_compiled": 28, "completed": 1, "evidence_persisted": 6, "mode_committed": 37, "proof_passed": 6, "selection_started": 41}`.
- Proof-pass lineage: `{"read_only_same_workspace_target_snapshot": 11}`.
- Model-written same-target provenance rejections: 54 events across 14 cases.
- Prompt branch-disclosure violations: 0.

The analyzer reports progressive-protocol stages and provenance outcomes without selecting a mode, altering proof decisions, or rewriting model output.
