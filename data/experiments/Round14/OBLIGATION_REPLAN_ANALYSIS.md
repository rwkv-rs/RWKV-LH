# Round14 Goal-obligation replan contract analysis

Post-run and score-independent. Reads only RWKV protocol payloads and persisted request decisions; no hidden acceptance, external checks, user request, or reference answer.

- Requests: 204 across 52 cases.
- Outcomes: `{"contract_error": 131, "ok": 73}`.
- Top shapes: `{"exact_v1_envelope": 77, "other_object_with_new_tasks": 5, "other_object_without_new_tasks": 39, "semantic_minimum_new_tasks_only": 83}`.
- `new_tasks`-only: 83 requests across 43 cases.

All 83 `new_tasks`-only responses contain a non-empty task array of objects; 82 have ID/title/description on every task, and 77 bind every task to a criterion. This is only a structural precheck, not proof that the proposed tasks are correct. A future minimal envelope may parse these exact RWKV task objects, but must still apply every existing task, criterion, dependency, scope, and completion rule without filling or rewriting any semantic field.
