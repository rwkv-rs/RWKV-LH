# Round48 Canary Causal Analysis

## Frozen outcome and gate

The fixed canary produced Strict `6/10`, external acceptance `8/10`, and agent
completion `8/10`.

- Strict: `B06`, `B11`, `B12`, `B18`, `B21`, `B25`.
- False negatives: `B08`, `B26`.
- False positives: `B27`, `B29`.

The preregistered gate required `B12` Strict, zero FP among `B12/B29`, `B27`
correctly blocked, and a B12 noop-lineage capsule that exposed the recorded
ancestor observation. The run failed all relevant attribution requirements
except B12's aggregate Strict status. Basic30 must not run and Round48 is not
upload-eligible.

## The candidate was not exercised by the real canary

No failed canary Task had a noop dependency. More importantly, this B12 sample
did not reproduce Round47's noop-interrupted chain. It produced:

`read_file -> write_json(correct) -> write_json(correct) -> read_json -> noop`

T4 directly depended on the non-noop T3 write and selected only T3's unchanged
output projection. The candidate's recursive noop branch did not run. B12's
Strict PASS therefore cannot be attributed to Round48.

Offline tests prove the candidate's mechanical property, but this single real
canary supplied no causal evidence that it improves the model distribution.

## Failure-by-failure analysis

### B08 — false negative after externally correct production

T2 and T3 both wrote the correct SHA256 manifest; external acceptance passed.
The verification Task T4 read `payload.txt`, then correctly stated that this
observation alone did not establish digest equality and chose `replan`.
Failure analysis requested action reselection, but RWKV twice emitted an invalid
`read_file` argument `end_char`. The protocol rejected those raw action calls
and blocked. No noop lineage was present. The first fault after correct
production was tool/action selection during recovery, not memory propagation.

### B26 — false negative after externally correct production

T2/T3/T4 created all three exact files and external acceptance passed. The
verification Task T5 selected `write_file(output/a.txt)` instead of a read/list
observation. Its Task commit correctly noticed that one file observation could
not establish the whole file set and replanned. RWKV then selected the same
write two more times and exhausted recovery. No noop lineage was present. The
failure is a verify-versus-mutate action-mode error amplified by repeated
reselection.

### B27 — false positive from stale value reconstruction

The first replacement changed only one occurrence. T3 correctly read the file,
detected remaining `protocol=v1`, and replanned. It then replaced one more
occurrence and incorrectly committed that none remained. T4's earlier read
represented the partially changed file. T5 reconstructed the final file by
writing that stale partial content, reintroducing remaining v1 occurrences.
Goal decisions accepted the stale evidence. No noop lineage was present.

### B29 — false positive from partial copy and wrong verification action

T2 used `write_file` with only `line two` instead of `copy_file` or the complete
observed source. T4, whose purpose was verification, wrote the manifest again
instead of comparing source and backup. Task and Goal commitments ignored the
different recorded SHA256 digests. This is the known tool/value-transfer and
semantic comparison error. No noop lineage was present.

## Conclusion

Round48 is an unexercised candidate under this real sample, not a demonstrated
improvement. Its code must be reverted under the preregistered gate.

The four failures reveal a broader protocol defect that should be evaluated
next: natural-language “verify” Tasks repeatedly select mutating producer tools,
while recovery resamples the same incompatible action. A future candidate may
let RWKV declare an explicit Task operation mode at the planning boundary and
use that model-owned declaration for progressive tool disclosure. Such a
protocol must preserve RWKV's declared mode, permit an auditable model-owned
mode revision during recovery, and never infer mode from benchmark text or
change a semantic answer. It should first be tested on fixed causal-state
replays so plan-sampling variation cannot hide whether the intended path was
actually exercised.
