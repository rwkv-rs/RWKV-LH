# Round46 Basic30 Causal Analysis

## Frozen metrics

| Metric | Round41 | Round46 | Change |
|---|---:|---:|---:|
| Strict E2E | 17 | 23 | +6 |
| External acceptance | 24 | 23 | -1 |
| Agent completed | 20 | 25 | +5 |
| False positive | 3 | 2 | -1 |
| False negative | 7 | 0 | -7 |
| Model requests | 467 | 517 | +50 |
| Tasks | 130 | 138 | +8 |
| Attempts | 134 | 144 | +10 |

Strict passes: `B01`, `B02`, `B03`, `B05`, `B06`, `B07`, `B08`, `B09`, `B11`, `B13`, `B14`, `B15`, `B16`, `B17`, `B18`, `B19`, `B20`, `B21`, `B24`, `B25`, `B26`, `B28`, `B30`.

Both agent and external failed: `B04`, `B10`, `B22`, `B23`, `B27`.

False positives: `B12`, `B29`. False negatives: none.

Round46 exceeds the preregistered FP maximum (`2 > 1`) and is not upload-eligible despite the Strict improvement.

## Confirmed architecture gain

The exact missing-schema normalization preserved RWKV's first correct `B27` Task decision. The raw two-field response said the complete file still contained `protocol=v1` and emitted `decision=replan`; the converter inserted only the fixed schema tag, made no second Task-commit request, and the run blocked. Raw/normalized payloads, distinct digests, the v4 transformation, and unchanged reason/decision are present in the trace.

The compact RWKV-owned verification contract also recovered `B21`, `B25`, and `B26` in both canary and Basic30. There are no false negatives in the full round. This confirms that a read/list result is sufficient evidence when RWKV directly judges it, without another verifier Task or Controller rule.

## Failure-by-failure first cause and amplification

### B04 — true failure, blocked

The producer wrote invented source content rather than copying the observed bytes. The incorrect artifact did not become a completed run. First cause remains action selection/value transfer; downstream blocking is correct.

### B10 — true failure, blocked

The coding workflow did not leave a test-passing implementation. The Task/recovery chain blocked rather than claiming success. This is a model coding/repair failure, not a format failure.

### B12 — false positive caused by stale parallel action commitment

The initial Task graph itself was poor: it created two independent ready Tasks, `read numbers.txt` and `read stats.json`, although `stats.json` did not yet exist. Both read actions were proposed from isolated parallel state. Their failures triggered independent action reselection, again in one ready frontier:

- T1 selected a correct `write_json(stats.json, {count:5,sum:25,min:-2,max:9})`.
- T2 selected a wrong `write_json(stats.json, {count:10,sum:55,min:1,max:10})`.

Harness side effects are executed serially, but both actions had already been committed against the same pre-write state. T1 wrote the correct file; on the next controller transition, the stale T2 action remained materialized and overwrote it. Task-local deterministic verification merely confirmed each model-selected value against itself. Later reads observed the last write, and Task/Goal decisions accepted it.

The first architectural defect is therefore optimistic-concurrency state staleness between parallel action proposal and serial side-effect execution. The semantic errors are then amplified by self-expected verification and Goal pass.

### B22 — true failure, blocked

The produced Markdown did not meet the exact unchecked-item format. The run blocked. The first cause remains producer formatting/action content.

### B23 — true failure, blocked

The fallback selection workflow did not produce the required selected JSON. The run blocked. The first cause remains action/dependency choice around unavailable/invalid primary input.

### B27 — true failure, correctly blocked after interface fix

Only one of the required replacements was made. The decision-last Task verifier detected the remaining occurrences. Exact schema-tag normalization preserved that `replan` instead of resampling it into `pass`. Recovery did not complete a producer correction, so the run blocked. This is the intended chain behavior.

### B29 — remaining semantic false positive

RWKV chose `write_file` and copied only `line two` instead of using `copy_file` or the full observed source. T2's Task decision claimed the partial output matched the original. T5 then selected the correct independent pair (`backup/source.txt` versus original `source.txt`) and again claimed equality despite different content and hashes. Goal adjudication repeated the false equality and completed the run.

This is not a missing-format case: all relevant semantic values were present and accepted. It remains a weak-model tool/value-transfer and comparison error. A Controller comparison rule would replace RWKV's decision and is not permitted.

## Next architecture step

Before addressing B29, fix the independent global scheduler defect exposed by B12. Parallel model proposals are valuable for large read-only code summarization, but a pending action selected from a frontier snapshot becomes stale when an earlier side effect changes the same target. The scheduler should use optimistic-concurrency invalidation:

1. retain parallel proposal for independent Tasks;
2. after executing a side effect, detect only later actions materialized from that same frontier whose declared path/destination overlaps the changed target;
3. do not execute the stale action; reset it to model selection and audit the invalidation;
4. let RWKV reselect against the new persisted state;
5. leave disjoint read-only parallel execution unchanged.

This is mechanical scheduling, not answer selection: it neither edits an action nor chooses a replacement. Round47 must preregister and test same-target write/write, write/read, disjoint side effects, disjoint parallel reads, failed/unknown effects, recovery, and checkpoint serialization.
