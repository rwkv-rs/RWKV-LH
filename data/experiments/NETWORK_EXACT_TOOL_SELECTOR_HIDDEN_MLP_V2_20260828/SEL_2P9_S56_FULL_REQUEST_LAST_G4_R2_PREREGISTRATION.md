# S56 full-request-last Selector / EXE-G4 R2 preregistration

Frozen on 2026-08-29 (Asia/Shanghai), before S56 data generation, feature
extraction, Head training, G4 training, or any R3 real-arm run.

## Reason for the numbered supersession

The frozen S55/G4 preregistration and generated S55 V4 dataset remain preserved
as diagnostic evidence.  A byte-level audit performed before training found
that V4 places the generic `stage_objective` at the continuation edge while the
complete immutable task appears only in the earlier bootstrap.  This is weaker
than the now-global input rule: stable context first, bounded causal state next,
and the complete current requirement as the final field immediately before the
RWKV continuation point.

S55 is therefore not trained or selected.  S56 changes only the Selector input
layout and preserves S55 labels, split membership, source isolation, tool menu,
progress projection and evaluation thresholds.  The already correct G4
Executor data is unchanged because its closed `current_requirement` is already
the final field.

## Frozen V5 protocol

- Schema: `rwkv-lh.exact-tool-selector-input.v5-full-request-last`.
- Bootstrap: tool names and descriptions, menu identity and the SHA-256 identity
  of the immutable request.  No parameter schema, result body, Executor text or
  full request text appears there.
- Step: schema, bounded progress, stage role, bounded latest-action objective,
  then the complete immutable task in `current_requirement` as the final JSON
  field.  Every causal step repeats that same closed task at the continuation
  edge.
- Selection remains one 2.9B Hidden `concat(mean,last)` + MLP forward and raw
  argmax.  No generated Selector text, threshold override, retry or
  postprocessing is allowed.
- Frozen V5 renderer SHA-256:
  `3d19665e4a85d5296b336acf616a087f4d1e272aa8acebfc5855d7a02edab7bf`.

## S56 deterministic data

The frozen S28, S39, S52, S53 and S55 rows are re-rendered byte-exactly under
V5 without changing labels, split assignments or semantic contents.  Old
protocol strings are parsed only to recover bounded progress, role and stage
objective; V5 output is produced exclusively by the frozen renderer.

- Train: 13,143 rows = S28 6,000 + S39 3,428 + S52 1,615 + S53 1,300 +
  S55 800.
- Dev: 2,571 rows = S28 750 + S39 857 + S52 399 + S53 325 + S55 240.
- Locked test: 2,579 rows = S28 750 + S39 857 + S52 407 + S53 325 +
  S55 240.
- Every rendered input ends in the JSON-escaped full request followed only by
  the closing step object; each row is byte-hashed and unique.
- The S55 public-holdout byte-5-gram cosine result and exclusive 0.75 threshold
  remain frozen.  No visible E2E request, filename, verifier body, expected
  value or raw canary generation is introduced.

Frozen source identities:

- S28 cases: `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`.
- S39 cases: `b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab`.
- S52 cases: `1cb1a1b2597a16c63b92753e402529239d4a765698964e0102640bf70dab7faf`.
- S53 cases: `bd3701c925717eb1d9f75d439c7fbb8b75a4905cc0099e348fa5314b98d1efde`.
- S55 cases: `f183b5ef6389dd4549d245f05be2e9933f9b5efb8bbecaf23ae2184a75de02fe`.
- S55 manifest: `0301ee78e793f80d314fb6f877433b101881bd5ec856bb67691d0fc0c7c4e659`.

## S56 Head training and gates

- Base model/state: unchanged 2.9B model with zero state.
- Parent Head: frozen S53 h64 SHA-256
  `fa25b05e69d484e677d96abe270161ce240449217f39ad81367fc27b6e284fd2`.
- Feature: same-forward `concat(mean,last)`, dimension 5,120; physical GPU0.
- Fixed training: seed 1059, hidden 64, dropout 0.15, AdamW, learning rate
  0.0001, weight decay 0.001, batch 128, cosine schedule, maximum 60 epochs,
  patience 12 and gradient norm 1.0.  Each source/class pair has equal total
  training mass.
- Dev gates: S28 accuracy/macro-F1 >=0.99; S39/S52/S53 accuracy and macro-F1
  >=0.96; S55 accuracy and macro-F1 >=0.98; each supported S55 class recall
  >=0.90; portable raw-logit replay is exactly equal.
- Locked tests open only after dev selection and use the same thresholds.

## G4 and release gates

The G4 dataset, zero-parent state training recipe, checkpoint order and all G4
dev gates remain exactly those in the S55/G4 preregistration.  Its frozen train,
dev and manifest SHA-256 values are respectively
`f5a1e2d3a06c4877bf589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93`,
`a81f3805535649ae75148e0d7debdb3be60e00ba36837b67d0f80fb8113bb50d`
and `ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f`.

Run the fixed real factorial `S56+G3`, `S53+G4`, `S56+G4` against the frozen
R2 `S53+G3` baseline.  Only 6/6 may proceed to live-network 2/2,
retrieval-quality 9/9 and Full90.  Select the smallest passing state set.
Original RWKV outputs and tokens are append-only and may never be induced,
rewritten, deleted, hidden or reordered.
