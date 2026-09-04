# NET-SEL-2P9-S34 V3 fusion product shadow-canary preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Purpose

Validate that the accepted S34 `concat-h64` artifact produces the same raw
25-logit decisions through the actual local product client/service and
persistent GPU0 vllm-rwkv lane as it did through the frozen offline path.
This is a shadow canary: it does not execute Harness tools, invoke the 13.3B
Executor, write `.env.local`, generate RWKV text, or alter a live run.

## Frozen runtime identity

- engine revision `67f0c5996c50dca0ad779da545cb491527de988f`, clean bundled
  source under `data/runtime/engines/vllm-rwkv-67f0c5996c50`;
- 2.9B weights SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- locked h64 head file SHA-256
  `fe97f9eed3e96a63efb4937fc79e884399585dca1af37aa224d4477e73a3410e`;
- locked head hash
  `6e2553e41dca4a3d3402e3f99b919c2b767a23d3fc64cba0662a9744b264a41d`;
- feature protocol
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`;
- explicit `zero` state profile with SHA-256 `00...00`; registry manifest
  SHA-256
  `706ff62cc8ae5851f9c918509911d4ee701f9db5d00bef16f24d2a568e3a0b47`;
- compact/product source SHA-256 values:
  V3 renderer
  `2d5668e9a7c4590670bcb9af4ed93df74e97de8bc49d0980db2e0f7479f62a6b`,
  artifact loader
  `f9895ee651d48b0422c54a214545fc37eab085adfb2dbdab806076a1f26a89ad`,
  client
  `99734cda8edf923a9b9fdfde4b3bad2dbc91fbde12b4cf0b7c6c757a2b306d55`,
  service
  `8891b0a610a218a9b22eb77fa5e0c1cd0f1915e1d03997525b6efe9d72d7de4c`,
  persistent extractor
  `bc6a362361f24e16e3f72c8069426b582e96bb251bd1c67804bac4eb5933341d`.

The reference predictions are the already consumed one-shot S34 blind file,
SHA-256
`6a09c0f7b186f695df64488c1ec967f6ae205306a0988a795e2a1e164647e7ed`.
No new model/head choice is made in this canary.

## Fixed coverage

Select exactly 25 frozen S30 test rows: English variant `000`, one registered
row for each class in the canonical 25-class order.  For every selected row:

1. product V3 bootstrap and every step must equal the frozen training/eval
   rendering byte-for-byte;
2. replay every registered history input through the same per-case persistent
   Selector lane before the current decision;
3. send the current step through `/v3/select` using the production client;
4. retain the complete request identities, checkpoint chain, 25 raw logits,
   raw argmax, and elapsed time;
5. compare current online logits and argmax to the content-addressed offline
   blind record for the same sample.

No replacement row, retry, second head, state, mask, threshold, output repair,
or Executor fallback is permitted.  Transport-level idempotent response replay
is not counted as a retry and is not intentionally invoked here.

## Gates

The canary passes only if all are true:

- exactly 25 current decisions and all 25 expected classes are covered once;
- every bootstrap/current/history V3 rendering is byte-identical to frozen
  S30 data;
- first calls carry `SelectorMenuV3 + SelectorTaskV3`; continuations carry no
  bootstrap and use `SelectorStepV3`;
- every parent checkpoint is the immediately preceding Selector checkpoint,
  token positions strictly increase, and all checkpoints remain on the 2.9B
  Selector lane/profile, separate from any Executor state;
- every current online raw argmax equals the frozen offline raw argmax;
- per-row maximum absolute raw-logit difference `<=0.005`, and global maximum
  `<=0.005`;
- all response rows retain 25 finite logits with `postprocessed=false` and
  `generated_text=false`;
- request wire contains no parameters, arguments, results, Executor text, or
  full tool output;
- service runtime identity is exact V3/fusion/zero-state identity;
- no generation, sampling, Harness tool execution, or 13.3B call occurs;
- current-decision median latency `<=3.0s` and p95 `<=5.0s`, excluding model
  startup but including HTTP, state load/save, one current RWKV forward, h64
  head, and response commit.

Failure leaves `.env.local` inactive and requires a separately recorded root
cause.  Passing authorizes writing only the exact pinned selector identity to
`.env.local` and a non-tool-executing health smoke; it does not establish full
Harness quality or activate S31.
