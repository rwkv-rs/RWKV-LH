# Network-policy result projection v1 protocol — 2026-08-26

## Root cause

The authoritative failed `web_search` ActionResult contains
`metadata.network_policy.controller_rewritten=false`, but the bounded RWKV decision-state
projection drops the complete `network_policy` mapping because it is absent from
`LongHorizonModel._RESULT_METADATA_KEYS`. The compact JSON output retains the fact only
as an escaped string, which does not satisfy the typed metadata projection contract.

## Single variable and threshold

Add `network_policy` to the existing exact metadata allowlist. Do not synthesize or
rewrite any field. The pre-existing progressive network-policy regression must observe
the exact `"controller_rewritten": false` typed fact, and all targeted/full tests must
pass.
