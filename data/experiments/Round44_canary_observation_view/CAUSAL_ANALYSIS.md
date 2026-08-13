# Round44 Canary Causal Analysis

## Frozen result

- Fixed cases: `B04`, `B27`, `B29`, `B05`, `B06`, `B08`, `B11`, `B12`, `B13`, `B18` (runner emitted catalog order).
- Strict E2E: `4/10`.
- External acceptance: `6/10`.
- Agent completed: `4/10`.
- False positives: `0`.
- False negatives: `B06`, `B29`.
- Strict passes: `B08`, `B11`, `B13`, `B18`.
- Both agent and external failed: `B04`, `B05`, `B12`, `B27`.

The preregistered canary gate required at most one FP and at least six of seven Round41 correct controls to remain Strict. Only four of seven controls were Strict, so no Basic30 run is permitted and the implementation must be reverted.

## Per-case chain attribution

### B04

The workspace remained wrong and the run blocked. Round44 did not reproduce the Round41 false completion, but this alone cannot establish selectivity.

### B05

The producer used `replace_text(old="deprecated=true", new="")`. It removed the substring but left a blank line, so external exact-content verification correctly failed. Later verification-only Tasks repeatedly treated a successful full `read_file` as “only a read, not verification”, selected `read_json` for a plain-text file, and exhausted recovery. The first failure is producer action semantics; the repeated amplification is the verification-Task/action mismatch.

### B06

The workspace was exactly correct. A verification-only Task read the complete correct file, but RWKV repeatedly said that `read_file` “only provided the contents without performing the newline check”. Recovery generated another identical verification Task and reached the same rejection. The first false-negative decision occurs at Task postcondition adjudication, before Goal evidence. Round44's larger JSON observation surface did not teach the model that it is itself the semantic verifier.

### B08, B11, B13, B18

Production, Task adjudication, Goal adjudication, and external acceptance all passed. These prove the observation projection is executable but not sufficiently stable/selective.

### B12

RWKV read the values `4, 9, -2, 9, 5` and wrote sum `21` instead of `25`. The workspace was wrong. Subsequent compute/verify Tasks and replans amplified the original arithmetic error but did not falsely complete. This is a model production/reasoning error, not a wire-format failure.

### B27

The workspace remained wrong and the run blocked. This removed the prior false completion in this sample, but the run did not produce a correct artifact.

### B29

The workspace was fully correct: copied hashes matched and manifest content matched exactly. RWKV then read the exact manifest line and incorrectly claimed that it was not the expected manifest line. Recovery action generation copied observation-view metadata (`source_complete`, `view_truncated`, `observation_metadata`, `observed_artifacts`) into a `read_file` call, causing protocol correction/failure rather than progress. The first error is Task semantic adjudication; the observation view then enlarged the error surface at the action boundary.

## Cross-case conclusion

The proposed shared JSON observation view mixed two distinct responsibilities and made the weak-model action prompt less compact. Although it exposed persisted bytes without Controller judgment, its extra schema and metadata were copied into later action calls, while it did not solve RWKV's confusion over verification-only Tasks. It therefore fails the project requirement that the chain become tighter.

The stronger root cause across `B05`, `B06`, `B21`, `B25`, `B26`, and `B29` is the architecture's creation and recovery of Tasks whose sole semantic operation is “verify”. A Harness read/list/test action supplies the evidence; RWKV is supposed to perform the comparison in Task postcondition adjudication. The current model often instead demands that the observation action itself issue a verdict, creating an impossible repeated Task.

Next work should not add another verifier call, semantic rule engine, or broader format adapter. It should tighten the existing Task contract so that:

1. planning does not create redundant verification-only Tasks when the producing Task's postcondition and existing Task adjudication can cover the effect;
2. when an explicit observation Task is necessary, the postcondition prompt states compactly that RWKV is the verifier and must decide directly from the returned evidence, not demand another verification action;
3. recovery does not recreate the same observation-only Task after the same complete evidence;
4. the wire-format converter remains limited to common registered call shapes and never consumes observation-view fields.

Round44 code was reverted and is not eligible for upload.
