# Round12 engine-refresh control pre-registration

Pre-registered: 2026-08-12, before any E2E-90 request on the updated inference engine.

## Purpose and classification

The user updated and re-forwarded the inference engine after the frozen Round12 formal run. This
control reruns the **unchanged Round12 architecture** on that updated engine before any Round13 code
change. It isolates engine/serving effects from the next architecture variable.

Output directory: `data/experiments/Round12_engine_control_20260812/`.

This is not a new architecture Round, is not eligible to become a GitHub architecture checkpoint,
and must not be described as a Round13 improvement. Its only scored comparison is against frozen
Round12 under the old engine. Round13 may be attributed to architecture only after it is run against
this control on the same updated engine and fixed serving configuration.

## Frozen architecture equivalence

The following current files match the frozen Round12 source manifest byte-for-byte:

| File | SHA-256 |
| --- | --- |
| `rwkv_lh/controller.py` | `5cd25f669ea82eca75bedaea1d98f9e0e2d68328b187a69182bc423845e838e5` |
| `rwkv_lh/harness.py` | `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8` |
| `rwkv_lh/memory.py` | `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797` |
| `rwkv_lh/model.py` | `db71a604231fac29b5023b40f0855d849b6f34da9eeaded48b6546481b45dbc1` |
| `rwkv_lh/proof.py` | `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd` |
| `rwkv_lh/schema.py` | `d2a5ff9addf036b6cb0e64c60dbf71d7f2fd19130820052c20fbbe9feec19b43` |
| `rwkv_lh/store.py` | `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05` |
| `rwkv_lh/tool_protocol.py` | `921737961e26676bce38f1fc43c7ace2e1030778c834c2b29b4c2d144be5e105` |
| `rwkv_lh/witness.py` | `a5293cbaa39f1471765e828eaa3afa762393ccce7c84be4634e1faef0f4a2a14` |
| `scripts/run_rwkv_e2e_benchmark.py` | `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8` |

The frozen 54-file Round12 manifest check has exactly one mismatch: `pyproject.toml`, where the
local manual-UI command and static assets were registered after Round12. The web UI is not imported
by the benchmark worker, Controller, Model, Harness, proof or witness path. New UI files/tests are
additive and are recorded in the control run's new source manifest.

## Fixed data and generation configuration

- Dataset: RWKV-E2E-90 v1; Basic, Medium and Hard each contain 30 cases.
- Visible tasks, hidden acceptance and post-run Codex-reference hashes remain identical to Round12.
- Model ID: `rwkv7-g1i-13.3b-20260805-ctx16384`.
- Backend profile: `vllm-rwkv-rapid`.
- Sampling policy: exactly the frozen Round12 `TemperaturePolicy`, top-p `1.0`, top-k `0`, presence
  and frequency penalty `0.0`, penalty decay `0.996`.
- Concurrency: `8`; maximum transitions per case: `200`.
- Endpoint: `http://127.0.0.1:29613/v1`, using the user's updated forwarded inference engine.
- The engine exposes the configured model through `/models` but `/capabilities` returns 404, so the
  runtime remains prompt-replay only and must not infer recurrent-state support.
- Runtime fingerprint SHA-256:
  `140e0547c50d738ae5564bed7a2d49d070bac0066888782f9837c7687d287ac8`.

No hidden acceptance or Codex reference may be available to RWKV, Controller, prompts, action
selection, witness selection or recovery during generation. They are used only after all 90 cases
have terminal raw results.

## Frozen Round12 comparator

- Results SHA-256: `85e2759678a27c57f61739d896c77513fc19e985dfb19fcbe9f04dcc899d1a30`.
- External `11/90`; Strict `0/90`; Completed `0/90`; FP `0`; FN `11`.
- Requests `1,436`.
- Basic/Medium/Hard External: `10/30`, `1/30`, `0/30`.
- Formal source-tree manifest SHA-256:
  `5df585e5df42469e05b03418dfdaba8f1456f46886d7499f0b01abd6494a0cd4`.

## Required artifacts and interpretation

Before generation:

1. full offline product tests pass;
2. LH-Control remains `30/30`;
3. runtime doctor and source manifest are written before case execution.

After generation:

1. preserve 90/90 per-case audit, model trace, events, state transitions, workspace and final-output
   equality data;
2. run the pre-existing acceptance evaluator and frozen Codex-reference comparison only after the
   90 raw runs finish;
3. generate backward causal analysis and classify the earliest failing stage plus downstream
   amplification for every case;
4. rerun full offline tests and LH-Control with the same frozen core;
5. record request counts, prompt/output tokens, FP/FN, transport failures and all hashes.

The control can show that the engine changes behavior, latency, reliability or scores. It cannot
identify which internal engine implementation change caused the difference because the new server
does not expose a build/version fingerprint and the old engine is no longer simultaneously
available for repeated A/B requests.

## Non-intervention and Git gate

- Never coerce, repair, replace, filter or rewrite RWKV's decisions or final output.
- Never rerun a completed generation merely because its answer is wrong.
- A transport-unknown case remains interrupted and is not silently regenerated under the same
  control identity.
- The control is never pushed as a better architecture. GitHub promotion remains closed until a
  separately pre-registered Round13 beats the best Round2 checkpoint under the restored FP gate and
  passes all full-data, causal-audit and raw-output-equality requirements.

