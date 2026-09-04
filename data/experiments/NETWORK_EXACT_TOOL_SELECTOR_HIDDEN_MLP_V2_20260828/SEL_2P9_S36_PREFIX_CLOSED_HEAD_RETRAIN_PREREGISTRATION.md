# SEL-2P9-S36 prefix-closed Head retrain preregistration

## Root cause carried from S35

S35 used the unmodified product client and service for every position in all
500 S30 test trajectories.  The locked S34 Head retained 493/500 current-row
decisions (98.6%) but only 319/495 earlier prefix decisions (64.44%).  Total
deployment accuracy was 812/995 (81.61%), so product activation remains locked.

The frozen S30 generator proves that each `expected_history_labels` item is the
real tool target at that earlier Harness position.  S30 training exposed only
one labeled current position per trajectory; it advanced through the earlier
positions only to construct state.  S36 fixes that dataset-coverage defect.  It
does not change the RWKV model, V3 input, zero state, feature extractor, tool
set, output, or product state semantics.

## Frozen source identities

- S30 trajectories:
  `data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1/cases.jsonl`
- S30 SHA-256:
  `5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305`
- S28 retention dataset:
  `data/datasets/rwkv_lh_network_selector_compact_current_harness_s28_v1/cases.jsonl`
- S28 SHA-256:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`
- S28 frozen dual-view feature manifest SHA-256:
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`
- Model: `rwkv7-g1i-2.9b-vllm-v1`
- Model SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- Engine revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`
- Input protocol: `rwkv-lh.exact-tool-selector-input.v3`.
- Feature protocol:
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1` with exact order
  `[mean, last]`, dimension 5120, both views from one current forward.
- State profile: explicit `zero`, SHA-256 equal to 64 zero characters.
- Physical training/extraction device: only GPU0.
- Canonical output classes: the existing ordered 25 labels; no class may be
  removed, merged, renamed, or delegated to the Executor.

## Prefix-closed derived dataset

Generate one derived row for every callable prefix of every S30 trajectory:

- ordered inputs are `history_selector_inputs + [selector_input]`;
- ordered labels are `expected_history_labels + [label]`;
- ordered rendered steps are `history_steps + [step]`;
- a derived row at position `p` contains the unchanged S30 bootstrap, steps
  strictly before `p`, the unchanged step at `p`, and the corresponding input;
- preserve the source split and language;
- use opaque hash-derived prefix and trajectory IDs which contain no label,
  language, split, or tool name;
- record source row digests for traceability but do not copy label-bearing S30
  sample IDs into feature shards;
- require exact render equality and no parameter schemas, full tool results,
  Executor text, generation, or sampling.

Frozen counts are:

- train: 2,000 trajectories, 3,336 prefix decisions;
- dev: 500 trajectories, 765 prefix decisions;
- test: 500 trajectories, 995 prefix decisions;
- total: 3,000 trajectories, 5,096 prefix decisions.

The derived dataset and its manifest must live under
`data/datasets/rwkv_lh_network_selector_prefix_closed_s36_v1/` and record the
source, version, purpose, generator hash, file hash, counts, and generation
method.

## Feature extraction

For each source trajectory, advance the bootstrap once from native zero state,
then advance its ordered steps once each on the same persistent state.  At
every step, retain mean and last final-hidden features from that same forward.
Store float32 features, opaque prefix IDs, split, language, position, and kind;
do not store labels or label-bearing IDs in feature shards.  Generation and
sampling counts must remain zero.  Shards are resumable only after complete
identity and content validation.

## Training isolation and fixed optimization

- Parse labels only for S28/S36 train and dev rows.  Skip every raw line marked
  `"split":"test"` before JSON label parsing.
- Load test features only during the separately locked regression, never in
  normalization, training, early stopping, candidate selection, or temperature
  selection.
- Training inputs are S28 train (6,000 current-Harness rows) plus S36 train
  (3,336 deployment-prefix rows).
- Compute feature mean and standard deviation unweighted over those train rows.
- Loss gives equal total mass to every `(dataset source, canonical class)` pair:
  a row in source `d`, class `c` has weight proportional to `1 / n[d,c]`, then
  the batch loss is `sum(row_ce * row_weight) / sum(row_weight)`.
- Seed 1030; dropout 0.15; batch size 128; AdamW learning rate `8e-4`, weight
  decay `1e-3`; cosine schedule; at most 80 epochs; gradient-norm cap 1.0;
  patience 12; deterministic CUDA with `CUBLAS_WORKSPACE_CONFIG=:4096:8`.
- Early-stop ordering is S36 dev macro F1, S36 dev accuracy, S28 dev macro F1,
  S28 dev accuracy, then negative summed dev cross entropy.
- Raw 25-way argmax only; temperature is metadata and never changes argmax.

## Capacity rule

Train `concat-h64` first.  If and only if h64 misses any dev gate, train
`concat-h128`.  Select the first candidate in that fixed ascending-capacity
order passing every gate.  If neither passes, stop; do not inspect test labels
and do not add rules, retries, fallback, or more candidates.

No state tuning candidate is included in S36.  S35 isolated the failure to
missing prefix supervision while the same zero-state representation retained
98.6% current-row accuracy and exact offline/product parity.  State tuning is a
later independent ablation only after the corrected data/Head baseline exists.

## Dev metrics and gates

S36 dev uses all 765 prefix decisions and S28 dev uses all 750 retention rows.
A candidate is eligible only if:

1. S36 prefix accuracy and 25-class macro F1 are each at least 0.96;
2. S36 history and current accuracy are each at least 0.96;
3. both S36 languages and each present position are at least 0.95;
4. each S36 supported class has recall at least 0.90;
5. all six previously frozen sibling-boundary groups are at least 0.95;
6. S28 retention accuracy and macro F1 are each at least 0.99;
7. every S28 canonical class has nonzero true positives;
8. portable JSON Head replay has equal argmax and maximum absolute logit
   difference at most 0.005;
9. test labels accessed, test metrics, RWKV generation, sampling,
   postprocessing, fallback, tool execution, and Executor calls are all zero.

## After dev selection

Lock the selected Head file/hash and evaluator before reading test labels.  Run
all 995 S36 test prefixes and all 750 S28 test retention rows exactly once.
The regression is confirmatory, not blind, because S35 already exposed S30 test
metrics.  Product activation remains locked unless the fixed test gates and a
new real GPU0 product parity canary both pass.
