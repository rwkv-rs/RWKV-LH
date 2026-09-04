# Menu policy and path-operation attribution

## Integrity

- Selector records: 880
- Stored selection/raw-logit argmax exact: True
- SQLite access: `mode=ro&immutable=1`
- RWKV raw outputs modified: false

## Offline policy attribution

- Offline network selections: 50
- Offline selections changed by the corrected eligibility mask: 50
- Immediate counterfactual operations: `{"calculator":12,"file_digest":12,"final_answer":8,"search_text":18}`
- This is an immediate stored-logit counterfactual only; downstream execution was not replayed or scored.

## JSON path attribution

- JSON operation selections: `{"patch_json":17,"write_json":132}`
- JSON action roots: `{"patch_json:non_json_only":15,"write_json:json_only":2,"write_json:non_json_only":127}`
- JSON action suffixes: `{"patch_json:.css":1,"patch_json:.html":2,"patch_json:.js":1,"patch_json:.md":2,"patch_json:.py":8,"patch_json:.toml":1,"write_json:.css":15,"write_json:.html":12,"write_json:.js":11,"write_json:.json":2,"write_json:.md":45,"write_json:.py":43,"write_json:.toml":1}`
- No suffix-based mask is authorized: the current atom contract has no authoritative media-type field.
