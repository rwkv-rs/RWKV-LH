# Round79: current model-input audit

Date: 2026-08-14

Status: complete input inventory for the registered 24-case sample. This is an
architecture baseline, not evidence that the redesign improves E2E results.

## 1. Question and answer

The question is: for every current model call in one task, what exact kind of
input does RWKV receive?

The answer is not one continuous task dialogue. RWKV currently receives a new,
independent completion prompt at every transition. The Controller reconstructs
selected Goal, Task, action history, evidence and tool definitions as text; the
deployed model API receives only `prompt`, sampling parameters, output limit and
stop suffixes. It receives no parent state, recurrent-state handle, event cursor,
fork identity or commit/rollback identity.

Across the registered sample, 24 E2E audit files contain 218 model calls and
755,361 prompt tokens. A case uses 9.1 calls on average and 3.6 distinct request
roles. The model therefore repeatedly infers which role it is in and reconstructs
the same trajectory from a lossy text projection.

## 2. Sources, versions and generation

Purpose: inventory the exact prompts that conditioned RWKV in the latest
Round77/Round78 causal comparison, not synthetic templates.

Source audit sets:

| Source | Cases | SHA-256 manifest digest |
|---|---:|---|
| `Round77_canary/cases/*/audit.json` | 7 | `ea896df48fc7f6ac164d1c21993a5f7238182cc70c7d5056b5093b0a25e5d219` |
| `Round78_architecture_fixes_canary_r2/cases/*/audit.json` | 7 | `1e283dcbc4110af42d281feed15ab6157825db89bd41ad4df89d5d7ab2fa1884` |
| `Round78_architecture_fixes_canary_r3/cases/*/audit.json` | 7 | `9ab026b26efe92a0190073eec46503e1ce8d8752df8b895efe2bfab57bc6f120` |
| `Round78_architecture_fixes_canary_r4_targeted/cases/*/audit.json` | 3 | `45b9b42e9af2cfffbd741c796c54cafeb7d4e7043b0754ece45cdbbb04d762ff` |
| Combined, path-sorted manifest | 24 | `d33c924ca970ddc9cd58a30c19a18bc27b40d61d78c0dc7097fbd941b9f34b22` |

Each manifest digest is the SHA-256 of the path-sorted `sha256sum` records for
the matching audit files. Analysis script:
`temp/analyze_round79_current_model_inputs.py`, SHA-256
`a67fe85d41313f5e09b6f613c1f096c7da19e0d2551a44a6d0be1590be7f93a5`.

Generation command:

```text
uv run python /home/chase/GitHub/RWKV-LH/temp/analyze_round79_current_model_inputs.py
```

Relevant source snapshot:

| File | SHA-256 |
|---|---|
| `rwkv_lh/model.py` | `a34004dd14d63b45858f870d728337f309e416999b8c72004f7f913d96e13dcf` |
| `rwkv_lh/memory.py` | `770e59c7746d9b039b9c831eae9323892930acdb8a8d33faa3cd5df6c2891d5c` |
| `rwkv_lh/controller.py` | `f8c2eab64e591889653d1f19bb4d6b90c414fdaba0586281a8a92734aca1da89` |
| `rwkv_lh/harness.py` | `3c37abcd5f6e1fb5f28e13fbe8c1199ca559fb53f29ad332ec7b6ca21e574893` |
| `rwkv_lh/runtime/openai_compat.py` | `fc3d7d6d9aad46c4da18a941826e07ae815ebc98f3e93de3d1fe9189924ab5ac` |
| `rwkv_lh/runtime/protocol.py` | `ab0cf60f92b9a23781ff7510749a33b8e0a9617a7d593b7752753b00c6534cd7` |
| `rwkv_lh/runtime/settings.py` | `891f86ebb443d91d25d8cc7b2722ec0fec2cf3fa2daf945e2a44af832f844b55` |
| `rwkv_lh/schema.py` | `f6ea691fe5bee821df9e3c492e321fa8d0a6ceb6458ac602f574936ec1b411f9` |
| `rwkv_lh/tool_protocol.py` | `1a1aa6f9ff11d2ab33e316f806d8e9b5da60e5b06ad2c70a02ebe9491afa885c` |
| `rwkv_lh/prompting.py` | `561f385eeba612d539f41c4a71ccacfa3b5996774624d62a35885606c9fa0edf` |
| `rwkv_lh/token_budget.py` | `5479983bcf79b3df007668c16a28a76bf865d08474f5b6178eada476b6694260` |
| `rwkv_lh/tokenizer.py` | `67b83e2ec297f02e80e041b719ecf64595a37920ce95b6650546b612b351fe06` |
| `rwkv_lh/temp_policy.py` | `a4e145913821d3a25ad59915551ddccf5af17cae882db54d3d0c2f61fb6554b9` |

