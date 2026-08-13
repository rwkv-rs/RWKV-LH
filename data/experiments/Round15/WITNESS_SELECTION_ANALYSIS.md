# Round15 witness-selection contract analysis

Post-run and score-independent. Reads only model traces, lifecycle events, and persisted request decisions; no hidden acceptance or reference fields.

- Requests: 729 across 42 cases.
- Outcomes: `{"contract_error": 663, "ok": 65, "protocol_error": 1}`.
- Optional reason: `{"omitted": 721, "provided": 8}`.
- Optional item note: `{"omitted": 797, "provided": 245}`.
- Compiled cases: 20; proof-passed cases: 5.

## Expected-side branch shapes

| Parsed branch shape | Items | Requests containing shape |
| --- | ---: | ---: |
| `conflicting_catalog_source_plus_literal` | 776 | 515 |
| `goal_literal_only` | 171 | 149 |
| `catalog_source_only` | 83 | 53 |
| `catalog_source_with_nonobject_literal` | 12 | 6 |

## Interpretation

Making reason and note optional removed explanatory-field failures without supplying or rewriting RWKV semantics. The remaining dominant failures are expected-side representation and source eligibility decisions: a model response often supplies both a catalog handle and a Goal literal, or selects a handle that is not expected-eligible. Those fields are not silently dropped or repaired.
