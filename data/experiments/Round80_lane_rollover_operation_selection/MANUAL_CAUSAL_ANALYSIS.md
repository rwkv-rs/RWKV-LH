# Round80 manual causal analysis

## Outcome first

The three requested stages are implemented and measured, but the model/system does **not** meet real-use acceptance.

| Layer | Frozen result | Interpretation |
| --- | ---: | --- |
| Rollover structure | 38/38 valid across 30 real E2E cases | General 16k continuation path works without semantic summarization |
| Context-limit regression | 0/90 cases | Round79's hard prompt-limit termination was removed in this run |
| Independent G1i wire | 90/90 | Current single wire format is stable in the isolated selector probe |
| Independent exact operation | 47/90 (52.22%) | Model cannot yet reliably distinguish the 20 operations |
| Repeat exact agreement | 27/30 (90%) | Output is often repeatable, including repeatably wrong decisions |
| Full90 Strict | 0/90 | Overall architecture/model is not accepted |
| Full90 External | 10/90 | Some workspaces become correct despite incomplete Agent state |
| Full90 Agent | 1/90 | Fail-closed behavior dominates; one false completion remains |
| Full90 FP/FN | 1 / 10 | Completion precision improved relative to Round77, recall collapsed |

## Rollover evidence

`FULL90_CAUSAL_SUMMARY.json` revalidated every record from the final serialized audit rather than trusting runtime log messages:

- 30 case ids and 38 rollover records;
- 652 archived event ids and 402 retained event ids;
- every retained/archived pair is disjoint, source-ordered, and exactly covers its source checkpoint events;
- every source checkpoint remains present and matches its recorded digest/token count;
- every compact checkpoint points to the source as parent and matches its output digest/token count;
- every output event list is `retained events + lane_rollover event`;
- every manifest digest and runtime projection digest recomputes exactly;
- every rollover has semantic request count 0;
- maximum source checkpoint was 16,260 tokens; maximum compact output was 8,686 tokens (mandatory current facts may exceed the 8,192 target but remained below the relevant request input limit);
- invariant failures: 0; context-limit failures: 0.

The real forced probe additionally archives 7 events while preserving all checkpoint bytes and successfully obtains a real `read_file` selection and binding after rollover.

## Operation-selection evidence

The isolated input was only 385–457 tokens, so failures cannot be attributed to 16k pressure. It always produced one strict `lh_select_operation` call and never emitted an unknown enum value in this dataset, but it collapsed several distinctions:

- `patch_json` → `read_json` or `write_json`;
- `remove_line` → `read_file`;
- `check_command` → `read_file` or `read_json`;
- `lh_workset`, `lh_task_done`, `lh_reopen_task` → `write_file`;
- `lh_replace_task` → `write_json`;
- collection `copy_file` → `write_file`;
- some `lh_chunk_map` → `read_file` or `lh_workset`.

This is not random formatting noise. Wire-valid was 100%, mean repeat similarity was 0.978829, repeat near-stable was 93.33%, and many wrong choices repeated three times. The remaining bottleneck is operation semantics/input discrimination for this base continuation model.

## Full90 causal boundary

Final r2 metrics are Strict 0/90, External 10/90, Agent completed 1/90, FP 1, FN 10. Statuses are 86 blocked, 3 interrupted, and 1 completed. Rejected candidate classes were:

- wrong top-level wire keys: 33;
- selector bypass inside accumulated Task dialogue: 26;
- invalid JSON: 7;
- other protocol/schema errors: 9.

This reconciles the independent probe with E2E: a clean one-step selector prompt has stable wire shape, while longer causal lanes can still cause the continuation model to repeat the prior direct operation instead of the newly visible selector. Rollover prevents unbounded length but does not itself teach phase discrimination.

The ten External-only cases are `B01`, `B03`, `B07`, `M05`, `H04`, `B13`, `B15`, `B18`, `B26`, and `M20`. The only Agent-completed case is `B09`, whose external verifier failed, so it is the remaining false positive.

## Newly exposed interface and storage issues

The first full90 run stopped after 89 audits because the benchmark-local `mock_api` extension still supplied string argument descriptions to the stricter unified `ActionDefinition`. Catalog validation alone did not instantiate this combination. The fixture now uses explicit JSON Schema and `E2E-LH09` completes normally in both a targeted run and final full90 r2.

The same run quantified quadratic snapshot duplication: 19.96 GB before completion. Transparent compressed JSON plus gzip initial-snapshot/delta timelines reduced the complete r2 to 0.94 GB (4.71%) while preserving 90 SQLite user-version-2 databases, 8,194 compressed checkpoint rows, 1,573 compressed event rows, and all decoded exports.

## What is solved and what is not

Solved in Round80:

- general pre-generation rollover for all lane kinds;
- explicit archive/retention relation and no silent evidence/event loss;
- operation binding preserved across rollover;
- real tokenizer limit enforcement with zero semantic compaction calls;
- independent, fixed operation-selection measurement;
- `mock_api` registry/schema interface mismatch;
- practical persistence size of full checkpoint history.

Not solved:

- exact operation selection is below the frozen 90% threshold;
- selector-phase adherence degrades in accumulated E2E transcripts;
- full90 completion/repair recall is too low;
- M06 remains failed;
- Round46 remains the formal accepted baseline; Round80 cannot replace it.

The next change must therefore target the base model's phase/operation discrimination using the independent dataset and the actual Task transcript distribution. It must not weaken strict parsing, auto-correct the selected operation in runtime, add a reviewer role, or tune against short7.
