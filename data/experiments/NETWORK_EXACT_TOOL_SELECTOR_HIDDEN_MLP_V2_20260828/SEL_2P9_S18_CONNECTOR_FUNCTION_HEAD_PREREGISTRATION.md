# NET-SEL-2P9-S18-CONNECTOR-N0 function-head preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Registered residual and minimization order

S17's scoped variable-menu S8 candidate passed every frozen internal gate
except one: `connector_lookup` recall was 23/30 (0.7667) against the fixed 0.85
threshold.  Overall test accuracy/macro-F1 were 0.9160/0.9154 and natural dev
was 176/176.  The failure is therefore isolated to one function.

Before adding another learned initial state, S18 tests the minimum candidate:
one connector-vs-other Hidden/MLP function head over the same zero-state 2.9B
query hidden already used by S8.  Number `N0` explicitly means no additional
learned state.  Only if this fails may a separately numbered
`S19-CONNECTOR-S1` state be trained.

## Frozen 2,000-row train projection

Source is S6 train rows and its zero-state last-hidden feature cache:

- source query SHA-256
  `d60ad4a2404fda0f9401a5858070bb5e3063d408be68c9f88e1c0431eed1313c`;
- feature manifest SHA-256
  `d2b6cf2ecd5c42981f390f94ce779ab2c36349829e185a4e310e78be9500b002`;
- positives: all 690 train `connector_lookup` rows;
- negatives: exactly 1,310 deterministic SHA-256-ranked train rows in fixed
  semantic groups: web 310, read_file 250, read_json 150, deterministic 150,
  other local-read 150, workspace-mutation 150, control/process 150;
- exact rows 2,000; family split and ECRA byte-5gram contamination identities
  are inherited unchanged from S6.

The dataset generator must emit row IDs, source IDs, source kinds, semantic
families, binary labels, fixed group counts, source/feature/protocol hashes and
the exact ranking algorithm.  It makes no model call and generates no RWKV
text.

## Frozen head and hierarchical decision

- input: zero-state final hidden at the last real query token, dimension 2560;
- train-only mean/std normalization;
- MLP `2560 -> 128 -> 2`, GELU, LayerNorm, dropout 0.1;
- class-balanced cross entropy; seed 851; AdamW, LR `1e-3`, weight decay
  `1e-3`, batch 64, at most 80 epochs, cosine schedule, clip 1.0, patience 12;
- best epoch by connector binary dev F1, then dev loss;
- raw two logits and raw argmax only.

At inference the function head is invoked only when Controller's immutable
menu already contains `connector_lookup`.  Raw `CONNECTOR` selects that tool.
Raw `OTHER` delegates to the frozen S8 shared scorer over the same authorized
menu with `connector_lookup` absent.  Both complete raw outputs are retained;
no threshold, score modification, calibration rule, retry or text generation
is allowed.  Menus without connector never call this function head.

## Gates

Internal binary dev/test:

- connector recall >= 0.90 and precision >= 0.90;
- OTHER recall >= 0.95;
- natural connector dev recall >= 0.95;
- mixed/privacy local-first false connector rate <= 0.02.

Complete hierarchical scoped test/natural gates remain exactly S17's gates.
The previously observed S6 test is retained as regression evidence, not claimed
as a new unseen holdout.  Only if all gates pass may the still-unread ECRA120
serve as the one external holdout under the unchanged S17/S2 thresholds.

Passing ECRA authorizes only protocol/service implementation and shadow canary.
Active routing still requires raw-output retention, menu authority, function
state isolation, crash recovery, live 2.9B-to-13.3B handoff, live networking
and the full local Harness regression.  Failure rejects S18 without modifying
S8, S17, any learned state, 13.3B Executor behavior or RWKV output.
