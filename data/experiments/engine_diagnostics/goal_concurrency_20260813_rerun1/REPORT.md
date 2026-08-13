# Goal concurrency diagnostic result

## Result

| Client concurrency | Valid Goal | Invalid | Requests | Transport failures | Duration |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 29/30 | 1 | 32 | 0 | 141.3s |
| 2 | 29/30 | 1 | 32 | 0 | 79.4s |
| 4 | 28/30 | 2 | 32 | 0 | 49.0s |
| 8 | 30/30 | 0 | 30 | 0 | 26.4s |

Across 120 condition-cases, `116/120` produced a valid Goal. All `126/126` model requests returned
with finish reason `stop`, and all `126/126` responses contained a parseable JSON object. There were
no transport failures and no incomplete-JSON/parser failures.

## Failures

| Concurrency | Task | Criteria per attempt | Terminal error |
| ---: | --- | --- | --- |
| 1 | E2E-B12 | [8, 8] | `ModelProtocolError: goal proposal has 8 criteria; maximum is 5` |
| 2 | E2E-B12 | [8, 8] | `ModelProtocolError: goal proposal has 8 criteria; maximum is 5` |
| 4 | E2E-B09 | [9, 9] | `ModelProtocolError: goal proposal has 9 criteria; maximum is 5` |
| 4 | E2E-B12 | [8, 8] | `ModelProtocolError: goal proposal has 8 criteria; maximum is 5` |

All four failures were RWKV semantic-contract failures: it returned 8 or 9 success criteria despite
the 1--5 instruction, and repeated the oversized list after correction. They were not response
truncation or JSON corruption. Two other first-attempt oversized cases recovered on the existing
second request. No output was selected or repaired.

## Interpretation

The preregistered concurrency-degradation hypothesis is not supported. Concurrency 8 was best at
`30/30`; validity was not monotonic with concurrency. The pre-restart `61/90` Goal-stage failure run
therefore should be attributed to that engine/forwarding instance until stronger evidence says
otherwise, not to general RWKV inability under concurrent requests.

This does not prove that the model is strong enough for Agent work. It only proves that the restarted
endpoint can produce the frozen Goal protocol reliably on this Basic-30 panel. A fresh unchanged
Round12 E2E-90 control is still required before any Round13 architecture attribution.

## Integrity

- Aggregate results SHA-256: `c30a65563f11aa65ed75d7c1f559c4183a8af098bbc4ea4ddba0c0f2dbd55e74`
- Durable case results checked: `120/120`
- Durable traces checked: `120/120`
- Integrity errors: `0`
- Manifest: `integrity_manifest.json`
