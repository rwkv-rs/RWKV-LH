# Round70 preregistered protocol: fixed semantic review tools

## Frozen evidence

- Round68 fixed15: `0/15`, dominated by copied review schemas.
- Round69 fixed15: `0/15`, dominated by arbitrary review schema values after
  semantic projection.
- Round69 offline: pytest `425/425`, LH-Control `30/30`, frozen subset `5/5`.

## Preregistered changes

### Fixed Goal review tool

Goal audit uses one fixed G1i tool `review_goal`. Its arguments are exactly
`decision`, `reason`, `omissions`, `inventions`, `redundancies`. There is no
model-generated schema argument. Exact bare arguments are accepted only at this
uniquely fixed boundary and normalized to the fixed tool name with raw/normalized
audit records.

### Fixed action review tool

Action review uses one fixed G1i tool `review_action`. Its arguments are exactly
`decision=approve|revise` and `reason`. The same closed bare-argument rule applies.

The old free-JSON review paths and schema-alias code are removed, leaving one
production review path per stage. RWKV still owns every semantic review field.

## Non-intervention

The fixed tool name identifies the already selected pipeline stage; it does not
choose a semantic result. Controller code validates types and exact fields but
does not change review decisions, issues or reasons. Goal finalization and action
revision remain fresh RWKV outputs. Hidden acceptance remains unavailable.

## Validation/gate

- Full pytest, LH-Control `30/30`, frozen subset `5/5`, compile/diff checks.
- Fixed-tool canonical/bare/unknown-field tests and proof that no review-schema
  aliases remain in production.
- Unchanged fixed15 gate and full90/upload gates from Round69.
- Efficiency remains audit-only.
