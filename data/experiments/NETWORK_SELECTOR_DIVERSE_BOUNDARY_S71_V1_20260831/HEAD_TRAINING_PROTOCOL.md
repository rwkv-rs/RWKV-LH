# S71 zero-state head training protocol

Date: 2026-08-31 (Asia/Shanghai)

Frozen after feature-manifest validation and before loading any S71 feature
shard into an optimizer.

- Dataset cases SHA-256:
  `aaaaccfbd1bb5e7afe7bbcc64e0ea2b1283f1808413e93f497d90d1ed749088c`.
- Dataset manifest SHA-256:
  `b01c739babbc6cfd3eb8a92b7dd6250504110df2e42f270ebdba7a7091bd82ca`.
- Zero-state train/dev feature manifest SHA-256:
  `3e95b9d4a64c62db4ae18576c4703742871d3fdd6ccae851f6504391f467c344`.
  All 125 registered feature-shard hashes passed before this protocol was
  frozen.
- Load exactly 2,000 train and 500 visible dev labels. Skip all 500 newly
  sealed S71 test rows before JSON parsing; test labels, features, and metrics
  remain unused.
- Reuse the frozen S67/S68 `DualViewGatedH128`, normalization, optimizer,
  deterministic seed `1067`, epoch-selection order, metric implementation,
  and raw-logit convention byte-for-byte. Concatenate
  `global_mean + final_last` as the global branch and use request
  `suffix_mean` as the tail branch.
- The visible dev corpus is the declared S70-test reclassification and never
  supplies optimizer gradients. Select only by its dev metrics.
- Accept zero state iff accuracy `>=0.96`, supported macro-F1 `>=0.96`, and
  every supported class recall `>=0.90`, using unmodified raw argmax.
- Persist the selected head state, normalization, complete training history,
  and all 2,500 raw train/dev logits. Do not postprocess, reorder, truncate,
  repair, replace, hide, or modify hidden features, raw logits, RWKV state, or
  RWKV output.
- This step performs zero RWKV forwards and zero sampling calls. GPU0 is used
  only for the fixed head optimization; GPU1/2 and product service 18070
  remain untouched.
- If zero state fails any dev gate, do not open S71 locked. Follow the
  preregistered single S71 train-only state-tuning branch. If it passes, freeze
  this one candidate before creating the one-shot locked-test protocol.