## 3. Wire distribution actually seen by the model

The 218 calls use three incompatible continuation prefixes:

| Dialect | Calls | Prefix |
|---|---:|---|
| Hash-role JSON | 207 | `### User ... ### Assistant\n```json\n{` |
| G1i tool dialogue | 2 | `System: Tools: ... User: ... Assistant: ```json\n` |
| Hash-role free text | 9 | `### User ... ### Assistant\n` |

The two G1i calls occur only during recovery-gap selection. The final answer
switches to free text. All other semantic transitions use the hash-role JSON
prefill. This means one run can change conditioning distribution twice without
changing model weights or the user task.

All semantic loops currently have `SEMANTIC_ATTEMPTS_PER_TRANSITION = 1`, which
correctly prevents a second model sample inside those loops. However, the next
request role still reconstructs and samples the semantics again from a new
prompt. “One sample per function” is therefore weaker than “one continuous
semantic transition with committed model state.”

## 4. Complete request inventory

| Request | Trigger and dynamic input | Static/repeated input | Calls; input tokens mean / median / max | Output and sampling | Primary defect |
|---|---|---|---:|---|---|
| `task_decomposition` | Initial Goal and workspace manifest | Long planning rules and 1,417-token mean action-effect catalog | 24; 2,306.9 / 2,304.5 / 2,485 | max 5,000; temperature 0.18, or 0.25 for complex Goal | The first continuation is already dominated by the action catalog; the model authors a six-field Task batch rather than only the causal frontier. |
| `task_step` | Attempt ID, allowed decisions, check summaries, evidence index and projected Task state | Full action schemas in every call, mean 2,516.7 tokens | 131; 4,117.1 / 3,753 / 10,310 | mean 518.5 output chars; max 850; temperature 0.05 | The median authoritative state is 660 tokens while the schema is 2,542. Prompt/capsule ratio is 6.2 median and 15.5 max. This is the main repeated load. |
| `task_member_declaration` | Active Task, existing members, grounded paths and observations | 299-token instruction prefix | 6; 1,624 / 1,412 / 2,269 | max 1,800; temperature 0.05 | A fresh role is created to restate identities that should be a Task-lane workset delta. |
| `collection_member_action` | Task summary, pending members and observations | Full action schemas, exactly 2,550 tokens in all 10 calls | 10; 4,043.6 / 4,053 / 5,023 | mean 386.6 output chars; max 900; temperature 0.05 | A one-member action is selected under a prompt 4.3 times the source capsule on average. |
| `failure_analysis` | Feasible decisions, recovery capsule and latest attempt | 234-token diagnosis role | 9; 2,621 / 2,149 / 6,678 | max 1,000; temperature 0.10 | Failure semantics are sampled in a separate state and then sampled again during the following Task step or replan. |
| `failure_recovery_gap_selection` | Failed Task view, reconstructed Goal/observations and Task IDs | G1i `select_recovery_gap` definition | 2; 3,196.5 / 3,196.5 / 4,593 | max 1,000; temperature 0.10 | This is the only mid-run switch to the model's G1i tool-dialogue form, then the result is reserialized into another dialect. |
| `replan` | Failure view, selected gap, reconstructed Goal/observations, manifest and Task IDs | Long replacement-DAG rules | 2; 3,624.5 / 3,624.5 / 4,872 | max 4,200; base temperature 0.28, escalating to 0.55 | A gap selected in one independent model state is consumed by a second independent state; higher temperature makes structural output less stable. |
| `goal_frontier_step` | One serialized state capsule | Goal-review instructions and six-field output contract | 25; 2,667 / 1,737 / 7,449 | mean 1,800.6 output chars, max 23,609; max 4,200; temperature 0.10 | Goal decisions reconstruct Task evidence after Task-state loss. Long repetition occurred, and only 10 calls visibly included the evidence registry. |
| `final_answer` | Original request and Controller-built “verified state” text | Free-text answer instruction | 9; 730.3 / 678 / 1,150 | mean 2,677.7 output chars, max 9,451; max 2,400; temperature 0.05 | The final call forks into a third dialect and has no recurrent continuity with the model decision that finished the Goal. |

Totals: 207 hash-role JSON calls, 2 G1i calls, 9 free-text calls; 141
calls repeat the complete action schemas; 26 include a workspace manifest; 10
include a visible evidence registry; total model output is 183,197 characters.

The most common transition is `task_step -> task_step` (97), followed by
`task_decomposition -> task_step` (22), `task_step -> goal_frontier_step` (16),
and `task_step -> failure_analysis` (9). Every arrow is currently a stateless
prompt boundary.

## 5. What one `task_step` actually contains

A typical Task decision is conditioned on five layers:

1. a 252–372-token instruction prefix describing decisions, member behavior,
   evidence rules and negative cases;
2. attempt, allowed-decision and deterministic-check summaries;
3. an evidence-ref index whose payloads are supposed to occur in the state;
4. a `ContextBundle` reconstructed by `WorkingMemoryBuilder`;
5. every registered action schema, even when only one or two actions are
   causally relevant.

The `ContextBundle` is not an actual chronological dialogue. It is rendered as
Goal, active Task, compressed causal state, dependency outputs, selected memory,
latest failure and an optional action contract. Therefore the model must infer
the chronology and distinguish current from historical fields from prose and
nested JSON rather than from an append-only event boundary.

## 6. Selection, loss and duplication before the model call

Current memory budgets are: total 13,600; Goal 1,200; Task 1,600; causal state
2,200; dependencies 3,000; evidence 5,000; failure 1,200; action contract 1,600
tokens.

If a request does not fit, `ContextBundle.projected()` removes data in this
order:

1. evidence entries from the end;
2. dependency outputs from the end;
3. the entire action contract;
4. the failure record;
5. only then fail if immutable Goal plus active Task still do not fit.

Within `_pack_entries`, a first oversized item may be truncated, while later
oversized items are skipped. Selected and excluded memory IDs are auditable,
but an exact observation can still be absent from the model-visible input. This
explains how the durable run can retain a true fact while a later Goal prompt
cannot use it.

At the same time, other data are duplicated: Task metadata appears in both
instructions and capsule, evidence is represented by both an index and payload,
and static action definitions are repeated in 141 prompts. The current behavior
therefore loses high-value dynamic facts while retaining low-value static text.

## 7. The real 16k and chunk boundary

The runtime checks every final prompt with the local RWKV tokenizer against
`max_model_len - BOS - max_output - safety`. That preflight is sound. The
problem occurs earlier:

- `read_file` and `read_json` expose character cursors with at most 16,000
  characters per result;
- `read_files` can expose 16,000 characters per file and 48,000 total;
- source slicing is therefore character-based while model capacity is
  token-based;
- oversized observations then enter the memory selector, which may truncate or
  omit them;
- there is no durable chunk range, coverage ledger, child model lane or reduce
  tree.

The current Controller intentionally serializes all model requests. It can run
only a known read-only Harness prefix concurrently. Therefore “chunk plus
multi-concurrency” currently parallelizes some I/O, but not independent model
analysis lanes, and it does not preserve exact coverage into Task completion.

## 8. Causal conclusions

The latest evidence supports five global conclusions:

1. **Input discontinuity is primary.** RWKV is used as independent JSON
   completion calls, not as a recurrent task trajectory.
2. **Static contract load is excessive.** The most frequent call often spends
   more tokens on all tool schemas than on the complete active state.
3. **Role fragmentation resamples interpretation.** Planning, member selection,
   failure, repair, Goal completion and answer generation do not share one
   committed cognitive state.
4. **External memory is necessary but its projection is unsafe.** Exact facts
   belong in a journal, yet they must enter the model as explicit typed events
   or token-bounded chunk results rather than optional narrative memory.
5. **Deterministic defects remain deterministic defects.** Schema/executor
   mismatch, parser history scan, range coverage and action validation must be
   fixed in runtime code; they cannot be attributed to model capability.

The target is consequently not a single giant prompt and not removal of
external state. It is one normal continuation grammar per isolated RWKV lane,
small model-authored commands, exact runtime-owned facts, and explicit chunk
results for every parallel branch.
