# NET-SEL-2P9-S32 source-balanced zero-state head result

Date: 2026-08-28 (Asia/Shanghai)

Decision: **rejected by the preregistered development conjunction**.  Neither
registered source weight passed all dev gates.  No candidate is locked, S30
blind remains sealed, and S32 changes no client, service, Harness, state
profile, `.env.local`, tool inventory, or 13.3B Executor behavior.

## Fixed architecture and data isolation

- current direct `LongHorizonModel -> Harness` architecture;
- independent 2.9B exact-tool Selector over all 25 classes;
- persistent 13.3B Executor still owns arguments, execution, observation,
  continuation, and summary;
- physical GPU0; zero Selector state; unchanged compact V3 inputs and frozen
  mean hidden features; no RWKV inference was repeated;
- fixed `mean-h512` MLP, seed 1030, unweighted frozen feature normalization;
- only S30 per-row loss weight changed: preregistered `3` and `5`;
- S28/S30 train/dev rows parsed: `6000/750` and `2000/500`;
- S28/S30 test rows skipped before JSON parsing: `750/500`;
- test labels accessed: 0; test metrics computed: false;
- RWKV text generation, sampling, class masks, repairs, threshold overrides,
  retries, postprocessing, and Executor fallback: 0.

Preregistration SHA-256:
`cb82a9d37a4293faf07126ea0600bbe7d64af728d5e8da16b1dd2cbe3631f0b9`.
Trainer SHA-256:
`63cbcbb3a5654136021839f61b55d0a488f91cfa2ceed4397d7c592275ea65ad`.

## Development results

| candidate | effective S28:S30 mass | S28 exact | S30 exact | S30 macro-F1 | EN | ZH | selected |
|---|---:|---:|---:|---:|---:|---:|---|
| `s30w3` | 6000:6000 | 750/750 | 486/500 | 0.971831 | 237/250 | 249/250 | no |
| `s30w5` | 6000:10000 | 750/750 | 486/500 | 0.972001 | 238/250 | 248/250 | no |

Both candidates passed aggregate S30 accuracy/macro-F1, S28 retention, all
stage, future-distractor, portable replay, and integrity gates.  Both failed
the language, minimum-label-recall, and sibling-boundary conjunctions:

- `s30w3`: `file_digest` recall `16/20`; `read_file` recall `17/20`;
  English `237/250`; `read_file/read_json` boundary `37/40`;
- `s30w5`: `read_file` and `remove_line` recall each `17/20`;
  English `238/250`; `read_file/read_json` boundary `37/40`.

Portable JSON replay preserved the sampled raw argmaxes.  Maximum sampled
absolute logit differences were below `4.8e-6`, far inside the `0.005` gate.

Machine-readable selection SHA-256:
`0b81ea2dbc6c186a1fe9780c54a8602a496e34b20dda2e3abf3348eeeb266973`.
The `s30w3` / `s30w5` head hashes are respectively
`5c4ac7a406ad5d3614c25f33fbd34082d95ad905a3083141bf2585bf5daf1823`
and
`c60e7a5601d27e7282a7245ee082da76d2c136cda25fb8aa687a0ace577b5f10`.

## Interpretation and disposition

Increasing natural-trajectory source mass is not sufficient: it makes S28
retention perfect but leaves S30 at exactly 486/500.  The identities of some
errors move with the loss weight, while eight dev cases remain wrong for the
weight-1 reference and both S32 candidates.  The persistent cases are
concentrated in English ordered-workflow continuation and close local-file
boundaries.  This is evidence against simple source-count imbalance as the
remaining root cause.

The frozen extraction already produced two complementary views in one RWKV
forward: current-step mean and current-step last hidden.  Mean alone preserves
the task best (`97.2%`), while last alone is much weaker (`<=93.6%`) but is the
view nearest the latest compact progress.  The next independent ablation
should therefore test one single MLP over `mean || last`, without changing
input text, state, data, model calls, labels, or Executor behavior.  This tests
whether the remaining boundary needs joint task-and-latest-progress
representation; it must be separately preregistered before any dev run.
