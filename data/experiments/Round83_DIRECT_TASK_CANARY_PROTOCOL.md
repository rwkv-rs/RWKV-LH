# Round83 direct Task-call canary preregistration

## Purpose

Validate the removal of the two-generation `lh_select_operation` handshake and
the restored semantics-free envelope normalizer against fixed cases selected
before execution from the Round81 causal census.

## Frozen cases

- `E2E-B01`: externally correct in Round81, then emitted direct `lh_task_done`;
- `E2E-B02`: emitted a valid direct `read_file` while selector was required;
- `E2E-B03`: externally correct in Round81, then used `function+arguments`;
- `E2E-H04`: externally correct in Round81, then emitted direct `lh_task_done`.

These cases are diagnostic, not a replacement score for the fixed E2E-90 suite.
Hidden acceptance and Codex reference answers remain unavailable to RWKV and are
used only by the unchanged isolated verifier after execution.

## Frozen implementation and runtime

- Branch: `chase/g1i-tool-protocol`
- Base commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- `rwkv_lh/model.py`: `bc77a5149f98f3415a88d5942f58c2a23fcb8031f975418138f27031d98a41d0`
- `rwkv_lh/model_io.py`: `ef9e773541fdbb823177dd8c6ba326ac170b849bbe04c5b7e6cd62e999eb3b5b`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- Complete local regression: `79 passed in 10.91s`
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service created: `1786754702`
- Concurrency: `1`
- Maximum transitions: `200`
- Sampling: current fixed lane sampling (`temperature=0.05`, no semantic resample)

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 \
  --case E2E-B02 \
  --case E2E-B03 \
  --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round83_direct_task_canary \
  --max-transitions 200 \
  --concurrency 1
```

No result-dependent parser, prompt, schema, verifier, retry, or score change is
allowed after this run starts. Success is assessed through Strict, External,
Agent completion, FP/FN, raw call acceptance, semantic request counts, and the
first remaining causal failure—not by rewriting RWKV output.
