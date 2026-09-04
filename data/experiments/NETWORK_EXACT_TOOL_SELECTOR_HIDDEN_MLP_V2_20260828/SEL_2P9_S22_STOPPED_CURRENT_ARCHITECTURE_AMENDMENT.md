# NET-SEL-2P9-S22 stopped-current-architecture amendment

Date: 2026-08-28 (Asia/Shanghai)

## Status

S22 was stopped before feature extraction completed and has no valid result.
It projected the historical S6 corpus into Planner-style atomic objectives, but
the current product target is the existing direct `LongHorizonModel` Harness:
one persistent Executor action lane, action-result events, progressive tool
disclosure, and direct next-operation selection.  A future Planner boundary is
not an admissible substitute for that architecture or its regression metric.

The extraction was interrupted after 1,760 of 9,076 rows.  The append-only
partial cache contains 110 contiguous 16-row feature shards under
`run_s22_atomic_objective_features/features/`, from
`features_00000_00016.pt` through `features_01744_01760.pt`.  It is retained as
an invalid/aborted artifact; it must not be completed, scored, trained on, used
to select a head/state, or treated as evidence for current integration.

## Current admissible boundary

The current first configuration remains two persistent role states:

- 2.9B Selector: current task/stage intent, frozen tool names/descriptions, and
  a compact operation/outcome/progress projection of the shared causal chain;
- 13.3B Executor: selected operation, the one complete tool schema, exact
  execution target, and the existing bounded action-result projection.

Both lanes keep independent runtime checkpoints and state-tuning profile
identities.  Harness execution authority, action-result facts, progressive
schema disclosure, and the 13.3B raw generation path remain unchanged.  The
Selector replacement is evaluated on the same full direct-Harness ECRA and
historical non-network regression surfaces as the current architecture.

