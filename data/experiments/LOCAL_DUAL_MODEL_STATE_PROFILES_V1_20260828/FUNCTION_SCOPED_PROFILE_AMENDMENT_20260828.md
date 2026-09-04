# Function-scoped State Profile amendment

Date: 2026-08-28 (Asia/Shanghai)

This amendment records an orchestration capability, not a change to any
already-started dataset, metric, threshold, similarity rule, checkpoint
selection rule, or RWKV-output contract.

## Decision

The profile cardinality is not capped at one Selector state and one Executor
state.  One model may register multiple immutable learned initial states, up to
one state per function when fixed ablation proves that sharing a state causes
cross-function interference.

Learned initial state and dynamic recurrent state are different identities:

- learned profile: immutable `profile_id + state SHA-256 + manifest SHA-256`;
- dynamic lane: append-only run/function lineage rooted in exactly one learned
  profile;
- a dynamic state may never resume under a different learned profile, model,
  role, function, or parent digest;
- Selector and Executor profiles and dynamic lanes are never imported into one
  another.

The vLLM-RWKV manifest already supports multiple profiles for one model and
requires each request to select a registered ID and matching SHA-256.  The
default remains `zero`; a tuned profile is never applied implicitly.  Separate
service instances may pin different profiles while sharing the same base-model
artifact, or a validated per-request deployment may choose among preloaded
profiles.  Neither path changes model weights or RWKV raw output.

## Numbering

- `NET-SEL-2P9-S0`: rejected zero-state Selector baseline.
- `NET-SEL-2P9-S1`: rejected broad Selector state.
- `NET-SEL-2P9-S2`: current 2K residual Selector candidate.
- future Selector split: `NET-SEL-2P9-S{n}-{function}`.
- `NET-EXE-13P3-N0`: retained general Executor profile
  `executor-stage8-r3-step1700`.
- future Executor residual: `NET-EXE-13P3-N{n}-{function}`.

`function` is a stable Harness operation ID such as `web_search` or
`connector_lookup`, or a registered phase ID such as `final` or `recovery`.
An artifact keeps its experiment number even when rejected; another state may
not reuse the number or overwrite its files.

## Fixed minimization order

1. Evaluate one shared profile for the role.
2. Cluster failures by function and causal phase on the same frozen evaluation
   set; do not create profiles from isolated examples.
3. Train only the smallest residual candidate that targets the observed
   cluster.
4. Compare shared versus split profiles using identical data, parameters,
   thresholds, similarity implementation, Harness regression, and raw-output
   integrity checks.
5. Keep the split only when it resolves the registered cluster without new
   cross-function regression and its state load/restore latency remains within
   the preregistered service budget.

This permits one-function-one-state at the architectural limit while making
the smallest passing profile set the deployment default.

## Current deployment status

No function-scoped profile is enabled by this amendment.  `NET-SEL-2P9-S2`
must first pass its frozen internal, ECRA120, state-causality, state-isolation,
full-suite, and networking gates.  `NET-EXE-13P3-N0` is unchanged.  Executor
network residual tuning and any further function split require a new
preregistration and do not inherit a Selector pass automatically.
