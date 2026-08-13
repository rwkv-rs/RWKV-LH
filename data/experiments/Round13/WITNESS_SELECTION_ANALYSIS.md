# Round13 witness-selection contract analysis

This analysis is post-run and score-independent: it reads model traces, lifecycle events, and persisted request decisions only, not hidden acceptance or Codex references.

- Selection requests: 355 across 34 cases.
- Outcomes: `{"contract_error": 348, "ok": 6, "protocol_error": 1}`.
- Parsed semantic decisions: `{"": 3, "pass": 352}`.
- Exact-top-level mismatches: 209.

## Exact-top-level mismatch anatomy

| Parsed top-level keyset | Count |
| --- | ---: |
| `decision,schema_version,witness_selections` | 203 |
| `decision,reason,schema_version` | 4 |
| `actual_source_handle_id,expected_goal_literal,expected_source_handle_id,note,task_id` | 1 |
| `criterion_id,expected_goal_literal,expected_source_handle_id,note` | 1 |

| Missing key set | Count |
| --- | ---: |
| `reason` | 203 |
| `witness_selections` | 4 |
| `decision,reason,schema_version,witness_selections` | 2 |

## Interpretation

The exact-key error is separated from source/Goal/proof errors. Missing an administrative field is not treated as a wrong RWKV source choice, and accepting it would not authorize the runtime to infer or replace any selection. Conversely, invalid Goal quotes and unknown WS IDs remain semantic/evidence-binding failures and are not repairable by dropping a redundant field.
