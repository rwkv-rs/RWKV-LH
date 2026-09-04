# NET-SEL-2P9-S41 V3 product shadow-canary preregistration

Date: 2026-08-29 (Asia/Shanghai)

## Purpose

Validate that the S40-accepted S39 `concat-h64` artifact produces the same raw
25-logit decisions through the actual local product client/service and the
persistent GPU0 vllm-rwkv lane as through the frozen one-shot test path. This is
a non-executing shadow canary: it does not call Harness tools or the 13.3B
Executor, change `.env.local`, generate RWKV text, or modify any model output.

## Frozen runtime and evidence identity

- S40 test report SHA-256:
  `aa8fe7d3973310d00b34294f8d3d043935fafc2fd0f20d51b15afee9ffcb12a8`
- S40 predictions SHA-256:
  `5e8381d39551880085b9eceb63b8875fb1a4d5a7db1e8b61e936aa117b6bedd0`
- S39 dataset SHA-256:
  `b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab`
- Locked h64 Head file SHA-256:
  `e2c4ffa85bb98637f8ba3dd2caf5789b732f2bb43ebc9b19bc4242e0ff3063dd`
- Locked Head hash:
  `73ecba1dcd84a2b8005d486b71fad210b1aab2f9981e8e04b2b7c90846ade7a7`
- Portable model hash:
  `479f6f1f1ee740003e8cd76036a8b580c1151d7084e83a43018dd73eba8b641a`
- Engine revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`
- 2.9B weights SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- Feature protocol:
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`
- Explicit native `zero` state profile with SHA-256 `00...00`; profile registry
  manifest SHA-256:
  `706ff62cc8ae5851f9c918509911d4ee701f9db5d00bef16f24d2a568e3a0b47`
- Case registry SHA-256:
  `7f2881140d6d092015ed3a79ab430bdc27dac6f77e2d61e6070f2cb0921d505a`
- Frozen source SHA-256 values: V3 renderer
  `2d5668e9a7c4590670bcb9af4ed93df74e97de8bc49d0980db2e0f7479f62a6b`,
  artifact loader
  `f9895ee651d48b0422c54a214545fc37eab085adfb2dbdab806076a1f26a89ad`,
  client
  `99734cda8edf923a9b9fdfde4b3bad2dbc91fbde12b4cf0b7c6c757a2b306d55`,
  service
  `8891b0a610a218a9b22eb77fa5e0c1cd0f1915e1d03997525b6efe9d72d7de4c`,
  persistent extractor
  `bc6a362361f24e16e3f72c8069426b582e96bb251bd1c67804bac4eb5933341d`.

## Fixed coverage

The immutable case registry contains exactly one S39 test/current/English row
for every canonical class in canonical order. Each is the lexicographically
smallest eligible sample ID for its class. Replay every prefix from the same
trajectory in increasing `trajectory_position` order before reaching that
current decision. The frozen counts are exactly 25 current decisions and 37
total Selector calls, with trajectory lengths
`[1,2,1,2,1,1,1,1,1,1,1,3,3,1,2,1,1,1,2,1,2,2,1,3,1]`.

For every prefix:

1. reconstruct the typed Selector input and prove its V3 bootstrap/step are
   byte-identical to the S39 record;
2. send it through `/v3/select` using the production client and immediate
   parent Selector checkpoint;
3. retain request identity, checkpoint chain, full 25 raw logits, raw argmax,
   elapsed time, and wire digest;
4. compare online raw logits and argmax to the content-addressed S40 prediction
   for the exact prefix ID and also compare raw argmax to its exact label.

No replacement case, retry, alternate Head/state, mask, threshold, repair,
fallback, or Executor call is permitted.

## Acceptance gates

The canary passes only if every gate is true:

- the registry selection rule, canonical order, sample IDs, trajectory lengths,
  25 current rows, and 37 total prefix calls are exact;
- all 37 frozen V3 renderings are byte-identical and every wire request obeys
  bootstrap-on-first-call/empty-bootstrap-on-continuation;
- every parent checkpoint is the immediately preceding Selector checkpoint,
  token positions strictly increase, and all checkpoints remain on the 2.9B
  Selector zero-state lane, independent of Executor state;
- every online raw argmax equals both the S40 offline raw argmax and the exact
  expected prefix label;
- every per-row and global maximum absolute raw-logit difference is at most
  0.005;
- every response retains exactly 25 finite raw logits with
  `postprocessed=false` and `generated_text=false`;
- request wire contains no parameters, arguments, full results, Executor text,
  or parameter schemas;
- service health identity exactly matches V3/fusion/Head/model/zero-state
  settings;
- generation, sampling, postprocessing, retries, fallback, Harness execution,
  and 13.3B Executor calls are zero;
- current-decision median latency is at most 3 seconds and p95 is at most 5
  seconds, excluding model startup but including HTTP, state persistence, one
  RWKV forward, h64 inference, and response commit.

The runner must refuse to replace existing S41 output. Failure keeps
`.env.local` inactive. Passing unlocks only the exact pinned Selector identity
for local activation and subsequent full regression; it does not activate an
S31 tuned state.
