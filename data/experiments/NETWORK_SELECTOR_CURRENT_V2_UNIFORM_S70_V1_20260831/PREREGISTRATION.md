# Network Selector S70 Current-V2 Uniform Semantic 2K V1 — preregistration

Date: 2026-08-31 (Asia/Shanghai)

## Trigger and architectural correction

S68 zero-state passed dev but failed its locked test at
`0.928 / 0.9196358972475079 / 0.15`.  S69 generation then proved that S65's
historical multi-stage V1 continuation rows cannot be replayed inside a current
single-responsibility `CurrentDirectStageV2` atom: a prior successful action can
prematurely satisfy the new atom.  S70 therefore keeps the architecture fixed
and changes only the semantic corpus.

Every S70 row is freshly constructed through the frozen S67 V2 contract and V7
renderer.  No S65 request, action history, V1 stage, locked-test label, Executor
text, Planner JSON, parameter schema, or tool result enters training.

## Fixed corpus

- 25 labels; train/dev/new locked test = `2000/500/500`; every label has
  `80/20/20` rows and English/Chinese are exactly balanced.
- Train has two semantic cores per label/language: 20 contextual repetitions of
  the frozen S67 train core and 20 repetitions of S69's unused formal-definition
  core 0.  Dev is disjoint in wording and roots: 5 repetitions of the S67 dev
  core and 5 of formal-definition core 1 per label/language.
- S69 produced no dataset and no model forward.  Its two formal-definition
  inventories are reclassified here as train/dev sources, never as S70 test.
- S70 locked test uses a new effect/postcondition inventory with two cores per
  label/language and 20 shared 25-class contrastive frames.  It is generated and
  frozen before feature extraction.
- Train, dev, and test root pools, exact requests, source families, rendered
  inputs, and semantic core identifiers must be disjoint.
- Every rendered input must end byte-exactly with the complete immutable
  requirement.  Current hidden features come from one forward only.

The frozen Ladder/E3 holdout and the rejected S68 locked test are isolation-only:
fixed `utf8-byte-5gram-cosine.v1`, exact overlap zero, maximum cosine `<0.95`.
S68 locked labels are never accessed and requests are not persisted in S70.

## Fixed candidate and gates

- Model: 2.9B zero state; quality engine commit
  `0501caa628967103490507d734f6a5efaf165794`; WKV `fp32io16`; physical GPU0.
- Feature views: `global_mean + suffix_mean + final_last` from the same current
  forward.  Head: frozen `DualViewGatedH128`, seed `1067`, same normalization,
  optimizer, epoch selection, and raw-logit persistence as S68.
- Dev gate: accuracy `>=0.96`, macro-F1 `>=0.96`, minimum class recall `>=0.90`.
- If zero-state dev passes, no state tuning is allowed.  If it fails, numbered
  S70 train-only states at `500/1000/1500/2000` may be compared on the same dev
  gate.  Dev never supplies optimizer updates.
- Exactly one candidate may open the S70 locked test once.  Locked gate remains
  `0.96 / 0.96 / 0.90`; failure rejects the candidate without retraining,
  calibration, threshold edits, or logit postprocessing.

Passing the locked gate is not release by itself.  The candidate must then pass
historical S65/S61 retention, artifact/service parity, real Harness canary,
failure-path injection, and the full project test suite.

## Integrity and service constraints

Do not modify, delete, hide, reorder, truncate, repair, or replace RWKV hidden
states, raw logits, or generated text.  Data generation invokes no RWKV and no
sampling.  Use only WSL, `uv`, and GPU0.  Do not stop, replace, or contaminate
`rwkv-8222:18070`; GPU1/2 remain untouched.
