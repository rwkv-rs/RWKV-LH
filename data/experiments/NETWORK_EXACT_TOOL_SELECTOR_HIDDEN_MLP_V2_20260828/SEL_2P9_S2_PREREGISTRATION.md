# NET-SEL-2P9-S2 residual state-tuning preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Numbering and parent

- `NET-SEL-2P9-S0`: zero-state 2.9B + Hidden/MLP baseline (`run_r1`), rejected.
- `NET-SEL-2P9-S1`: broad 7,500-row head corpus plus 6,000-step state
  (`run_s1`), rejected by the frozen external gate.
- `NET-SEL-2P9-S2`: this residual experiment.
- `NET-EXE-13P3-N0`: current stable 13.3B executor profile
  `executor-stage8-r3-step1700`; it is not modified by S2.
- `NET-EXE-13P3-N1`: separately gated future network-executor state tuning.

S2 starts from the 2.9B zero state.  It does not continue the rejected S1
state.  Selector and Executor learned profiles and dynamic recurrent lanes are
stored independently and communicate only through committed structured events.

## Observed residual

The rejected S1 head scored 47/120 on the complete frozen ECRA route set:

| category | exact |
|---|---:|
| local-only | 12/30 |
| public-web | 22/25 |
| deterministic | 11/15 |
| structured connector | 1/20 |
| mixed local-first | 1/20 |
| privacy local-first | 0/10 |

Local network false-positive rate is 5/30.  Connector errors are 13 `web_search`,
5 `replace_text`, and 1 `check_command`.  Therefore this is not a missing
retrieval-provider defect and not a connector-only corpus problem.  The data
must jointly calibrate connector, ordinary web, local/deterministic retention,
mixed local-first, privacy local-first, and stopping.

## Frozen dataset

Version: `rwkv-lh.network-selector.residual-s2.v1`.

Training rows: exactly 2,000.

- 1,400 failure-grounded semantic rows from the already validated Stage3
  natural-route/stop train split:
  - stable selector/completion replay 500;
  - natural connector 400;
  - ordinary web 100;
  - mixed local-first 200;
  - privacy local-first 200.
- 600 class-retention rows: exactly 24 per each of the 25 v2 tool labels,
  selected in source order from the frozen v2.4 train split.

Development rows: 276 (the 176 Stage3 residual dev rows plus 4 per label from
the v2.4 dev split).  Synthetic retention test: 250 (10 per label from the
v2.4 test split).  Semantic families and source splits cannot cross.

The natural residual rows are projected into the v2 Selector contract using
only immutable request, stage objective, stage role, compact operation names
and success/failure counters.  No schema, tool-result body, Executor output,
reasoning, ECRA instruction, ECRA entity, URL, or reference answer is included.

The dedicated natural-connector residual cluster is 400/2,000.  Stable replay
and class retention add 74 connector labels, so the exact label balance is
474 connector to 1,526 non-connector (about 1:3.22), stricter than the
historical minimum 1:2 hard-negative balance.  Dataset acceptance
requires exact duplicates 0, train/dev family overlap 0, all labels present in
all splits, and maximum UTF-8 byte 5-gram cosine against the frozen ECRA120
instructions below 0.75.

## State training

- base: `rwkv7-g1i-2.9b-20260805-ctx16384`, zero initial state;
- GPU0, `--peft state --op fla`, BF16, micro-batch 1, DeepSpeed stage 1,
  gradient checkpointing, BOS 0, `target_suffix` loss;
- 2,000 steps, one epoch, shuffle, seed 831;
- context 1,280; tokenizer preflight must prove every target suffix is intact;
- LR `2e-5 -> 4e-6` cosine, warmup 40;
- checkpoints every 500 steps; only final step 2,000 is selected unless it is
  non-finite or incomplete.

Checkpoint orientation is `[head,value,key] -> [head,value,key]` identity.
Training and vLLM tensors, SHA-256, shape, dtype, finiteness and nonzero values
must be validated before feature extraction.

## Hidden/MLP ablation

Extract batch-1 last and real-token mean features for the same frozen dataset
under both zero state and S2 state.  RWKV text generation and sampling counts
must remain zero.  Train the same 256-hidden MLP with the same seed and fixed
hyperparameters for each state.  Preserve raw 25 logits and use raw argmax
only.

The state-effect audit also replays the selected S2 head on zero-state features;
S2 is not credited when predictions/features are indistinguishable from zero.

## Frozen acceptance gates

Internal retention test:

- accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- `web_search`, `connector_lookup`, calculator/date/time recall >= 0.85;
- local/search/web/connector boundary accuracy >= 0.85.

ECRA120 first-tool gates:

- local-only >= 24/30;
- public web >= 23/25;
- deterministic >= 14/15;
- connector >= 12/20;
- mixed local-first >= 10/20;
- privacy local-first >= 8/10;
- local-only network false-positive rate = 0;
- required-online false-negative rate <= 0.10;
- web/connector macro-F1 >= 0.70.

State causality gate: compared with the same S2 head on zero-state features,
the tuned profile must change at least 3 ECRA120 predictions, yield at least 3
net exact rescues, and regress at most 1 case.  If the zero-state head passes
but S2 has no causal benefit, the learned state is rejected rather than being
kept only to satisfy an architectural preference.

No gate may be changed after a run.  Passing network scores cannot compensate
for regression in local, deterministic, mixed, privacy, completion, identity,
state isolation, or the full local test suite.
