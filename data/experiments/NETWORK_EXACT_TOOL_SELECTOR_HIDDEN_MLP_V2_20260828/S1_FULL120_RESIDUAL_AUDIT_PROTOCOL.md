# Selector S1 / ECRA120 residual audit protocol

Date: 2026-08-28 (Asia/Shanghai)

## Purpose

The preregistered 45-case external gate rejected S1 because
`connector_lookup` recall was 1/20.  Before constructing any residual training
data, audit the same frozen S1 head on every related ECRA route category.  This
is a post-rejection residual diagnostic; it does not change the 45-case gate or
make S1 deployable.

## Frozen inputs

- Dataset: `data/datasets/rwkv_lh_ecra_route_v1/cases.json`
- Dataset SHA-256:
  `7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a`
- Cases: all 120, in source order.
- Selector input projection:
  `task=instruction; stage=instruction; role=work; zero progress; v2 menu`.
- Model, state profile, feature protocol, heads, class order and raw-argmax
  policy are exactly those recorded by `run_s1/TRAINING_SUMMARY.json`.
- Batch size is 1.  RWKV generation and sampling counts must both remain zero.

## Fixed diagnostics

- first-tool exact accuracy overall and for all six ECRA categories;
- 25x25 expected/predicted confusion counts;
- local-only network false-positive rate;
- required-online false-negative rate;
- web/connector macro-F1 and per-class precision/recall/F1;
- prediction counts for each failed category.

No thresholds are added after seeing this run.  The audit only determines the
global residual surface and the positive:hard-negative balance of a future,
separately preregistered dataset.  Exact ECRA instructions, entities and URLs
remain excluded from training.

## Command and output

```bash
uv run --no-sync --project /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50 \
  --python /home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python \
  /home/chase/GitHub/RWKV-LH/temp/audit_network_selector_s1_full120_20260828.py
```

Output:
`run_s1/S1_FULL120_RESIDUAL_AUDIT.json`.
