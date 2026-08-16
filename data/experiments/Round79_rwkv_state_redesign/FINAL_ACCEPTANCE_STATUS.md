# Round79 final acceptance status

Date: 2026-08-14

## Completed

- Unified G1i model I/O and strict current-candidate parsing.
- Transactional ModelSession and five durable state lanes.
- Runtime-owned facts/evidence/worksets/checkpoints.
- Tokenizer-exact byte chunking and common-parent explicit-only parallel merge.
- Locked Task operation selection and sole-schema parameter binding.
- One ActionDefinition source for Harness declaration, validation and execution.
- Deletion of legacy role prompt/normalizer/recovery paths.
- Local regression: `71 passed`; unified control subset: `35 passed`.
- Final short7 r8 artifacts and causal analysis preserved.

## Not accepted

- Final r8 gate: Strict `0/7`, External `1/7`; required Strict was at least
  `4/7` with B01/B02/B10 all Strict.
- Full90 was intentionally not run.
- Large-code-31 real chunk/workset acceptance was not run.
- Prompt-replay lane rollover beyond 16k is not implemented.
- Native recurrent-state transport is unavailable.

## Stage

Architecture implementation and local regression are complete. Real canary
acceptance failed. The next work is a new general 16k lane-rollover and
operation-selection stability phase on a separately preregistered dataset, then
a new canary gate. Only after that gate passes may full90 and release readiness
begin.
