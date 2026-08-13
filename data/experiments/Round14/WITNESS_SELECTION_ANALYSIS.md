# Round14 witness-selection contract analysis

Post-run and score-independent. Reads only model traces, lifecycle events, and persisted request decisions; no hidden acceptance or reference fields.

- Requests: 507 across 38 cases.
- Outcomes: `{"contract_error": 471, "ok": 36}`.
- Optional reason: `{"omitted": 506, "provided": 1}`.
- Optional item note: `{"omitted": 555, "provided": 211}`.
- Compiled cases: 19; proof-passed cases: 5.

## Expected-side branch shapes

| Parsed branch shape | Items | Requests containing shape |
| --- | ---: | ---: |
| `conflicting_catalog_source_plus_literal` | 578 | 376 |
| `goal_literal_only` | 141 | 92 |
| `catalog_source_only` | 47 | 36 |

## Interpretation

Making reason and note optional removed explanatory-field failures without supplying or rewriting RWKV semantics. The remaining dominant failures are expected-side representation and source eligibility decisions: a model response often supplies both a catalog handle and a Goal literal, or selects a handle that is not expected-eligible. Those fields are not silently dropped or repaired.
