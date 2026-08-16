# Round114 uv Python coding smoke preregistration

- Date: 2026-08-15
- Purpose: verify that the current RWKV-driven Agent can read code/tests, modify an
  implementation in an isolated workspace, and execute the resulting Python tests
  through the project uv environment after the read-only runtime mount fix.
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Fixed cases: `E2E-B10`, `E2E-B30`
- Suite: frozen `all` E2E-90 catalog; only the two registered case IDs are run.
- Parameters: `max_transitions=200`, `concurrency=1`; repository/runtime code is
  frozen at process start and is not changed after seeing case results.
- Metrics: Strict result, external hidden acceptance, Agent terminal status,
  non-empty raw-matching Final, attempt/action sequence, and earliest divergence.
- Interpretation: one passing case proves the mechanism can complete that concrete
  small coding task; it does not imply that all simple coding tasks are reliable.

## Dataset files

| File | SHA256 | Role |
|---|---|---|
| `benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json` | `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c` | B10 model-visible task and workspace fixture |
| `benchmarks/rwkv_e2e/rwkv_e2e_30/acceptance.json` | `c4953c556a9ba2e080493f34bb2261db349080542376c4e94f08d5227e0f74cd` | B10 hidden acceptance |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json` | `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b` | B30 model-visible task and workspace fixture |
| `benchmarks/rwkv_e2e/rwkv_e2e_extension48/acceptance.json` | `395e1651f52259de7e56a63476504891f136edd2d4dd5a8263064077741ede12` | B30 hidden acceptance |

Generation command:

```bash
uv run rwkv-lh-e2e --suite all --case E2E-B10 --case E2E-B30 \
  --max-transitions 200 --concurrency 1 \
  --output data/experiments/Round114_uv_python_coding_smoke
```
