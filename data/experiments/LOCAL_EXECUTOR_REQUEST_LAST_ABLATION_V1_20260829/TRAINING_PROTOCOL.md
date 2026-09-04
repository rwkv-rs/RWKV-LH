# EXE-G2-V3-RL training protocol

Registered before the first training command on 2026-08-29 (Asia/Shanghai).

## Cause and profile identity

The frozen E1 dev480 run with `EXE-G1-V2-STEP1250` retained 480/480 transport
and 20/20 final facts but produced 17 canonical residuals in four operation
families. Therefore the V2 state is not eligible for the V3 layout. The next
general profile is `EXE-G2-V3-RL`; it is a new zero-initialized state, not a
continuation of G1 and not a per-tool state.

## Frozen inputs

- Dataset: `rwkv_lh_executor_state_tuning_v3_request_last_2k`.
- Train rows: 2000; dev rows: 480; V2 targets and split membership unchanged.
- Training JSONL SHA-256:
  `6a6b0c04b02858c717d833b5a80f61fd957b85210e0d4966dbb9dc8a0014df7f`.
- Dev stage SHA-256:
  `47f4c80adf5f89279ee4e0d4b0792a48118868d3211021ba7ca1141cbdbef8dd`.
- Before training, the authoritative remote RWKV-PEFT tokenizer, BOS=0 causal
  alignment, target-suffix labels, no truncation, and exact prompt+target boundary
  must all validate with zero failures.

## Frozen training configuration

- Base: 13.3B G1i SHA-256
  `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`.
- Initialization: native zero; no `state_init`, G1, Stage8, or other continuation.
- Physical GPU0 only; `CUDA_VISIBLE_DEVICES=0`.
- `peft=state`, `op=fla`, BF16, DeepSpeed stage 1, gradient checkpointing.
- `ctx_len=2496`, micro batch 1, accumulation 1, target-suffix loss, BOS 0.
- 2000 steps, one epoch, shuffle enabled, seed 829.
- Save every 250 steps.
- Cosine LR: `2e-5` to `2e-6`, warmup 50; beta1 0.9, beta2 0.99,
  Adam epsilon `1e-8`.

All eight checkpoints are retained and evaluated on the same complete dev480.
Selection is the earliest checkpoint at the start of a full-score plateau; it
must then repeat byte-identically three times. Metrics and thresholds are those
in `PROTOCOL.md`; no output repair, constrained decoding, hidden retries, or
post-result metric changes are allowed.
