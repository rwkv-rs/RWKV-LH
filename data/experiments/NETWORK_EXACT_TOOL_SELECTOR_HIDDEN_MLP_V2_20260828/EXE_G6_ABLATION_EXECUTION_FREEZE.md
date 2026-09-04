# EXE-G6 ablation execution freeze

Frozen on 2026-08-29 (Asia/Shanghai), before training completion and before any
G6 checkpoint output was evaluated.

The parent G4 step2000 and all eight G6 checkpoints are evaluated on both fixed
480-row dev sets. Each row is sent exactly once and its first response envelope,
raw text, token IDs, model identity, and request metadata are appended and
fsynced before parsing. Sampling is temperature 0.1, top-p 1, top-k 0, seed
1067, max output 256. Concurrency is fixed at 8 for every arm; it changes only
batching throughput and is not an evaluation metric or selection feature.

The selection rule remains the preregistered earliest checkpoint passing every
quality, retention, recovery, per-operation, integrity, and positive-rescue
gate. Every checkpoint is evaluated even after an eligible one is found.

- ablation runner SHA-256:
  `9d6cad204faad0e182e8b307b19070d443275c09bdbe24147c64c2a72a8fb5ad`
- raw-first temperature-0.1 evaluator SHA-256:
  `f482e1503d2acaeb1a7bb1e71517b1da10f31b01b505de75242c8e979b6be048`
- G4 launcher SHA-256:
  `3f441a6e14124f9777696230ad017fed7ed151d1630bc5caea42044cc5217296`
- G6 launcher SHA-256:
  `3d6f0841959e4929e178c3cf42ecabb66ea38558f6919d4785999e3c3d13c69a`
- G4 eval SHA-256:
  `f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d`
- G6 eval SHA-256:
  `f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee`

Both launchers are verified locally and remotely before the output directory is
created. Every service must attest physical GPU0 and the exact state digest;
the existing port-18070 product service must stay healthy.
