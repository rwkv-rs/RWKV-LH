# S70 zero-state train/dev feature extraction protocol

Date: 2026-08-31 (Asia/Shanghai)

This protocol is frozen before any S70 model forward.

- Input cases SHA-256:
  `2895e10545ab4a1c98e4746b38a135167a1794c9dcfdb804ffd61358ea8d4f98`.
- Input manifest SHA-256:
  `34584d0c755f40e4c8cc286d907eca8d840f5f9bc84614d1d2dcac019aac5f21`.
- Parse exactly 2,000 train and 500 dev rows.  Skip all 500 locked-test
  lines before JSON parsing; access zero test labels and compute zero test
  metrics.
- Physical GPU0 only.  Zero state only.  Model, model artifact revision,
  quality-engine revision, source-validation evidence, runtime-derivation
  attestation, WKV `fp32io16`, and GPU UUID are identical to the accepted S68
  extraction protocol.
- Replay bootstrap and prior compact steps exactly.  For the current step,
  obtain `global_mean`, request-suffix `suffix_mean`, and `final_last` from one
  and the same forward.  The suffix starts at the value following the unique
  serialized `complete_requirement` marker.
- Store float32 hidden views, identity metadata, token counts, and hashes in
  20-row shards without labels.  Do not generate or sample text.  Do not
  modify, delete, hide, reorder, truncate, repair, or replace hidden states or
  logits.
- The S68 extraction implementation is reused as a frozen algorithm, with only
  S70 paths, hashes, schemas, and output directory rebound by the S70 runner.
  Its registered aggregate feature-protocol identifier remains unchanged to
  denote exact algorithm identity.
- Refuse replacement of any pending or completed S70 output.  Verify the
  remote product health before, every 500 rows, and after extraction; do not
  stop or replace `rwkv-8222:18070`.
