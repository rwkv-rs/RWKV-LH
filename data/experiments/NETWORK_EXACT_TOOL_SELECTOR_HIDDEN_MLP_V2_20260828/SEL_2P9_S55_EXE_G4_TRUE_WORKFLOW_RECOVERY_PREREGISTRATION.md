# S55 / EXE-G4 true-workflow recovery preregistration

Frozen on 2026-08-29 (Asia/Shanghai), after the immutable R1 and R2 real-arm
results and before generating S55/G4 data or training either candidate.

## Observed residual and scope

The R2 global metadata correction is retained: it moved `S52+G3` from 4/6 to
5/6, proving that production-shaped persistent Selector inputs matter. The
release combination `S53+G3` remains 5/6 and fails only `E2E-H10`.

The residual is not registered as an H10 special case. It exposes two general
coverage gaps:

1. S53 long workflows were synthetic but did not cover enough natural
   paraphrases of ordered multi-input, dual-output workflows. The real route
   reaches all three inputs, then chooses verification before creating the
   second required output.
2. G3 "multistage" rows have recent action records, but their final
   `current_requirement` usually describes one already selected operation.
   Production repeats the full immutable multi-operation request at the tail.
   With three observed inputs, G3 still emits an unwrapped JSON list and
   un-discounted values despite an observed verifier contract.

No canary task ID, exact filename, exact verifier body, exact expected value,
or raw canary generation may be used for training or candidate selection.

## Frozen joint synthetic source

One generator creates linked but role-pure prefixes for five disjoint workflow
families: two structured arithmetic/dual-output families, one implementation
and verification family, one public-web evidence family, and one structured
connector evidence family. Every trajectory has exactly eight selected
operations and keeps the same full immutable request at every stage.

- Train: 100 trajectories / 800 prefixes (20 trajectories per family).
- Dev: 30 trajectories / 240 prefixes (6 per family).
- Locked test: 30 trajectories / 240 prefixes (6 per family).
- Train/dev/test entities and lexical frames are disjoint.
- Maximum byte-5-gram cosine against all visible E2E and live-network requests
  must be below 0.75. This algorithm and threshold cannot be changed later.
- Selector rows contain only the V4 name/description menu, bounded progress and
  operation/outcome metadata. They contain no parameter schema, result body or
  Executor text. `stage_objective` remains the last field.
- Executor rows contain the exact production bootstrap, bounded recent action
  records, one committed operation schema, and the full immutable
  `current_requirement` as the last closed field before continuation.
- Targets are deterministic programmatic contracts, never RWKV generations.

## S55 2.9B Selector Head

- Base model/state: the unchanged 2.9B model, zero state.
- Feature: one forward pass, `concat(mean,last)` hidden, dimension 5120.
- Parent: frozen S53 h64 Head SHA-256
  `fa25b05e69d484e677d96abe270161ce240449217f39ad81367fc27b6e284fd2`.
- Training sources: frozen S28/S39/S52/S53 train rows plus S55 train rows;
  source/class pairs receive equal total mass.
- Fixed training: physical GPU0, seed 1059, hidden 64, dropout 0.15,
  AdamW, learning rate 0.0001, weight decay 0.001, batch 128, cosine schedule,
  at most 60 epochs, patience 12, gradient norm 1.0.
- Dev gates: S28 accuracy/macro-F1 >=0.99; S39/S52/S53 accuracy and macro-F1
  >=0.96; S55 accuracy and macro-F1 >=0.98; every supported S55 class recall
  >=0.90; portable raw-logit replay argmax exact.
- Locked tests are opened only after dev selection and must satisfy the same
  thresholds. Raw argmax is the decision; no threshold override, retry,
  postprocessing, or generated Selector text is permitted.

## EXE-G4 13.3B state

- Parent state: zero; G4 is a replacement profile, never stacked on G3.
- Train: 1,200 frozen G3 direct-retention rows (50 per each of 24 operations)
  plus the 800 linked true-workflow train prefixes, total 2,000.
- Dev: 240 frozen G3 direct-retention rows (10 per operation) plus 240 disjoint
  true-workflow dev prefixes, total 480.
- Fixed training: server physical GPU0, seed 1059, context 2496, target-suffix
  loss only, BOS 0, BF16, state PEFT, FLA, 2,000 steps, batch 1, LR
  2e-5 -> 2e-6 cosine, warmup 50, checkpoints every 250.
- Candidate order: 250, 500, 750, 1000, 1250, 1500, 1750, 2000; select the
  first checkpoint satisfying every gate.
- Fixed evaluation: one attempt, temperature 0.1, top-p 1.0, top-k 0, raw
  first output. Evaluate zero, frozen G3 and every G4 checkpoint on both the
  frozen G3 dev480 and G4 dev480.
- G4 gate: frozen G3 dev remains 480/480 schema-valid and 480/480 canonical,
  wire and byte exact; G4 dev reaches 480/480 on the same four measures; every
  operation recall is >=0.95; true-workflow rescues versus G3 are positive and
  regressions are zero; state attestation, base model identity and physical
  GPU0 identity are valid.

## Real release factorial and final gates

Using the frozen R2 `S53+G3` 5/6 result as baseline, run `S55+G3`, `S53+G4`
and `S55+G4` under the same six cases and parameters. Keep the smallest
combination that achieves 6/6 without integrity loss. If only the joint arm
passes, retain both profiles because their interaction is experimentally
required.

Only a 6/6 arm may proceed to live-network 2/2, retrieval-quality 9/9 hard
gates and Full90. Full90 must dispatch 90/90 with valid request-last/raw-output
integrity; only `E2E-LH09/mock_api` may be explicitly unsupported. Existing
product port 18070 must remain healthy throughout. Original RWKV outputs and
tokens are append-only and are never induced, rewritten, deleted, hidden or
reordered.
