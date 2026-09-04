# S71 2.9B Selector state-tuning protocol

Date: 2026-08-31 (Asia/Shanghai)

Frozen after zero-state dev rejection and before remote training.

## Trigger and data isolation

- Zero-head result SHA-256:
  `8d2695a53f8d53e785a9f3d0077fab7f232828d64c22fe2b6b3c25e3de422e62`.
- Train state rows SHA-256:
  `36c3faa290ab284734bb6c1bc7034431f683da3c147fd52fc63eb60c3241993f`.
- Dev state rows SHA-256:
  `cdb72d7959cd6a569730cd0359a37b6119b03b64e056ed4f47589f9435bc4317`.
- Dataset manifest SHA-256:
  `b01c739babbc6cfd3eb8a92b7dd6250504110df2e42f270ebdba7a7091bd82ca`.

Only the 2,000 S71 train rows supply gradients. The 500 visible dev rows are
uploaded only for loss-mask/tokenizer contract validation and later feature
evaluation; they never supply gradients. The 500 newly sealed S71 test rows
are absent from state exports and must remain skipped before JSON parsing.

## Fixed training run

- Remote host `rwkv-8222`, physical GPU0 UUID
  `GPU-1faf7f09-25f4-2515-b707-6e0766aa841d`; preserve healthy product port
  18070, require experimental port 18075 to remain unused, and require at
  least 55,000 MiB free before launch.
- Base model is the unchanged 2.9B checkpoint with SHA-256
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`.
- Initial trainable state is exact zero; no parent state and no weight update.
- Frozen RWKV-PEFT configuration: `--peft state --op fla`, 32 layers, width
  2560, ctx 2496, target-suffix loss, JSONL BOS 0, bf16,
  deepspeed-stage-1, seed 1067, 2,000 steps, cosine LR `2e-5 -> 4e-6`, 40
  warmup steps, microbatch 1, checkpoint every 500 steps.
- Before launch, revalidate exact target suffix, BOS alignment, token limit,
  train/dev counts, all audited trainer-source hashes, base identity, GPU
  identity/free-memory floor, absence of concurrent trainer, and product
  health.

Collect and validate all four numbered states `S71-ST500/1000/1500/2000`.
Each state must have 32 finite nonzero tensors and 5,242,880 elements after the
frozen identity conversion to the vllm-rwkv profile format. Base weights,
remote raw checkpoints, raw loss rows, and trainer logs remain preserved.

## Fixed comparison

For each numbered state, extract S71 train/dev features with the same
one-forward three-view protocol and train the same `DualViewGatedH128`.
Compare all four on the unchanged dev gate (`0.96 / 0.96 / 0.90`) and choose
the passing state with the smallest step; if none pass, reject S71 state
tuning. S71 locked test stays unparsed until exactly one candidate is frozen.

Do not alter, hide, reorder, truncate, postprocess, repair, replace, or delete
RWKV states, hidden features, raw logits, raw trainer logs, or checkpoints. Do
not modify, suppress, or replace RWKV output. Do not use GPU1/2.

