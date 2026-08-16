# Round62 fixed-15 manual causal analysis

## Frozen outcome

- Strict E2E: `2/15`
- External acceptance: `4/15`
- Agent completed: `3/15`
- FP: `1` (`M06`)
- FN: `2` (`M01`, `M12`)
- LH02 model requests: `381`; state database: `608,026,624` bytes

The preregistered Strict and FN gates failed. Full90 was not run and this candidate is not upload-eligible.

## What the ablation proved

- **B02** changed from external-only to Strict. Independent GC1/GC2/GC3 relations avoided the missing-array and obligation fallback chain.
- **M18** changed from FP to correctly blocked. A directory listing containing `b.json` could no longer be hidden by one all-criteria array attached to a one-entry digest map.
- **M12** improved from verified `{GC2,GC3}` to `{GC2,GC3,GC4,GC5,GC6}`. GC1 alone remained unresolved.
- **M06** remained FP. Even when GC2/GC4/GC5 were judged independently, RWKV treated manifest keys as proof that files had been copied and that the package contained no other files.
- **M01** was externally correct in this sample because the plan read all three source files, but became FN. The final verification Task read only `api.json`; the criterion-local adjudicator refused to treat earlier write snapshots for `web.json` and `worker.json` as current verification.

## Remaining M12 chain

The final T6 command output is `Ran 2 tests ... OK`. For GC1, RWKV's reason says the successful tests confirm `safe_divide`, but its enum is `advances`, not `satisfies`. Full-history adjudication then states that the newest `math_utils.py` snapshot contains `return a * b`; the persisted source actually contains `return a / b`. This is a second semantic pass contradicting the first real observation, not missing data.

## Structural limit exposed by LH02

Every completed Task was compared against every criterion, and each request event saved a complete RunState snapshot. The single case issued 381 model requests and produced a 608 MB SQLite database. Efficiency was not a score gate, but this multiplication makes the structure fragile and cannot be uploaded as the final architecture even if correctness later improves.

## Next root cause

Round61/62 both show Tasks whose postcondition requires several reads/copies while the executor permits one action. A successful partial action followed by RWKV `decision=replan` is currently recorded as a failed Attempt and sent through failure analysis. The extra failure decision may repeat, replace, or abandon the action even though RWKV already stated the Task is simply incomplete. The next isolated change is a multi-action Task loop.
