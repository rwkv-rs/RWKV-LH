# S67 request-tail pooling ablation preregistration

## Timing and question

This diagnostic is frozen after the registered ST500 and ST1000 screens were rejected and before any ST1500/ST2000 metric or request-tail feature was read. Static inspection showed that the semantic `complete_requirement` is correctly placed at the byte tail, while the registered `mean` view averages the whole contract step and the `last` view ends on JSON closing bytes. The fixed question is whether pooling only the already-tail-positioned request allows the same h128 Hidden+MLP architecture to expose the operation distinction. The structural tokenizer precheck parsed S67 test rows and is disclosed in `LOCKED_TEST_ISOLATION_INCIDENT_20260831.md`; those rows are retired from locked evaluation and cannot contribute to this diagnostic or a release claim.

## Frozen data and states

- S67 cases SHA-256 `0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859`; manifest SHA-256 `0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46`.
- Train 2000 and dev 500 are used. The ablation runner skips the retired S67 test 500 before JSON parsing and computes no test feature, prediction, or metric. It does not assert that S67 test was never previously parsed.
- Evaluate zero state and every numbered S67 state for which the registered screen sequence has produced a manifest. State order and product selection are unaffected.

## Byte/token-preserving split and feature

- The current step must contain the exact marker `,"complete_requirement":"` once. Let the split point be immediately after this marker.
- Feed `"\n" + step[:split]` followed by `step[split:]` as two continuations of the same persistent RWKV state. Their byte concatenation must equal the original `"\n" + step` exactly.
- The disclosed pre-registration precheck found 3000/3000 exact token IDs using the frozen tokenizer but invalidated S67 test isolation while doing so. The runner independently repeats the equality check only on the included 2500 train/dev rows and rejects otherwise; it does not parse the retired test rows.
- The feature is float32 `concat(request_tail_mean_hidden, request_tail_last_hidden)`, where both views come only from the second continuation. The prefix still updates the authoritative recurrent state; no token or hidden value is dropped from state propagation.
- For every included row, the new request-tail `last` vector must match the already frozen one-piece `last` vector at maximum absolute difference `<=1e-5`. This is the causal parity gate that the split changed pooling only, not tokenization or recurrent state.

## Fixed head and evaluation

- Head: Linear(5120,128), GELU-tanh, LayerNorm, dropout 0.05, Linear(128,25).
- Train-only mean/std; seed 1067; AdamW `1e-3`; weight decay `1e-4`; batch 256; cosine schedule; at most 160 epochs; patience 30; gradient norm 1.0.
- Selected epoch and metrics use the exact registered screen procedure. Gates remain dev accuracy `>=0.96`, supported macro-F1 `>=0.96`, and minimum supported-label recall `>=0.90`.
- Raw tail mean/last feature shards and selected raw head logits are preserved. There is no generated RWKV text, sampling, rule mask, family route, threshold route, argmax repair, or logit postprocessing.

## Boundary

This is a diagnostic pooling ablation, not a release candidate. A pass must still receive a one-engine-call implementation with numerical parity, retention/full-dev gates, artifact/service parity, a newly registered independent S68 locked-test, and real Harness canary before product use. The retired S67 test can never satisfy that gate. A failure leaves the state/prompt/data objective as the remaining bottleneck; gates are not changed.
