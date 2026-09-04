# NET-SEL-2P9-S24 current-Harness 2K result

Date: 2026-08-28 (Asia/Shanghai)

## Disposition

Rejected.  The zero-learned-state S24 head is not integrated and was not run on
S23.  Its failure is the registered evidence that permits the separately
numbered S25 2.9B Selector state-tuning ablation; it does not permit threshold
changes, class masks, generated Selector text, 13.3B fallback, or any Harness
replacement.

## Frozen identities

- S24 cases SHA-256:
  `0349d9df08dd3e28418b5bc15415646d50a7d38c4c3d29e489c633392dba7601`;
- feature manifest SHA-256:
  `ab7a407df1308f4e1cae43459e5a9a35cd74b6630d4e4ae5c035fef9e48b28b4`;
- training summary SHA-256:
  `0f26de99e39addbaf82402773dca3142ade213b10fe66017306bb1b2ae6e3ab7`;
- report SHA-256:
  `80e5fbb27f332d3dfdd1bed9d21ef229ce63487302fb810217c1f5c0e1b6efcd`;
- head file SHA-256:
  `69284ab79ce547d27eeff96aa79cdbfa2669f43df7662b212979c13546a57cad`;
- head hash:
  `22d12cebd5a0750bcbfa3db858ac31898e6f8bd7ae90bce8c0ac40934642187e`;
- 2.9B model SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- initial Selector state: exact zero;
- physical device: GPU0;
- feature: current-step mean hidden after the bootstrap and step were processed
  through the same persistent recurrent state.

No RWKV text was generated, no sampler ran, every prediction retained all 25
raw logits and raw argmax, and no Executor fallback or postprocessing ran.

## Metrics

| split | accuracy | macro-F1 | search boundary |
|---|---:|---:|---:|
| train | 0.9585 | 0.9366 | 0.9495 |
| dev | 0.8225 | 0.5872 | 0.8913 |
| balanced test | 0.4040 | 0.3802 | 0.1333 |

On balanced test, `connector_lookup` and `read_file` recall were zero;
`web_search` recall was 0.20.  Accuracy, macro-F1, all-class recall,
new-operation recall and search-boundary gates all failed.  The large train to
balanced-family test gap is evidence of insufficient zero-state hidden
generalization at this exact current-Harness input boundary, not an ECRA score
and not a comparison against invalid old-route positions.

The S24 test was read exactly once after dev-selected epoch 18.  S23 remains
untouched for the next candidate that first passes the internal and causal
gates.

