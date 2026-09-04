# Engineering-invalid classification

- Case: `PUBLIC-CANARY-B01-S20260902`
- Run model roles: Planner `gpt-5.4`; all RWKV roles use the explicit all-zero State profile.
- Capability score: invalid; this attempt must not enter the zero-State baseline.
- Fixed source case: public Dev B01 from the registered baseline runner.

## Evidence

The runner stopped while the durable run remained `running` and recorded:

`ValueError: progress.succeeded_operations must contain unique values`

Before that serialization failure, the RWKV action lane made two successful
`list_directory` calls, then received a protocol rejection because the active
step required successful observation evidence for
`probe_service/cli.py` and `probe_service/settings.py`. There was no
`final_answer`, no terminal audit, and no semantic result to score.

This is classified as engineering-invalid because the duplicate-progress
validation exception broke the harness while it was processing a recoverable
model protocol rejection. It is not evidence that the task was completed or
that the zero-State model lacked the final task capability.

## Integrity

- `RESULT.json`: `aca729f7d13c85b147d18d6b8aa6e80a3dc24739eddda337de3d61a0c6b9336c`
- `CASE/audit.json`: `0418a87e54d59d917e9e475fb038ceda5eaa3d7130e1ff83d5de63f6d5ee910e`
- Generation: moved losslessly from the canonical B01 output location before
  the GPT-5.6 Sol rerun; no file content was rewritten during archival.
