# Round18 progressive witness analysis

Post-run and score-independent. Reads only model protocol traces, lifecycle events, Goal/task state, witness/proof state, and action paths; hidden acceptance/reference fields are not read.

- Mode requests/commits: 250 / 160; committed modes: `{"catalog_source": 130, "goal_literal": 30}`.
- Runtime-selected mode events: 0.
- Binding requests: 260; outcomes: `{"contract_error": 196, "ok": 64}`.
- Stage cases: `{"binding_compiled": 22, "completed": 1, "evidence_persisted": 6, "mode_committed": 28, "proof_passed": 6, "selection_started": 34}`.
- Proof-pass lineage: `{"same_workspace_target_snapshot": 13}`.
- Prompt branch-disclosure violations: 0.

Progressive disclosure improved protocol compilation, but exact equality against a prior artifact of the same model-written workspace target is consistency evidence, not independent Goal correctness. That lineage class is reported, not rejected or rewritten by this post-run analyzer.
