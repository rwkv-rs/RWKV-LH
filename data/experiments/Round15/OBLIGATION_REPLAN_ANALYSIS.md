# Round15 Goal-obligation replan contract analysis

Post-run and score-independent. Reads only RWKV protocol payloads and persisted request decisions; no hidden acceptance, external checks, user request, or reference answer.

- Requests: 146 across 53 cases.
- Outcomes: `{"contract_error": 27, "ok": 119}`.
- Top shapes: `{"other_object_with_new_tasks": 1, "other_object_without_new_tasks": 25, "semantic_minimum_new_tasks_only": 120}`.
- `new_tasks`-only: 120 requests across 49 cases.

All 120 `new_tasks`-only responses contain a non-empty task array of objects; 119 have ID/title/description on every task, and 116 bind every task to a criterion. This is only a structural precheck, not proof that the proposed tasks are correct. A future minimal envelope may parse these exact RWKV task objects, but must still apply every existing task, criterion, dependency, scope, and completion rule without filling or rewriting any semantic field.
