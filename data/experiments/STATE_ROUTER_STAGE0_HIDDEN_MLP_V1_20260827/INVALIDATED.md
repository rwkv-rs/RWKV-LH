# Invalidated formal run

This first 2k run is retained as diagnostic evidence and is excluded from A/B/C selection.

- Root cause: PyTorch reported that deterministic algorithms were requested, but CUDA cuBLAS
  backward was not deterministic because `CUBLAS_WORKSPACE_CONFIG` was absent before CUDA work.
- Scope check: the same local backend is shared by A/B/C, so the correction was applied at that
  common boundary rather than to one runner.
- Correction: set the documented CUDA deterministic workspace `:4096:8` before Torch import or
  the first CUDA operation.
- Frozen evaluation labels, split, metrics, thresholds, seed, architecture and training
  hyperparameters were not changed. No observed test value from this run is used for tuning.
- Replacement output: `data/experiments/STATE_ROUTER_STAGE0_HIDDEN_MLP_V1_R2_20260827/`.

