# Local-native engineering remediation v1 preregistration

- Date: 2026-08-27
- Scope: only the local RWKV-LH product path and its configured strong Planner/Reviewer.
- Candidate RWKV runtime: `rwkv7-g1i-13.3b-rwkv-lh-stage7-step2000-bos-ctx2496`.
- Network policy for Contract Graph canary: `offline`.
- Evaluation: mechanical exact fields and append-only trace events; no post-run threshold changes.

## Frozen cases and acceptance thresholds

1. `HEALTH-MODEL-IDENTITY`: an endpoint whose `/models` omits the configured model must report `available=false`; an exact model match must report `available=true`. Threshold: 2/2 unit cases.
2. `USER-LITERAL-PROVENANCE`: `requests`, when present in the immutable user request and later echoed by a provider result, remains `user_public_literal`; secret-shaped input remains `secret`. Threshold: 2/2 unit paths and no policy rejection for the repeated public literal.
3. `CONNECTOR-CAPABILITY`: the product schema exposes exactly the locally implemented public structured operations and excludes `github_code` and `weather_alerts`. Threshold: exact enum equality.
4. `PRESENTATION-BOUNDARY`: create `report.json` containing exactly `{"mode":"hybrid","verified":true}`, read it back, then return a concise confirmation. Threshold: completed run; exact JSON content; at least one mutation and one dependent read; no work/correction node bound to a `final_presentation` obligation; final output non-empty.
5. `PARENT-TRACE`: Contract Graph parent status projects all committed child actions and RWKV request counts without copying them into a second mutable action store. Threshold: projected atom action count equals the sum in committed outcomes and is non-zero.

## Regression gates

- Targeted runtime/retrieval/Contract Graph/Web/CLI suites all pass.
- Full `uv run pytest -q -s` passes.
- `git diff --check` passes.

The state-router remains disabled/shadow-only and is not a completion dependency for this remediation.
