# Historical store read incident

Date recorded: 2026-08-30

## Scope

During reconciliation, one historical A-arm worker database was accidentally
opened through `LongHorizonStore.load` instead of immutable SQLite access.  The
load recovery path appended exactly one event after the already terminal run:

- database:
  `run_a_legacy_selector_view_v1/cases/AGENT-LADDER-L1-FIX01/atom_workers/CONTRACT-BATCH-d116601db647c217e50d/read-pricing/state/long_horizon.db`
- current database SHA-256:
  `9d6421219b80056e69f3b3dccf294c36e615a73a536ad4a95bb1d389b45f2277`
- appended revision: `21`
- event type: `snapshot_recovered`
- payload: `{"checkpoint_revision":4,"corrupt_current_revision":20}`
- preceding terminal event: revision `20`, `run_completed`

No pre-existing event, model decision, raw RWKV output, action, audit JSON, or
workspace artifact was changed or deleted.  The case audit SHA-256 remains
`7d2472a14f4bdc036af521f177046cc314526a833a82bbdfbb8a598a0e3918b3`.
The appended recovery event is not included as a model generation or action in
the reconciled metrics.

## Containment

All subsequent diagnosis scripts open event stores only with SQLite
`mode=ro&immutable=1`.  Historical experiment stores must not be inspected via
`LongHorizonStore.load`.  The verification script is
`temp/inspect_snapshot_recovered_incident_v1_20260830.py`, SHA-256
`6433d62740669abb1075aa1bb3ceaaca2bd2ad0337d45b175c106f85d4b2c52d`.

The database is retained as-is to preserve the incident trail; no event was
removed or rewritten.
