# Round125 v19-P0 — Spec-Adjacency Anchor — REPORT

**Verdict: REVERT (decisive).** Strict 12/90 (−18 vs R119's 30), FN 19 (+19), R119-TP retention 8/30.

## Setup
- **Baseline:** Round119 v18-P0 (Strict 30 / FP 36 / FN 0).
- **Single variable:** an ephemeral generation-time *spec-adjacency anchor* — the verbatim `state.goal.request` (+ constraints) re-stated immediately before the continuation marker on **every** ACTION/terminal turn, with an instruction to "verify your artifact against this text before completing." Not persisted (transcript_digest unchanged); input-budget skip. Only `rwkv_lh/model.py` + `rwkv_lh/model_session.py` changed vs R119.
- **Hypothesis:** 21/36 R119 FP were pure exact-literal drift; placing the verbatim request adjacent to the write point every turn should recover them (FP→TP) at low cost.
- **Run:** frozen manifest `Round125_v19p0_source_manifest.json` (`--check` 49 files, 0 mismatch); model rwkv7-g1i-13.3b-20260805-ctx16384; max-transitions 200; concurrency 1; 90/90 completed.

## Results
| Metric | R119 | R125 | Δ |
|---|---|---|---|
| Strict (TP) | 30 | **12** | **−18** |
| FP | 36 | 4 | −32 |
| FN | 0 | **19** | **+19** |
| OTHER (no-complete, wrong artifact) | 24 | 55 | +31 |
| R119-TP retained | — | 8/30 | — |
| byte-precision | 5/5 | 3/5 | −2 |
| code-chain | 6/6 | 0/6 | −6 |
| literal-drift FP recovered (FP→TP) | — | **3**/21 (B04, B29, M04) | — |
| anchor fired | — | 7768 / 7920 req (98%); 152 budget-skipped | — |
| mean effective prompt tokens/req | — | **10314** | — |

## Gates (baseline R119)
- G1 byte==5/5: **FAIL** (3/5; B13, B28 lost)
- G2 Strict≥32: **FAIL** (12)
- G3 FP≤31: PASS (4) — *but see analysis: FP collapse is a shadow of completion collapse, not a win*
- G4 FN≤1 & 0 running: **FAIL** (FN 19)
- G5 R119-TP retention≥28/30: **FAIL** (8/30)

4 of 5 gates fail. **VERDICT: REVERT.**

## One-line cause
The mechanism (fix literal drift) worked for exactly 3 cases, but its *delivery* — re-injecting the full verbatim request every turn plus a second "verify before completing" decision — violated the fixed-state adjacency principle (per-request tokens → mean 10314; score inversely correlated) and the RWKV-creator decomposition rule (a homogeneous duplicate of the root request in every prompt). It converted 14 R119 successes into correct-artifact-but-never-complete (TP→FN) and broke 8 more outright (TP→OTHER). See `MANUAL_CAUSAL_ANALYSIS.md`.

## Post-verdict actions
- Byte-revert `rwkv_lh/model.py` → sha 49dea587… and `rwkv_lh/model_session.py` → sha f4c9a6a3… (R119 baseline).
- Quarantine `tests/test_round125_spec_anchor.py`; confirm full suite green + source byte-exact vs R119 manifest.
- No commit (REVERT).
