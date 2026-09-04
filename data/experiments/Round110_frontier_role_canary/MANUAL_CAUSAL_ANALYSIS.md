# Round110 manual causal analysis

## Fixed result

- Agent/External/Strict: fail/fail/fail; no false completion.
- 50 requests, 10 Tasks, 27 Attempts, 0 applied repairs.
- All ten Tasks carried raw RWKV `frontier_role=prerequisite`.
- Final was non-empty raw RWKV output.

## Call and workspace chain

1. RWKV correctly marked the initial discovery/preparation frontier as prerequisite.
2. T1 listed the workspace and read `migration_rules.md`, including both exact special
   migrations.
3. In T2, RWKV read service01 through service08, then wrote upgraded service01 through
   service06 and reread service01. The writes and every value came directly from RWKV.
4. General v3 fields were correct for service01/02/04/05/06. Service03 received general
   fields but RWKV preserved its old `database` object instead of applying the visible
   required `storage {dsn, pool_size}` migration.
5. RWKV committed T2 early. T3 and T4 read already-touched services and completed. T5 read
   service04 through service08 and then looped back over earlier services without producing
   more writes.
6. Goal recovery proposed batches duplicating active Tasks; they were rejected by the
   registered graph-delta constraint. The run blocked rather than resetting the graph.
7. External state was materially closer to correct but still failed service03 special
   migration, all service07/08 changes, migration report, and verifier.

## Conclusion

The frontier-role gate fixed Round109's false positive and did not prevent real RWKV
mutations. Remaining wrong values and early Task completion are model decisions. The
controller must not patch service03 or synthesize the missing files. Broader regression is
needed to measure whether the extra role field reduces FP without harming simple-task
Strict accuracy.
