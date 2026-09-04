# NET-SEL-2P9-S12-GATE state-tuning preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Trigger and scope

S11 is rejected as a deployment candidate but isolates one residual: its Tool
head reaches public-web 25/25 and structured-connector 18/20 with no required
online miss, while the Gate wrongly takes over 3 local, 3 deterministic and 6
mixed-local-first ECRA rows. Privacy takeovers are zero. S12 therefore trains
one 2.9B Gate-specific initial state; it does not train an Executor state,
change the Tool head, change a threshold, add keyword rules or alter RWKV text.

Profile number and ID are immutable:
`NET-SEL-2P9-S12-GATE` / `selector-gate-s12-v1`. It starts from zero, not the
rejected S1 or S2 state. `NET-EXE-13P3-N0` remains unchanged.

## Frozen state data

Source is S11 SHA-256
`553208ddf01e9baa6542fbd95ed653a0615111263a0573be4c388a4ca86f0c17`.
Only S11 train/dev rows whose complete serving token sequence (BOS included)
is at most 384 tokens are exported. This excludes 39 train and 14 dev `DEFER`
rows that the S11 feature extractor left-truncates; training a different full
sequence would violate serving parity. No network row is excluded.

- train: 1,467 rows (NETWORK 680, DEFER 787);
- dev: 275 rows (NETWORK 110, DEFER 165);
- S11 test 205 and all ECRA/E2E rows are excluded;
- prompt is byte-exact S11 `rendered_input`;
- target is exactly `\nGateLabelV1: NETWORK` or
  `\nGateLabelV1: DEFER`;
- loss is target suffix only, BOS=0, generated RWKV text count zero.

The S11 fixed UTF-8 byte-5gram contamination result is inherited unchanged:
maximum 0.4595745763, exclusive threshold 0.75.

## Fixed remote training

- base model: `rwkv7-g1i-2.9b-20260805-ctx16384.pth`, SHA-256
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`;
- train only 32 `blocks.<layer>.att.time_state` tensors from zero;
- `--peft state --op fla`, BF16, micro batch 1, accumulation 1,
  DeepSpeed stage 1, gradient checkpointing, shuffle, seed 843;
- ctx 512, 1,467 steps, one epoch, checkpoint every 489 steps;
- LR 2e-5 to 4e-6 cosine, warmup 30;
- final step 1,467 is selected unless incomplete or non-finite.

The remote tokenizer must prove prompt/target token concatenation, target
suffix integrity, maximum sequence <=513 including BOS, zero historical
assistant supervision and exact label counts before training.

## Fixed ablation and gates

S12 must be converted to the registered vLLM identity layout without tensor
transposition. Corrected tuned-state injection must change hidden features.
Using the same S11 dataset, MLP topology, seed, optimizer, split, raw argmax and
candidate selection, compare:

1. S11 zero profile (recorded baseline);
2. one S12 profile forward feeding both Gate and Tool heads.

The single-profile candidate is accepted only if all S11 internal gates and
the complete S11 ECRA regression gates pass, including zero takeovers in all
75 local/deterministic/mixed/privacy rows, web >=23/25, connector >=18/20 and
web/connector macro-F1 >=0.90. It must causally change at least 8 of the 12
registered false takeovers to DEFER, introduce zero new false takeovers and
regress at most one required-online case.

If S12 improves Gate but harms Tool, it is rejected as the one-forward
candidate. A later separately preregistered two-forward split may use S12 only
for Gate and zero state for Tool. Passing S12 does not itself authorize runtime
integration; raw-output integrity, profile isolation, live retrieval and the
complete historical Harness regression remain mandatory.

