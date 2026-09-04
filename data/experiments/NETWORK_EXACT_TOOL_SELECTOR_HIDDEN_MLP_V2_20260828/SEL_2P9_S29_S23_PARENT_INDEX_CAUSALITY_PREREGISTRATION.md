# NET-SEL-2P9-S29 S23 parent-index causality preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Purpose

This is a diagnostic causality ablation, not an acceptance rerun and not a
replacement for the consumed S28 blind test.  It quantifies one discovered
S23 projection defect while freezing the locked S28 model, all 245 labels,
all task requests, all action outcomes, and the compact V3 protocol.

## Fixed identities

- S23 rows SHA-256:
  `45aa37308ae7ac4aa0c2f19f9671ecfa4899be38ac95dccf81a82b3ea96d25f7`;
- consumed S28/S23 predictions SHA-256:
  `6360bed681c0cf576ecc1ca305c3a538a1ae535e537f5d9e484fa6127d28ab00`;
- locked S28 head file SHA-256:
  `e370ed7ca404c70dd64c5174a4b8277e05f2d924ae1dd8004b22ca8d2a856d86`;
- locked head hash:
  `b0ee9c854602147bdb0949ae6dc11db9ab660eb33a3b6eaeef2f25c8eb9220da`;
- model weights SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- physical GPU0, local modified vllm-rwkv revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- zero initial Selector state and current-step mean hidden feature.

The consumed comparison is 103/245 overall, 86/120 first, 17/125
continuation, and 7/99 for continuation `final_answer`.

## Single registered intervention

`generate_network_selector_current_harness_ecra_s23_v1.py` constructs a
continuation input after appending action `k`, but passes a synthetic parent
whose `action_index` is also `k`.  The production projection then sees no
action with `sequence > parent.action_index`, so every continuation loses the
new `succeeded_operations` or `failed_operations` delta.

For every frozen S23 continuation row only, reconstruct the progress delta
that production would have produced from the previous Selector checkpoint:

- keep `completed_stage_count`, `action_index`, and
  `protocol_rejection_count` unchanged;
- read the already-frozen minimal `latest_action` fact from
  `CurrentDirectStageV1`;
- if its `success` is true, set `succeeded_operations` to its single
  operation and `failed_operations` empty;
- otherwise set the inverse;
- change no task, label, stage fact, action outcome, tool menu, model state,
  head, feature rule, or metric.

All case trajectories are replayed persistently from zero.  No RWKV text is
generated, no sampling occurs, and all 25 logits/raw argmaxes are retained.

## Fixed comparisons

- exact accuracy overall, first, continuation, and continuation
  `final_answer` recall;
- per-row raw argmax transition between the consumed defective projection and
  the corrected projection;
- first-step invariant: all 120 first labels and argmaxes must remain
  unchanged because their rendered inputs are unchanged;
- causal support is recorded only if all 125 continuation rows required the
  registered correction, the first-step invariant passes, continuation exact
  strictly improves over 17/125, and continuation `final_answer` exact
  strictly improves over 7/99.

No threshold from this diagnostic authorizes integration.  Any remaining
first-step errors and any disagreement with current tool semantics must be
handled separately in a new independent dataset/ablation.
