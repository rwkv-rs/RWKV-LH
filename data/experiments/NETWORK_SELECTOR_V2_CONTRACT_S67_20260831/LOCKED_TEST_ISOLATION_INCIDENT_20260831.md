# S67 locked-test isolation incident

## Incident

After the ST500 and ST1000 registered dev screens had completed, a read-only interactive tokenizer-boundary check loaded every line of `cases.jsonl` with `json.loads` in order to compare one-piece and split token ID sequences. That loop included the 500 rows whose `split` is `test`. It printed only aggregate token-boundary equality (`3000/3000`) and three train-row mismatch examples for a rejected boundary; it did not print test prompts, labels, predictions, logits, or metrics and did not write a derived test artifact. Nevertheless, the strict contract is parsing isolation, so test JSON and its label fields existed in process memory and the isolation claim is breached.

## Scope

- The authoritative zero-state and numbered-state feature extractors skipped test rows before JSON parsing. Their train/dev features and ST500/ST1000 results were produced before or independently of this interactive check.
- No S67 test feature, classifier prediction, score, aggregate metric, threshold decision, or product decision was computed.
- The check exposed only structural tokenizer-boundary equality across all rows, but that is still disallowed access under the registered locked-test policy.

## Fail-closed disposition

- The 500 S67 test rows are permanently disqualified as a locked release evaluation for every current or future S67 candidate. They must not be used to claim a locked-test pass.
- Existing S67 train/dev results remain valid as development evidence. Any report must state that S67 locked-test was retired, not passed.
- If a unique dev candidate is frozen, a new independently generated and separately versioned S68 locked-test must be registered by source/hash before its labels or model outputs are read. It must use disjoint lexical material and must not reuse this tokenizer precheck.
- No threshold, dev result, feature, raw RWKV output, or existing S67 row is deleted or altered. This incident record is additive and auditable.
