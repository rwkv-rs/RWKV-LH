# Token/context rejection before decision-state projection fix

- Exact tokenizer: RWKV-PEFT `rwkv_tokenizer.py` with `rwkv_vocab_v20230424.txt`.
- Fixed gate: `ctx_len=2496`, request capacity 2497 tokens.
- Rows checked: 2,000 train + 200 dev.
- Rejected rows: 1,652/2,200 because the supervised target would be truncated.
- Overall token range: 988–9,198; mean 3,360.33; median 3,232.5.
- Protocol-correction rows passed; every completion, coverage, and privacy row overflowed.
- Coverage was worst: 4,258–9,198 tokens.

Root cause: progressive rollover represented the same committed action observation in
both `recent_exact_action_records` and retained `action_result` events. The exact action
record also copied duplicate artifacts/evidence and non-decision metadata from the full
append-only result. Increasing the training context would preserve this runtime defect,
so the dataset remains rejected and `training_ready=false`.

Corrective invariant: one bounded `action-result-decision-state.v1` projection per
committed action; full ActionRecord/evidence remains authoritative in the store. A
projected output prefix must explicitly be incomplete.
