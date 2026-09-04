# S71 zero-state train/dev feature extraction protocol

Date: 2026-08-31 (Asia/Shanghai)

Frozen before any S71 model forward.

- Input cases SHA-256:
  `aaaaccfbd1bb5e7afe7bbcc64e0ea2b1283f1808413e93f497d90d1ed749088c`.
- Input manifest SHA-256:
  `b01c739babbc6cfd3eb8a92b7dd6250504110df2e42f270ebdba7a7091bd82ca`.
- Parse exactly 2,000 train and 500 visible dev rows. Skip all 500 newly
  sealed S71 test lines before JSON parsing; access zero test labels and
  compute zero test metrics.
- Physical GPU0 only. Use the 2.9B zero state, validated derived quality
  engine revision `0501caa628967103490507d734f6a5efaf165794`, model-artifact
  revision `67f0c5996c50dca0ad779da545cb491527de988f`, and WKV mode
  `fp32io16`.
- Use the attested extractor implementation SHA-256
  `d7ca18fd54ca6d2a835c647ab3d7712a05132e51c1f456cf4c93dbb1f23ef465`;
  its derived-engine state-profile validation uses the model-artifact
  revision and does not alter the zero-state computation.
- Replay bootstrap and prior compact steps exactly. For the current step,
  obtain `global_mean`, request-suffix `suffix_mean`, and `final_last` from
  one and the same forward. The suffix starts at the value following the
  unique serialized `complete_requirement` marker.
- Store float32 hidden views, identity metadata, token counts, and hashes in
  20-row shards without labels. Do not generate or sample text. Do not
  modify, delete, hide, reorder, truncate, repair, or replace hidden states,
  logits, model output, or model state.
- Reuse the frozen S68 extraction algorithm byte-for-byte. The S71 binding
  layer may change only registered paths, hashes, schemas, output directory,
  and the attested extractor implementation hash.
- Refuse replacement of any pending or completed S71 output. Verify the
  remote product health before, every 500 rows, and after extraction; do not
  stop or replace `rwkv-8222:18070`. Do not expose GPU1/2.

