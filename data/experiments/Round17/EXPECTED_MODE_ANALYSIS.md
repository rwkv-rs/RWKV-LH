# Round17 expected-mode analysis

Post-run and score-independent. Reads only parsed RWKV witness-selection payloads, persisted request decisions, lifecycle events, and persisted evidence state.

- Requests: 657 across 39 cases.
- Outcomes: `{"contract_error": 642, "ok": 15}`.
- Selection-shape classes: `{"read_operator_used_as_mode": 8, "source_kind_used_as_mode": 242, "unknown_mode": 71, "valid_catalog_mode_shape": 35, "valid_goal_mode_shape": 29, "valid_mode_wrong_fields": 622}`.
- Compiled/proof/persisted-evidence cases: 4 / 1 / 1.

The analyzer reports exactly what RWKV emitted. It does not alias source kinds into modes, drop fields, select a branch, inspect hidden acceptance, or modify any runtime decision.
