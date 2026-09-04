# Network Selector S71 diverse-boundary 2K V1 — preregistration

Date: 2026-08-31 (Asia/Shanghai)

Frozen before S71 dataset generation, feature extraction, or model forward.

## Trigger and measured cause

S70 zero state failed dev at `0.944 / 0.940371 / 0.40`.  All four
train-only states were then compared under the unchanged gate; the best was
S70-ST1000 at `0.952 / 0.950049 / 0.55`, so S70 state tuning was rejected and
no candidate opened its locked test.

The frozen dev-error projection shows a corpus-coverage defect rather than an
example-count defect:

- all five heads fit the 2,000 training rows at `1.0 / 1.0 / 1.0`;
- every one of ST1000's 24 dev errors is semantic core variant 1;
- the zero candidate has 28 errors, also all variant 1;
- 19 rows fail all four state candidates and 13 fail all five candidates;
- errors concentrate in the near-effect boundaries `replace_text`,
  `remove_line`, `write_file`, `write_json`, `copy_file`, and
  `list_directory`.

S70 trained only two repeated semantic cores per label/language.  S71 keeps the
2,000-row budget and replaces repetition with four balanced semantic cores and
more surface/context combinations.  It does not add model calls, labels, tool
schemas, or postprocessing.

Evidence:

- S70 dev comparison SHA-256:
  `0e90ae8fdbb7e9b76e2f1559624dd6abe533bbed4008f9cf3b5ef742db4cf6bc`
- S70 failure analysis SHA-256:
  `ae03f33bae3fbe1f808c4ff85877ed8fb7c87e3c85c874627ece41ef86af5793`

## S70 locked-test disposition

After S70 had already been rejected on dev, one S70 test row was parsed during
a field-structure inspection.  The complete S70 test split is therefore
quarantined from all future locked/release use.  Its contamination record
SHA-256 is
`9d3b92994ad9014594fe9b28d3b8feca90d7bb11a8498c2e0ef03c115780bc2f`.

S71 may explicitly reclassify all 500 quarantined S70 test rows as a visible
development corpus.  They may select/reject S71 candidates but may not supply
optimizer gradients.  This reclassification and label access must be recorded;
the rows are no longer described as locked or blind.

S71 must generate a wholly new 500-row locked split with new requests, roots,
contexts, source families, and effect/contrast wording before any feature
extraction.  After generation, S71 test rows must remain skipped before JSON
parsing until exactly one candidate is frozen on dev.

## Fixed corpus and architecture

- Counts remain train/dev/locked = `2000/500/500`, 25 labels, `80/20/20`
  rows per label, and exact English/Chinese balance.
- Train has four balanced current-V2 semantic cores per label/language:
  S67 canonical core 0, S67 held-out core 1, S69 formal core 0, and the
  previously failing S69 formal core 1.  Each core appears ten times per
  label/language under disjoint modifiers and contexts.
- Dev is the explicitly visible reclassification of S70's quarantined former
  test effect/postcondition corpus.  Dev never supplies state or head optimizer
  updates.
- Locked test uses a new S71 relation/effect inventory and is not derived from
  S70 dev strings.
- Every row remains a fresh or canonically re-bound
  `CurrentDirectStageV2` single-responsibility input under input protocol V7.
  No S65/V1 continuation, Executor text, Planner JSON, parameter schema, or tool
  result is allowed.
- The complete immutable requirement stays byte-exact at the input tail.

## Fixed candidates and gates

- First evaluate the unchanged 2.9B zero state using the same validated quality
  engine, `fp32io16`, physical GPU0, one-forward
  `global_mean + suffix_mean + final_last`, and the frozen
  `DualViewGatedH128` training algorithm/seed.
- Dev gate remains accuracy `>=0.96`, macro-F1 `>=0.96`, and every class recall
  `>=0.90`; raw argmax only.
- If zero passes, state tuning is forbidden.  If zero fails, one new S71
  train-only 2,000-step state run may compare checkpoints 500/1000/1500/2000
  under the same dev gate and select the smallest passing step.
- Exactly one frozen dev-passing candidate may open S71 locked once.  Locked
  gate remains `0.96 / 0.96 / 0.90`; a failure rejects S71 without retraining,
  threshold edits, calibration, or output repair.

## Integrity and completion

Do not modify, delete, hide, reorder, truncate, repair, or replace RWKV states,
hidden features, raw logits, trainer logs, or generated text.  Generation uses
no RWKV and no sampling.  Use WSL, `uv`, and GPU0 only; preserve
`rwkv-8222:18070` and do not use GPU1/2.

A locked pass is not release.  Historical/current retention, service artifact
parity, real Harness canary, failure injection, retrieval quality, and the full
project regression remain mandatory.
