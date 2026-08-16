# Round61 fixed-15 manual backward causal analysis

## Frozen outcome

- Strict E2E: `1/15`
- External acceptance: `5/15`
- Agent completed: `4/15`
- FP: `3` (`M01`, `M06`, `M18`)
- FN: `4` (`B02`, `B10`, `M12`, `LH02`)

The preregistered canary gate failed (`Strict >=6`, `FN <=1`). Round61 must not run the full 90 or be uploaded.

## Per-case backward trace

| Case | Observable result | First incorrect link | Downstream amplification | Root class |
| --- | --- | --- | --- | --- |
| B01 | Exact file result and Agent completion both correct | None | Task-local relation and Goal evidence agree | Strict control |
| B02 | `report.json` is externally exact, Agent blocks | T1 says read/extract only advances GC1; T2 omits verification GC3. A valid first T2 relation also used `reasoning` and was discarded as a format error | Full-history/obligation fallback emits internal Task objects instead of the five-field batch and blocks | criterion-array omission + narrow format boundary + fallback protocol |
| B10 | `slug.py` and tests are externally correct, Agent blocks | Goal parser splits one tested implementation outcome into ten criteria; early Task relations copy nearly all IDs | Six criteria verify, four remain; obligation recovery blocks despite passing tests | criterion explosion + all-ID binding instability |
| M01 | Summary is correct, but service files lose unrelated settings | Initial plan observes only directory names, then preplans writes. Action selection guesses complete JSON without reading each source file | Final summary read is treated as proof that unrelated original settings were preserved; GC1/GC3 pass without a pre-mutation observation | speculative dependency chain + unsupported preservation proof |
| M03 | Migration never executes | T3 action response uses a common object form with extra `action/path/value` fields and the G1i boundary rejects it | Downstream verify Task remains unreachable | action wire-format failure |
| M06 | No selected assets are copied; only a guessed manifest exists | High-level “copy listed files” Task first reads selection, then writes a manifest instead of issuing the required copy actions. Task commit incorrectly equates manifest membership with copied files | Goal relation/adjudication treats an index as evidence that referenced files exist and that no others exist | one-action Task mismatch + index-as-object evidence error |
| LH02 | All 15 checkpoints and final config are externally correct, Agent blocks | Goal is split into 19 criteria. Sibling checkpoint Tasks all depend only on the initial read, so final Task's causal closure excludes the checkpoint siblings | GC19 adjudication sees the full original Goal through the GOAL source, expands “verify final config” back into the whole checkpoint set, and fallback source selection invents/omits refs | incomplete dependency ownership + criterion scope leakage |
| LH05 | Only listings/rules/shard01 are observed; no report is produced | Initial five Tasks stop at discovery; the next-frontier response uses noncanonical internal Task shapes | Obligation extension rejects both attempts and blocks | obligation wire-format failure after discovery |
| LH11 | No checkpoints/summary are produced | Planner creates multi-file Tasks, but one Harness action can read/list only one path. Several actions also target nonexistent range-like paths | Task commit correctly rejects partial reads; retries/recovery repeat or block and dependencies cascade | Task granularity versus one-action executor mismatch |
| B24 | Input is read, transform never executes | T2 action response mixes `read_file` with arguments from another read/evidence schema | G1i argument validation blocks the remaining chain | cross-tool argument format failure |
| M12 | Code and all tests are externally correct, Agent blocks | Final test Task relation claims GC1-GC5 but omits GC6 (“all tests pass”) despite its own successful test output | Full-history adjudication hallucinates the current median implementation as wrong and obligation output is noncanonical | criterion omission + same-path version rescan |
| M16 | All five selected inputs are observed, no `recovered.json` is created | Initial graph ends after reads; next-frontier generation does not produce an accepted canonical producer Task | Agent blocks before synthesis | obligation protocol after complete discovery |
| M18 | Digest map omits `inputs/b.json`, Agent nevertheless completes | Directory listing observes both files, but downstream reads only `a.txt` and preplanned producer writes a one-entry map | Task relations copy all five criteria; Goal adjudication ignores the listed-but-missing `b.json` contribution | speculative chain + partial-collection false proof |
| H12 | Only listing and one sample shard are read | One Task describes aggregating all 15 shards in memory, but its action response is a noncanonical `action/path/value` object | Producer and verify Tasks remain unreachable | multi-action Task mismatch + action format failure |
| H13 | Several first files are read, no phase outputs are produced | Each planned Task covers four documents while one action reads one document; one call also emits a nested G1i action object | Task commit rejects incomplete batches and the action/retry budget is consumed | Task granularity versus one-action executor mismatch |

## Cross-case causal chain

1. **Planning can describe more work than one action can establish.** The runtime nevertheless binds one Task to one action attempt. Grouped reads/copies/aggregation therefore start from a structurally impossible contract.
2. **Post-Task Goal-effect arrays are too wide for this model.** Responses frequently copy every displayed criterion ID, omit the exact final criterion, or switch semantic content on a format retry.
3. **Task-local closure is only as correct as planner dependencies.** Sibling producers needed by a collection/final criterion are absent when RWKV did not encode those edges.
4. **Fallback Goal evidence leaks the complete original request into each fixed criterion through the GOAL source.** The model expands a local criterion back into unrelated obligations and confuses scope.
5. **Evidence semantics remain too permissive.** A manifest, summary, test count, or one sample is repeatedly treated as proof of all referenced objects or the complete collection.
6. **Common format variance triggers semantic resampling.** `reasoning` versus `reason` and internal Task/G1i object shapes cause a good semantic first response to be discarded; the retry can be worse.

## Next architecture guidance

The immediate next experiment should isolate each immutable criterion in a separate post-Task RWKV request and ask for one enum relation (`unrelated`, `advances`, `satisfies`) instead of arrays of IDs. The fixed criterion ID comes from request scope; no Controller semantic choice is added. The Goal evidence view should expose only that criterion's immutable text for the GOAL source, not the complete original request. A transparent `reasoning` to `reason` key alias may be accepted with the value byte-for-byte preserved.

After that isolated ablation, the next independent architecture experiment should treat a Task as a multi-action loop: a successful action plus RWKV `replan` Task verdict means “Task still open; ask RWKV for another action with all prior Task observations,” not a failed action to repeat. This is necessary for grouped file reads/copies and should be evaluated separately so its effect is measurable.
