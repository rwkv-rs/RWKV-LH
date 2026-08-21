# R130 WSL resource-stability amendment

**Recorded:** 2026-08-19, before the successor run's first model request.

## Evidence and disposition

Two concurrency-5 Full90 attempts ended when the local WSL environment crashed under load:

- the first attempt persisted 37/90 results and is closed as
  `Round130_order_ensemble_INVALID_WSL_RESOURCE_CRASH_37of90`;
- the retry persisted 35/90 results and is closed as
  `Round130_order_ensemble_INVALID_WSL_RESOURCE_CRASH_35of90_20260819`.

Neither partial run is scored, resumed, or used in any architecture decision. Their artifacts remain
read-only infrastructure evidence.

## Successor run

The successor is a fresh source-frozen Full90 in
`Round130_order_ensemble_full90_concurrency2_official_20260819` with:

- case concurrency **2**, reduced from 5;
- at most **6** simultaneous K=3 physical model requests, reduced from 15;
- a systemd CPU quota of **400%**;
- systemd `MemoryHigh=12G` and `MemoryMax=16G`, so the benchmark is contained before WSL-wide memory
  pressure can terminate the environment;
- a distinct output directory created by the runner; no old artifacts are copied into it.

The concurrency and systemd limits alter only local scheduling and containment. Model, frozen source,
suite, prompts, K=3 order ensemble, sampling, maximum transitions, external acceptance, scoring,
thresholds, and protocol red lines remain unchanged from
`Round130_ORDER_SHUFFLED_SELF_CONSISTENCY_PROTOCOL.md`.

The successor is valid only if it reaches 90/90 persisted results with zero running cases. Any local
unit failure or WSL restart closes that attempt as infrastructure-invalid before scoring.
