# Round80 preregistered protocol: lane rollover and operation selection

Status: frozen before implementation and before any Round80 model request.

## Scope

Round80 closes three stages:

1. define one general rollover/compaction contract for Goal, Task, chunk, reduce, and final lanes;
2. implement that contract without a summarizer role or any extra semantic request;
3. measure Task operation selection on an independent fixed dataset and run related regressions.

This round does not change the single G1i wire format, does not add a model role, does not retry a malformed semantic candidate, and does not execute benchmark-selected operations.

## Rollover v1 contract

Protocol id: `rwkv-lh.lane-rollover.v1`.

- Trigger: immediately before generation when the committed input checkpoint token count is greater than `max_prompt_tokens(max_output_tokens)` computed by the real project tokenizer and runtime settings.
- Semantic request count: exactly zero. Compaction is a deterministic runtime projection; RWKV never writes or approves the projection.
- Archive: the source checkpoint remains immutable in `RunState.model_states`. Its id, SHA-256 transcript digest, token count, model, and transport are the exact archive reference.
- Lineage: the compact checkpoint keeps the same lane id/kind and names the source checkpoint as `parent_checkpoint_id`.
- Manifest: one durable rollover record contains the exact source event ids, retained event ids, archived event ids, lane decision ids, content refs, source/output checkpoint metadata, projection digest, and token limits. Retained and archived event ids must form an exact disjoint partition of source event ids.
- Visible input: one canonical `lane_rollover` event contains archive and manifest refs/digests, the continuation constraint, a deterministic current runtime projection, and as many newest full events as fit.
- Target: after minimal projection succeeds, retain newest full events while the compact checkpoint remains at or below `min(input_limit, floor(max_model_len / 2))`. Mandatory continuation facts remain even when no historical full event fits.
- Evidence: active Goal evidence refs, current Task output/evidence refs, member progress, and checkpoint/content manifest digests are runtime-derived. Historical bytes remain reachable through the exact checkpoint archive and are never overwritten.
- Overflow: if the minimal deterministic projection itself exceeds the request input limit, fail with `InputBudgetError`; no silent truncation and no semantic resampling are allowed.
- Repeated rollover: the new rollover event points to the previous archive/manifest, so archive lineage is transitive without replaying every old byte.
- Concurrency: chunk children may independently roll over after forking; only explicit commands are merged, never child state or transcript.

## Required rollover checks

- `ModelSession.rollover` lineage, token count, event ids, audit event, export/import.
- Automatic pre-generation rollover for an oversized Task selection checkpoint.
- Exact source-event partition and old checkpoint retention after state serialization round-trip.
- Preservation of operation binding when rollover occurs between selection and parameter binding.
- Task member counts plus pending/active member projection.
- Goal, Task, chunk, reduce, and final definition scoping after rollover.
- Minimal-projection overflow fails closed without calling the completion client.
- Parallel chunk candidates still share only their declared parent and merge commands only.

## Independent dataset

- Dataset: `data/datasets/rwkv_lh_operation_selection_v1/cases.json`.
- Dataset SHA-256: `74760bd370f4ae0f35703820ea350da58788a5857a165c2cc5f99be5e59ebf13`.
- Version: `rwkv-lh.operation-selection-dataset.v1`.
- Cases: 30; every one of the 15 public `ActionDefinition` operations and 5 Task controls occurs at least once.
- Independence: no short7 prompt, Round77 case id, benchmark fixture path, expected parameter object, or action execution is present.

## Fixed model run

- Prompt: current production `render_bootstrap` with only the registry-derived compact `lh_select_operation` definition and one canonical `task_activated` fixture event.
- Sampling: temperature `0.05`, top_p `1.0`, top_k `0`, presence penalty `0`, frequency penalty `0`, penalty decay `0.996`.
- Output limit: 96 tokens.
- Repeats: 3 per case.
- Concurrency: at most 8.
- Retry/resample: none at benchmark semantic level. Runtime HTTP transport behavior is recorded separately.
- Parser: production `parse_model_command`; no JSON extraction, repair, normalization, or historical scan.

## Frozen metrics and thresholds

Metric id: `rwkv-lh.operation-selection-metrics.v1`.

- dataset/schema/registry coverage: exactly 100%; otherwise the run is invalid;
- HTTP success rate: 100%; otherwise report infrastructure failure separately;
- strict G1i protocol-valid rate: at least 0.95;
- exact expected-operation rate over all requests: at least 0.90;
- direct-operation selector-bypass rate: at most 0.02;
- unknown-operation rate: at most 0.02;
- per-case three-repeat exact agreement rate: at least 0.90;
- repeat near-stable comparison rate: at least 0.90.

Raw-output repeat similarity uses `utf8-byte-5gram-cosine.v1`: encode UTF-8 bytes, count contiguous byte 5-grams, and compute cosine similarity over count vectors. A comparison is near-stable at similarity `>= 0.95`. Empty/empty is 1.0 and one-empty is 0.0. Evaluation code and thresholds are not changed after the first model request.

## Regression gates

- all project unit tests related to the unified controller, ModelSession, chunks, schema/store, harness registry, and web serialization;
- fixed `lh_control_30` benchmark validation/execution;
- E2E catalog validation for all 90 cases;
- targeted real E2E cases that previously reached the 16k failure (`B02`, `M03`) after the generic implementation, without case-specific branches;
- causal report records every failure and separates architecture correctness from base-model stability.

Round80 is complete only when artifacts, commands, environment, hashes, raw model outputs, aggregate metrics, test logs, and unresolved failures are recorded under this experiment directory. Passing thresholds is not assumed; a failed frozen threshold is a measured remaining limitation, not permission to change the metric.
