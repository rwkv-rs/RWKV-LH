# Invalidated run

This A run is retained as diagnostic evidence but is excluded from every ablation and
selection result. The local vllm-rwkv feature extraction completed successfully, but
the RWKV-LH Torch 2.8 MLP backward warned that deterministic algorithms had been
requested before `CUBLAS_WORKSPACE_CONFIG` was set.

R2 restores `CUBLAS_WORKSPACE_CONFIG=:4096:8` in the shared local backend before any
Torch import/CUDA operation and writes to a separate output directory. Dataset,
features, labels, split, architecture, seed, optimizer, calibration, thresholds and
metrics are unchanged. No R1 test value was used to choose or tune the correction.
