# S70 zero-state head training protocol

Date: 2026-08-31 (Asia/Shanghai)

Frozen before loading any S70 feature shard into an optimizer.

- Dataset cases SHA-256:
  `2895e10545ab4a1c98e4746b38a135167a1794c9dcfdb804ffd61358ea8d4f98`.
- Dataset manifest SHA-256:
  `34584d0c755f40e4c8cc286d907eca8d840f5f9bc84614d1d2dcac019aac5f21`.
- Zero-state train/dev feature manifest SHA-256:
  `b4a4703faa57cd8fc72758fb5db60f722e739870fb476b7eb2d763354b44a7e2`.
- Load exactly 2,000 train and 500 dev labels.  Skip all 500 locked-test
  rows before JSON parsing; test labels, features, and metrics remain unused.
- Reuse the frozen S67/S68 `DualViewGatedH128`, normalization, optimizer,
  deterministic seed `1067`, epoch-selection order, metric implementation, and
  raw-logit convention byte-for-byte.  Concatenate `global_mean + final_last`
  as the global branch and use request `suffix_mean` as the tail branch.
- Select only by dev metrics.  Accept zero state iff accuracy `>=0.96`,
  supported macro-F1 `>=0.96`, and every supported class recall `>=0.90`.
- Persist the selected head state, normalization, complete training history,
  and all 2,500 raw train/dev logits.  Do not postprocess, reorder, truncate,
  repair, replace, hide, or modify hidden features or logits.
- This step performs zero RWKV forwards and zero sampling calls.  GPU0 is used
  only for the fixed head optimization; GPU1/2 and product service 18070 remain
  untouched.
