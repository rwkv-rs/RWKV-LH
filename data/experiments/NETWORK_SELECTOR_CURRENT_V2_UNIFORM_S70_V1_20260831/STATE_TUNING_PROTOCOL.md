# S70 2.9B Selector state-tuning protocol

Date: 2026-08-31 (Asia/Shanghai)

Frozen after zero-state dev rejection and before remote training.

## Trigger and data isolation

- Zero-head result SHA-256:
  `77b80c919d3ff13d515207451f3a82fee085bd8bfe7e54c2afc4542dd5ad8e5a`.
- Train state rows SHA-256:
  `90b117f82e42bfdfb16eed8030d2d77dab6f5f570a523f99a0e57377a71d721f`.
- Dev state rows SHA-256:
  `feb3b1b6c26f580e64e823eb9d3e93903cb8eca94f9133a67a42b7ca0f4cf868`.
- Dataset manifest SHA-256:
  `34584d0c755f40e4c8cc286d907eca8d840f5f9bc84614d1d2dcac019aac5f21`.

Only the 2,000 train rows supply gradients.  The 500 dev rows are uploaded only
for loss-mask and tokenizer contract validation and later feature evaluation;
the 500 locked-test rows are absent from state exports and must remain unopened.

## Fixed training run

- Remote host `rwkv-8222`, physical GPU0 UUID
  `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`; preserve healthy product port
  18070 and require experimental port 18075 to remain unused.
- Base model is the unchanged 2.9B checkpoint with SHA-256
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`.
- Initial trainable state is exact zero; no parent state and no weight update.
- Frozen RWKV-PEFT configuration: `--peft state --op fla`, 32 layers, width
  2560, ctx 2496, target-suffix loss, JSONL BOS 0, bf16,
  deepspeed-stage-1, seed 1067, 2,000 steps, cosine LR `2e-5 -> 4e-6`, 40
  warmup steps, microbatch 1, checkpoint every 500 steps.
- Before launch, revalidate exact target suffix, BOS alignment, token limit,
  train/dev counts, all audited trainer-source hashes, base identity, GPU
  identity/free-memory floor, absence of concurrent trainer, and product health.

Collect and validate all four numbered states `S70-ST500/1000/1500/2000`.
Each state must have 32 finite nonzero tensors and 5,242,880 elements after the
frozen conversion to the vllm-rwkv profile format.  Base weights and remote raw
checkpoints remain preserved.

## Fixed comparison

For each numbered state, extract S70 train/dev features with the same one-forward
three-view protocol and train the same `DualViewGatedH128`.  Compare all four on
the unchanged dev gate (`0.96 / 0.96 / 0.90`) and choose the passing state with
the smallest step; if none pass, reject S70 state tuning.  S70 locked test stays
unparsed until exactly one candidate is frozen.

Do not alter, hide, reorder, truncate, postprocess, repair, replace, or delete
RWKV states, hidden features, raw logits, raw trainer logs, or checkpoints.
