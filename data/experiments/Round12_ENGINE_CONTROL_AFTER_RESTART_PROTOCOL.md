# Round12 unchanged-architecture control after engine restart

Pre-registered: 2026-08-13 Asia/Shanghai, before any E2E-90 request in this control.

## Purpose

Run the frozen Round12 Agent architecture on the user's restarted, locally forwarded endpoint
`http://127.0.0.1:29610/v1`. This separates the prior unhealthy engine instance from Agent
architecture before Round13.

Output directory: `data/experiments/Round12_engine_control_after_restart_20260813/`.

This remains an engine control, not a new architecture Round and not a GitHub promotion candidate.

## Evidence requiring this rerun

The pre-restart engine control used the same frozen core but obtained External `2/90`, Strict `0/90`,
Completed `0/90`, with `61/90` cases failing before Goal creation. Its results SHA-256 is
`71a504911be278064d7a68afa866300acc07284ed94fc834b3d6ba445f1643d1`.

After the user restarted the engine and exposed port `29610`, the preregistered public Basic-30
Goal-only diagnostic produced:

| Client concurrency | Valid Goal | Parseable returns | Transport failures |
| ---: | ---: | ---: | ---: |
| 1 | 29/30 | 32/32 | 0 |
| 2 | 29/30 | 32/32 | 0 |
| 4 | 28/30 | 32/32 | 0 |
| 8 | 30/30 | 30/30 | 0 |

Diagnostic results SHA-256:
`c30a65563f11aa65ed75d7c1f559c4183a8af098bbc4ea4ddba0c0f2dbd55e74`.
All 120 durable case results and traces matched the aggregate. This rejects monotonic concurrency
degradation on the restarted instance and justifies a new full unchanged-architecture control.

## Frozen code and data

The current benchmark core remains byte-identical to frozen Round12:

- Controller `5cd25f669ea82eca75bedaea1d98f9e0e2d68328b187a69182bc423845e838e5`
- Harness `c4631b3d839da010ef54c75183207ad5c7fda8d60918df2c0a62d1108dce01d8`
- Memory `461bfcf192e4235c975520cb34d7cac1cd50acb3d4392bcdaa3ec48141f9e797`
- Model `db71a604231fac29b5023b40f0855d849b6f34da9eeaded48b6546481b45dbc1`
- Proof `b58fa752c41ba773260c52c826cfe0002ead3e39eafd0ab52bb97529794ddabd`
- Schema `d2a5ff9addf036b6cb0e64c60dbf71d7f2fd19130820052c20fbbe9feec19b43`
- Store `d7203c0e779b25055a2e91dd0e5def792a0bf66954be233b6e638ec87e58ac05`
- Tool protocol `921737961e26676bce38f1fc43c7ace2e1030778c834c2b29b4c2d144be5e105`
- Witness `a5293cbaa39f1471765e828eaa3afa762393ccce7c84be4634e1faef0f4a2a14`
- E2E runner `c1d5c72550788c53826ab8a332c7a2ab6265a2353d236b2442a7c6a7a9ba47a8`

The only old 54-file manifest mismatch remains the additive local-web entry in `pyproject.toml`; it
is outside the benchmark worker/Controller/model path. The control writes a new complete source
manifest before cases run.

Dataset, visible-task hashes, hidden acceptance hashes and post-run Codex-reference hash remain
exactly those in frozen `Round12/RUN_PROTOCOL.json`. Acceptance and references are forbidden during
generation.

## Fixed run configuration

- Suite: RWKV-E2E-90 v1, Basic/Medium/Hard each 30.
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`.
- Backend profile: `vllm-rwkv-rapid`; max model length 16,384.
- Endpoint: `http://127.0.0.1:29610/v1`; API key configured locally and never recorded.
- `/capabilities` remains 404; prompt replay only, no inferred recurrent-state capability.
- Sampling: exactly frozen Round12 policy; top-p 1, top-k 0, penalties 0, penalty decay 0.996.
- Concurrency 8; maximum transitions 200.
- Never regenerate a terminal case because its answer is wrong. Outcome-unknown transport cases stay
  interrupted under this identity.

## Required pre/post gates

Before generation: full offline suite `211/211`, LH-Control `30/30`, runtime doctor, source manifest,
and 90-case dataset validation.

After all 90 raw cases terminate:

1. run the existing acceptance and frozen reference comparison;
2. preserve all per-case prompt/raw/parsed/normalized/event/state/workspace data;
3. generate score-independent backward causality first, then post-run standard-answer comparison;
4. quantify Goal/plan/action/witness/proof funnel, FP/FN, requests and token usage;
5. rerun full offline suite and LH-Control;
6. compare against frozen old-engine Round12 and the pre-restart control without merging cases.

## Interpretation and Git boundary

- A substantial recovery from pre-restart `2/90`, especially far fewer Goal failures, is engine
  instance recovery—not an Agent architecture gain.
- Remaining failures after Goal creation guide Round13, but no Round13 change is made during this run.
- This control is never pushed as a better architecture. Git promotion remains gated on a separately
  preregistered Round13 beating the Round2 best checkpoint with FP restored, full causal coverage,
  raw-final equality and complete regressions.
- No rule may repair RWKV choices, infer criteria/evidence, select passing handles, or modify final
  output.

