# Round80 implementation log

## Frozen inputs

- Protocol was written before implementation/model requests: `PROTOCOL.md`.
- Independent dataset: `rwkv-lh.operation-selection-dataset.v1`, 30 cases, SHA-256 `74760bd370f4ae0f35703820ea350da58788a5857a165c2cc5f99be5e59ebf13`.
- The dataset covers all 15 public local `ActionDefinition` actions and 5 Task controls and contains no short7/Round77 case text.
- Sampling, three repeats, concurrency, strict parser, byte 5-gram similarity, thresholds, and full90 gates were not changed after the first model request.

## Runtime implementation

1. `long-horizon.run.v13` adds immutable `ModelRolloverRecord` objects to `RunState`.
2. `ModelSession.rollover` creates a same-lane committed checkpoint whose parent is the exact source checkpoint and performs zero model calls.
3. `LongHorizonModel` preflights every generation, applies one definition scope for the expected function, builds a lane-specific runtime projection, retains mandatory/latest full events, and archives the remaining exact ids/digests.
4. Task projection includes member set status/counts, active/pending member page, exact member manifest digest, current evidence/output refs, and recent attempt summaries. Goal projection includes the immutable Goal, task status/frontier, task manifest, and Goal evidence refs.
5. Rollover failure is closed: if the minimal deterministic projection is over the request limit, generation is never called.
6. Chunk children still fork the declared common parent. A child may roll over independently after the fork; only the explicit child command is merged.
7. Large SQLite state/event JSON is transparently stored as `zlib-json-v1`; decoding accepts both compressed and prior plain JSON storage rows. E2E state timelines are gzip initial-snapshot-plus-delta artifacts.
8. The E2E `mock_api` extension was changed from obsolete string descriptions to the same explicit JSON Schema required by `ActionDefinition`. A dedicated test prevents this interface combination from escaping again.

## Verification chronology

- Dataset validate-only: valid 30/30, registry coverage 20/20.
- Unit suite after final code: 77 passed.
- Unified control suite after final code: 40 passed.
- E2E catalog validate-only: 90/90 valid.
- Real forced rollover probe run2: 16,228 source tokens > 16,151 input limit; output 8,049 tokens; 10 retained + 7 archived events; source checkpoints retained; state round-trip true; real model emitted and bound `read_file`.
- Independent real selection run: 90/90 HTTP and strict G1i valid, 0 bypass, 0 unknown, repeat exact agreement 27/30, near-stable 84/90; exact expected operation only 47/90.
- First full90 attempt retained 89 audits, then exposed obsolete `mock_api` schema construction. It is retained as negative evidence and is not reported as a completed full90.
- Final full90 r2: 90 audits, no runner crash. Thirty cases triggered 38 rollovers. All rollover partitions, source/output checkpoint lineage, manifest/projection digests, event visibility and zero-semantic-call invariants passed. No context-limit error occurred.
- Snapshot/timeline storage: incomplete r1 `19,964,672,062` bytes; complete r2 `940,411,787` bytes, ratio 0.047104.

## Commands

All commands ran inside WSL from `/home/chase/GitHub/RWKV-LH` with the project `.venv` Python. Exact full90 and runtime environment are also stored in each run's `RUN_PROTOCOL.json` and `source_tree_manifest.json`.

```text
.venv/bin/python -m pytest -q -s
.venv/bin/python scripts/run_lh_control_benchmark.py --output data/experiments/Round80_lane_rollover_operation_selection/control_regression_r2.json
.venv/bin/python scripts/run_rwkv_e2e_benchmark.py --suite all --validate-only
.venv/bin/python scripts/run_operation_selection_benchmark.py --dataset /home/chase/GitHub/RWKV-LH/data/datasets/rwkv_lh_operation_selection_v1/cases.json --output /home/chase/GitHub/RWKV-LH/data/experiments/Round80_lane_rollover_operation_selection/operation_selection_baseline_run1.json
.venv/bin/python scripts/run_rwkv_e2e_benchmark.py --suite all --max-transitions 200 --concurrency 8 --output /home/chase/GitHub/RWKV-LH/data/experiments/Round80_full90_r2
```
