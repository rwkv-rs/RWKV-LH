# NET-SEL-2P9-S28 compact current-Harness >=96% preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Objective and architecture

S28 must reach at least 96% exact 25-class tool selection on a new frozen blind
set while retaining every current Harness capability. The product architecture
remains the direct `LongHorizonModel -> Harness` path:

- one independent 2.9B RWKV Selector receives only the literal task, bounded
  progress, and all tool names/descriptions;
- one persistent 13.3B RWKV Executor receives the selected tool's full schema
  and remains solely responsible for arguments, paths, search queries,
  execution, Observation interpretation, continuation, and final synthesis;
- Selector and Executor states remain separate;
- no Planner, extra model call, keyword router, class mask, tool deletion,
  generated selection text, output repair, or 13.3B selection fallback is
  permitted.

The class set remains exactly 25: 23 executable tools plus `final_answer` and
`ABSTAIN`.

## Registered compact input

V2 remains immutable. S28 evaluates the additive V3 protocol in
`rwkv_lh/exact_tool_selector/compact_protocol_v3.py`, SHA-256
`976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508`.

V3 makes two input-only changes:

1. all 25 descriptions are shorter and explicitly contrast common siblings;
2. the fixed menu is rendered before the literal task, so the RWKV recurrent
   state sees the task after the long invariant menu.

The current stage and bounded progress remain a separate persistent
`SelectorStepV3`. Parameter schemas, arguments, full tool results, Executor
text, workspace listings, hidden labels, and generated RWKV text remain
excluded.

The already-consumed S26 diagnostic is not an acceptance set. It showed
`0.950` exact accuracy with V3 mean hidden versus S27's `0.922`, and may be used
only as root-cause evidence, never for S28 model selection or acceptance.

## Frozen S28 data contract

- train/dev/blind test: exactly `6000/750/750`;
- every split contains all 25 labels with exact balance:
  `240/30/30` rows per label;
- train language per label: English 160, Chinese 80;
- dev and test language per label: English 15, Chinese 15;
- train phase per label: first 120, continuation-1 96, continuation-2 24;
- dev and test phase per label: first 14, continuation-1 12,
  continuation-2 4;
- every continuation records and replays its exact prior Selector steps on one
  persistent WKV lane;
- train English covers all six frozen v2.4 operation-contract variants plus
  contrastive natural frames; dev and test use disjoint held-out lexical
  families;
- Chinese uses independently partitioned frames and entities;
- exact rendered trajectories, semantic families, held-out lexical-family IDs,
  and entity IDs may not cross splits;
- the literal request itself must identify the current operation; no legacy
  hidden stage label may determine the target;
- maximum UTF-8 byte-5gram cosine against frozen ECRA instructions must remain
  below `0.75`.

The generator must record source/version/purpose, row counts, split and family
audits, protocol hash, file hashes, and exact generation command under
`data/datasets/` before feature extraction.

## Frozen feature and head candidates

- physical GPU0 only;
- unchanged local modified vllm-rwkv revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- unchanged 2.9B vLLM weights SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- initial Selector state: zero; S28 does not use S25/S27 or any Executor state;
- batch size 1; exact bootstrap, history, current-step persistent replay;
- feature views: current-step real-token `mean` and `last`, obtained without
  generation or sampling;
- MLP candidates: `2560 -> {256,512} -> 25` for each feature view;
- GELU(tanh), LayerNorm, dropout `0.15`, class-balanced cross entropy;
- seed `919`, maximum 80 epochs, batch 128, AdamW LR `8e-4`, weight decay
  `1e-3`, cosine schedule, gradient clipping 1.0, patience 12;
- train normalization only; test labels and metrics are unavailable to the
  trainer and candidate selector.

Candidate selection uses only this fixed dev ordering:

1. highest dev macro-F1;
2. highest dev exact accuracy;
3. lowest dev cross-entropy;
4. smaller hidden dimension;
5. `mean` before `last`.

A candidate is locked for blind evaluation only if dev exact accuracy and
macro-F1 are both at least `0.97`, every-label recall is at least `0.90`, both
language accuracies are at least `0.96`, every phase accuracy is at least
`0.95`, and every registered sibling-boundary accuracy is at least `0.95`.
If no candidate passes, S28 stops without reading blind labels.

## One-shot blind gates

The locked artifact may evaluate the 750-row blind split exactly once. It must
simultaneously satisfy:

- exact accuracy `>= 0.96` (at least 720/750);
- macro-F1 `>= 0.96`;
- every-label recall `>= 26/30`;
- English and Chinese accuracy each `>= 0.95`;
- first and continuation-1 accuracy each `>= 0.95`;
- continuation-2 accuracy `>= 0.90`;
- each sibling boundary below has exact accuracy `>= 0.95`:
  - `read_file/read_json`;
  - `search_text/web_search/connector_lookup`;
  - `write_file/write_json/patch_json`;
  - `copy_file/move_file`;
  - `check_command/run_command`;
  - `final_answer/ABSTAIN`.

All 25 raw logits and raw argmaxes must be retained. Temperature may be stored
for calibration but may not change argmax. Any mask, threshold override,
postprocessing, retry, generated selection output, or Executor fallback rejects
the run.

Only a fully passing S28 artifact may run once on the unchanged S23 245-point
current-Harness comparison. Passing the synthetic blind set does not itself
authorize product deployment.
