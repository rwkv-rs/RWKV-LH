# Infrastructure-invalid classification

- Case: `PUBLIC-CANARY-B01-S20260902`
- Planner: `gpt-5.6-sol` through Responses API.
- Capability score: invalid; no RWKV model request or action occurred.

The relay returned HTTP 400 before inference with
`invalid_request_error`: Responses `json_object` requires the input message to
contain the word `json`. The serialized PlanPatch payload was valid JSON but
did not contain that literal English cue. This is a transport-envelope defect,
not a model capability result.

The fixed envelope adds `JSON request payload:\n` before the otherwise
byte-identical serialized user payload. It does not generate, delete, reorder,
or repair any semantic field.

## Integrity

- `RESULT.json`: `2cc7cd7b81a2ca125365846cf04d627b63460acaff33314f392eda35ed600394`
- `CASE/audit.json`: `77a0b0cb69220734f93c3f1a804350c951dd322fdd9682c2faa3dca04a429b92`
