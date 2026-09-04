# SEL-2P9-S38 matched-prefix data and Head preregistration

## Root cause and non-adaptation rule

S36 corrected current-only supervision and raised the frozen S30 full-prefix
test from 81.61% to 93.07%, while retaining S28 at 99.87%.  S37 still failed
the fixed 96% deployment gate.  S38 does not tune against individual S37 test
errors.  It corrects two independently auditable generator defects:

1. S30 `depth_schedule(split, language_index)` includes the queried
   `language_index` inside the sort seed.  It therefore builds a different
   permutation for every query instead of indexing one fixed permutation of
   the registered 50/30/20 depth multiset.  The resulting prefix counts were
   train/dev/test = 3336/765/995, so dev was not structurally representative of
   test.
2. S30 constructs `source_by_label` from only v2.4 `train` rows and then uses
   that pool for all three S30 splits.  The frozen v2.4 dev and test operation
   intent pools remain unused by S30/S36 and provide a genuinely separated
   source partition.

No S37 prediction, confusion pair, or test feature may enter S38 generation,
training, weighting, capacity selection, or threshold selection.

## Frozen sources and architecture

- Operation-contract source:
  `data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl`
- Source SHA-256:
  `78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc`
- Frozen S30 trajectory builder dependency:
  `scripts/generate_network_selector_true_trajectory_s30_v1.py`
- Dependency SHA-256:
  `ab4d7c821e347fc7955945355b4b03fc1a0be8fffb4bc00caf5f261815672d21`
- S28 retention dataset SHA-256:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`
- S28 feature manifest SHA-256:
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`
- Model: `rwkv7-g1i-2.9b-vllm-v1`.
- Model SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- Engine revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`.
- Input: unchanged compact V3 names/descriptions-only protocol.
- Features: exact same-forward `[mean, last]` concat, dimension 5120.
- State: explicit native zero state; no state tuning in this ablation.
- Outputs: all existing 25 canonical classes in their existing order.

## Matched trajectory generation

Build the same number of base trajectories as S30: train/dev/test =
2000/500/500, balanced by the 25 current-position labels and by English/Chinese
inside every label/split.

- For target split `train`, draw English operation intents only from v2.4
  `train`; for `dev`, only v2.4 `dev`; for `test`, only v2.4 `test`.
- Preserve the frozen S30 compact task construction, predecessor/successor
  semantics, completion semantics, progress projection, V3 renderers, and
  Chinese operation contract.
- Replace only the defective depth function.  For each split, construct one
  deterministic fixed assignment of depths and index it by `language_index`:
  - 40 train examples per label/language: 20 depth-0, 12 depth-1, 8 depth-2;
  - 10 dev examples per label/language: 5 depth-0, 3 depth-1, 2 depth-2;
  - 10 test examples per label/language: the identical 5/3/2 multiset with a
    split-distinct deterministic ordering.
- Preserve S30's explicit completion depth and ABSTAIN behavior; these have
  exact split-scaled counts.
- Expand every base trajectory into every callable prefix exactly as S36 did.
- Use opaque hash IDs containing no label, language, split, or source sample
  identifier.  Store source row/content digests for traceability; feature
  shards must not store labels or label-bearing IDs.

Frozen derived counts:

- train: 2,000 trajectories + 1,428 history positions = 3,428 prefixes;
- dev: 500 trajectories + 357 history positions = 857 prefixes;
- test: 500 trajectories + 357 history positions = 857 prefixes;
- total: 3,000 trajectories, 5,142 prefixes.

The dataset must live at
`data/datasets/rwkv_lh_network_selector_matched_prefix_s38_v1/` with source,
version, purpose, generator hash, generation method, file hashes, exact counts,
class distributions, fixed depth schedules, render validation, and split
isolation in its manifest.

## Feature extraction

Use GPU0 and the bundled engine.  For each base trajectory, advance its V3
bootstrap once from zero state and each step once on the same persistent state.
At every callable prefix, retain mean and last features from that same step
forward.  Store float32 finite tensors, opaque IDs, split/language/position/kind
metadata, and token counts.  Labels, generation, sampling, and test metrics are
forbidden from feature shards.

## Fixed training and capacity selection

- Before JSON parsing, skip every raw `test` line for both S28 and S38.  Test
  labels/features may not affect normalization, training, early stopping,
  temperature, weighting, or selection.
- Train on S28 train (6000 rows) plus S38 train (3428 prefixes); select only on
  S28 dev (750) plus S38 dev (857).
- Use the same S36 fixed optimization: seed 1030, dropout 0.15, batch 128,
  AdamW `8e-4`, weight decay `1e-3`, cosine schedule, maximum 80 epochs,
  gradient cap 1.0, patience 12, deterministic GPU0, and unweighted train-only
  feature mean/std.
- Give equal total loss mass to each `(dataset source, canonical class)` pair
  with row weight proportional to `1/n[source,class]`.
- Early-stop ordering is S38 dev macro F1, S38 dev accuracy, S28 dev macro F1,
  S28 dev accuracy, then negative summed dev loss.
- Train h64 first; train h128 only if h64 misses a dev gate.  Select the first
  ascending-capacity candidate passing all gates.  Do not add candidates.
- Raw 25-way argmax only; no rules, label repair, temperature argmax,
  postprocessing, fallback, or Executor routing.

## Dev gates

1. S38 overall accuracy and macro F1 each at least 0.96;
2. S38 history and current each at least 0.96;
3. both languages and positions 0/1/2 each at least 0.95;
4. every supported class recall at least 0.90;
5. all six frozen sibling boundaries at least 0.95;
6. S28 accuracy and macro F1 each at least 0.99 and all 25 classes have true
   positives;
7. portable/product Head replay equal argmax with max logit difference <=0.005;
8. test access, generation, sampling, postprocessing, fallback, tool execution,
   and Executor calls all zero.

## Locked test

After a dev candidate passes, freeze the Head and evaluator before reading any
S38 test label.  Run exactly once on all 857 previously unconsumed S38 test
prefixes and all 750 S28 test retention rows.  Use the same gates as dev, with
exact fixed counts.  This may be called a one-shot source-held-out regression,
not a hidden-label blind benchmark.  A passing result unlocks, but does not
replace, a real GPU0 V3 product canary; `.env.local` remains unchanged until
that canary passes.
