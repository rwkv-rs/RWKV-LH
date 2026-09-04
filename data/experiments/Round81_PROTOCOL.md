# Round81 full90 repeat preregistration

## Purpose

Run the current unified RWKV-state architecture on the fixed RWKV-E2E-90 suite after the forwarded model service was restarted. This is an independent repeat of the same source tree used by `Round80_full90_r2`, intended to measure real run-to-run stability rather than introduce another architecture change.

## Frozen architecture and runtime

- Branch: `chase/g1i-tool-protocol`
- Git commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- Dirty worktree is the architecture under test; it must not be changed during the run.
- The 56 entries in `Round80_full90_r2/source_tree_manifest.json` were rehashed before this run: `changed=0`, `missing=0`.
- Local regression before the run: `77 passed in 14.99s` using `uv run pytest -q -s`.
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service `created`: `1786751545`
- SSH forwarding service was active before the run (`NRestarts=1`).

## Frozen dataset and command

- Suite: all fixed 90 cases (`30 basic / 30 medium / 30 hard`).
- Hidden acceptance remains isolated and is used only by the external verifier.
- Codex reference answers remain forbidden from runtime model input and are used only after the run.
- Maximum transitions per case: `200`.
- Case concurrency: `8`.
- Sampling and endpoint configuration are taken from the same checked-in/runtime configuration recorded by the generated `RUN_PROTOCOL.json`.

Exact command:

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round81_full90 \
  --max-transitions 200 \
  --concurrency 8
```

## Frozen comparisons

- Uploaded best checkpoint: Round46, Strict `31/90`, External `32/90`, Agent `55/90`, FP `24`, FN `1`.
- Same-source prior repeat: Round80 full90 r2, Strict `0/90`, External `10/90`, Agent `1/90`, FP `1`, FN `10`.

No score-dependent rule, hidden acceptance access, RWKV output rewrite, semantic retry, or post-run evaluation change is allowed. All model requests, raw outputs, canonical projections, state transitions, action results, validation evidence, final outputs, and external verifier results must be preserved by the benchmark artifacts.
