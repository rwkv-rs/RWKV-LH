# Round108 manual causal analysis

## Fixed result

- Strict/Agent/External: fail/fail/fail.
- 36 requests, 1 Task, 0 Attempts, 0 repairs.
- Final was non-empty raw RWKV output.

## Chain

1. Collection guidance changed the Goal topology from eight service Tasks to one discovery
   Task. This confirms that the weak model can respond to the disclosed grouping pattern.
2. RWKV did not choose `collection_listing`; it declared `file_content_read` evidence for a
   new `discovery_report.json` output and selected `list_directory("services")` first.
3. The Round106 subject guard treated the final evidence subject as if it were the only
   legal input path and rejected the directory listing. RWKV then spent the Task protocol
   budget trying many list-directory representations; none executed.
4. The run blocked with no Attempt and no workspace change.

## Conclusion

The single-subject guard is architecturally invalid for composite Tasks: final completion
evidence is not an input-scope declaration. It must be removed. Any future input boundary
must come from an explicit RWKV-declared workset/input set rather than inference from
`evidence_subject`.
