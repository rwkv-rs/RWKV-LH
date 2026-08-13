# Round16 expected-witness union analysis

Post-run and score-independent. Reads only parsed RWKV witness-selection payloads, persisted request decisions, and lifecycle event counts.

- Requests: 726 across 39 cases.
- Outcomes: `{"contract_error": 704, "ok": 9, "protocol_error": 13}`.
- Expected-shape classes: `{"read_operator_used_as_union_discriminator": 27, "source_kind_used_as_union_discriminator": 814, "valid_catalog_union": 10, "valid_goal_union": 172, "valid_kind_wrong_fields": 52}`.
- Compiled/proof-passed cases: 4 / 1.

The dominant failure is not an ambiguous runtime choice. RWKV used concrete source kinds such as workspace/action_output/action_result as the union discriminator and often copied source-catalog or expected-value fields into the branch object. The runtime rejected these objects without aliasing the kind, dropping fields, or selecting a branch.
