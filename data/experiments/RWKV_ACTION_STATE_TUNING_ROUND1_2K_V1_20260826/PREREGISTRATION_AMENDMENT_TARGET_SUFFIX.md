# Preregistration amendment: exact target-suffix loss

This amendment is made before training or tuned-model evaluation. The authoritative
remote QA-mask audit found that all 2,200 rows would supervise every historical
`Assistant:` span in addition to the selected next-transition target:

- selected target tokens: 53,342;
- additional historical Assistant tokens: 32,928;
- affected rows: 2,200/2,200.

That objective conflicts with the preregistered purpose: tune the state at the
selected historical failure boundary, not repeat generic trajectory SFT. Training is
therefore changed from `loss_mask=qa` to `loss_mask=target_suffix`.

Frozen contract:

1. The training row must contain exact `prompt`, `target`, and `text=prompt+target`.
2. Exact RWKV tokenization must be additive at the prompt/target boundary.
3. The complete text must fit `ctx_len+1=2497`; truncation fails closed.
4. Labels before the target token boundary are `-100`.
5. Every and only target token is supervised.
6. The server RWKV-PEFT `dataset.py` digest and its recoverable backup are recorded.

No dataset count, cluster weight, context limit, holdout threshold, evaluation metric,
or checkpoint selection rule is changed.
