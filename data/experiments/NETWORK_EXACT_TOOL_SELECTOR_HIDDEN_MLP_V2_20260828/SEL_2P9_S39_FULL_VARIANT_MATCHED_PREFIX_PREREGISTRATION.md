# SEL-2P9-S39 full-variant matched-prefix preregistration

## Dev-only finding

S38 correctly matched depth distributions and separated v2.4 source pools.
Without reading any S38 test label, h64 reached 96.97% / 97.51% macro F1 on
857 dev prefixes and retained S28 at 100%, but English was 93.94% while Chinese
was 100%.  No S38 candidate was locked and S38 test remains unparsed.

Code inspection found one residual S30 assumption: after S38 selected distinct
v2.4 train/dev/test pools, the frozen `english_intent` still applied
`VARIANTS = train:(0,1,2,3), dev:(4), test:(5)`.  That filter was needed only
when S30 derived every split from one v2.4 train pool.  With truly distinct
source pools it discards one third of train English contracts and five sixths
of each dev/test pool, creating an unnecessary lexical bottleneck.

S39 changes exactly this data variable: inside each already separated v2.4
source split, all six contract variants are eligible.  It does not use S37 or
S38 test predictions, change thresholds, add class rules, or change RWKV.

## Frozen inputs and unchanged design

- S38 generator dependency:
  `scripts/generate_network_selector_matched_prefix_s38_v1.py`
- Dependency SHA-256:
  `dc7629016694a61a0be7c16827b872d178dbe0882269474f8b9d86b995c82752`
- v2.4 source SHA-256:
  `78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc`
- S30 builder SHA-256:
  `ab4d7c821e347fc7955945355b4b03fc1a0be8fffb4bc00caf5f261815672d21`
- S28 retention dataset and feature manifest SHA-256:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`,
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`.
- 2.9B model SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`.
- Engine revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`.
- Same compact V3 input, 25 labels, zero state, and same-forward mean+last
  dimension-5120 representation.

## Dataset

Reuse S38's fixed depth assignment, split-specific source pools, trajectory
semantics, prefix closure, opaque IDs, and validations.  Before constructing
any row, set each target split's allowed source variants to `(0,1,2,3,4,5)`.

Counts remain frozen and exactly matched:

- train: 2,000 trajectories, 3,428 prefixes;
- dev: 500 trajectories, 857 prefixes;
- test: 500 trajectories, 857 prefixes;
- total: 3,000 trajectories, 5,142 prefixes.

The dataset lives under
`data/datasets/rwkv_lh_network_selector_full_variant_matched_prefix_s39_v1/`.
Its manifest must record all source/dependency/generator/file hashes, exact
counts, per-split source-pool usage, depth distributions, opaque-ID checks,
render equality, and zero split overlap.  S39 test labels must remain unused
until a Head is locked from train/dev.

## Extraction, training, and gates

Feature extraction and training are byte-for-byte the frozen S38 algorithms
with only S39 paths, hashes, row counts, and experiment labels substituted.

- GPU0; native zero state; one bootstrap and one forward per real prefix;
  same-forward mean+last; no labels in feature shards; no generation/sampling.
- Train S28 6000 + S39 3428; dev-select S28 750 + S39 857; skip raw test lines
  before JSON label parsing.
- Equal total loss mass per `(dataset source, class)`; train-only unweighted
  normalization; seed/hyperparameters unchanged.
- h64 first, h128 only if h64 misses any gate; no further candidate.
- Gates are unchanged: S39 accuracy/macro F1 >=0.96; history/current >=0.96;
  both languages and positions >=0.95; every supported class recall >=0.90;
  six sibling boundaries >=0.95; S28 accuracy/macro F1 >=0.99 with all classes
  true-positive; portable replay <=0.005 and equal argmax; all forbidden paths
  zero.

After dev lock, freeze a new evaluator before parsing all 857 S39 test labels
exactly once.  Test uses the same gates plus S28's 750-row retention test.  A
pass unlocks only the real GPU0 product canary; `.env.local` remains unchanged
until product parity also passes.
