# Engineering-invalid classification

- Case: `PUBLIC-CANARY-B01-S20260902`
- Planner: `gpt-5.6-sol` through Responses API.
- Capability score: invalid; the harness crashed before a terminal result.

The GPT Planner completed successfully and RWKV executed two actions. While
recovering from a model protocol rejection, the current G1J Selector projection
scanned the full action history (correct for its per-boundary initial State) but
serialized one `succeeded_operations` entry per action. Repeating
`list_directory` therefore produced duplicate operation-kind values and failed
the registered unique-array protocol with:

`ValueError: progress.succeeded_operations must contain unique values`

The systemic correction preserves first-observation order while projecting
unique operation kinds. Real action cardinality remains unchanged in
`completed_stage_count` and `action_index`. Both success and failure lists, and
both local and network SelectorProgress boundaries, now enforce the same
invariant.

## Integrity

- `RESULT.json`: `cecbd068df10d95262c80d0b6f209cf25c04a62e844f33d4df50bd41167d175b`
- `CASE/audit.json`: `7dff268a3fc15aa6d7c1ec35c9675c73fd893e6f46ea2a843cbdc339561cb8b6`
- Regression: 103 relevant tests passed after the correction.
