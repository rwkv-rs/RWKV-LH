# Round115 uv Python coding smoke preregistration

- Date: 2026-08-15
- Change from Round114: the benchmark harness now forwards the base sandbox's
  `include_project_venv` parameter. No task prompt, workspace fixture, acceptance,
  sampling policy, or model endpoint is changed.
- Environment: `/home/chase/.local/bin/uv 0.12.5`; `uv sync --frozen --dev` reports
  the locked 11 packages checked.
- Fixed cases: `E2E-B10`, `E2E-B30` from the frozen E2E-90 catalog.
- Parameters: `max_transitions=200`, `concurrency=1`.
- Primary checks: a model-selected Python command reaches bubblewrap; current uv
  `pytest` imports successfully; actual test output returns to RWKV; workspace code
  and hidden acceptance remain independent of controller decisions.
- Score reporting: Strict, Agent status, external hidden acceptance, non-empty raw
  Final, and manual earliest-divergence analysis.

Dataset SHA256 values are unchanged from
`Round114_uv_python_coding_smoke_PREREGISTRATION.md`.

```bash
uv run rwkv-lh-e2e --suite all --case E2E-B10 --case E2E-B30 \
  --max-transitions 200 --concurrency 1 \
  --output data/experiments/Round115_uv_python_coding_smoke
```
