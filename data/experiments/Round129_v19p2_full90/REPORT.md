# Round129 v19-P2 — Bootstrap Homogeneous-Item Decomposition — REPORT

**Verdict: REVERT.** Three of five preregistered gates fail; the hypothesis is falsified with clean
causal attribution. Source restored byte-exact to `baseline/round126-v19p1` (model.py sha256
`399bf5225ef384d98e4994246aa0c1e6460f177fd836820caec70d7b57ff0212`); 107 tests green; nothing running.

## Setup
- **Baseline:** Round126 v19-P1 (official {Strict 36, FP 30, FN 0, OTHER 24}; confirmatory {Strict 34,
  FP 31, FN 0}). Single-run Strict variance ±3.
- **Single variable (only `rwkv_lh/model.py`, `_assignment`):** the two homogeneous lists
  `workspace_manifest` and `recent_exact_action_records` split **out** of the terminal `_assignment`
  JSON into separate labeled blocks placed **above** a compact terminal JSON
  `{protocol,constraints,instruction,immutable_request}`; `protocol` bumped to
  `single-rwkv-direct-action.v2`. R126 request-last adjacency and R127 closed-JSON completion geometry
  both preserved; every field's content bytes identical to R126 (grouping/placement only).
- **Run:** frozen manifest `Round129_source_manifest.json` (`--check` 48 files, 0 mismatch; exactly
  `rwkv_lh/model.py` differs from R126); model `rwkv7-g1i-13.3b-20260805-ctx16384`; temp 0.05 /
  top_p 1.0 / top_k 0; max-transitions 200; concurrency 1; **90/90 valid Finals; 0 running.**

## Results (full-90, authoritative from results.json)
| Metric | R126 (baseline) | R129 | Δ |
|---|---|---|---|
| **Strict (TP)** | 36 | **28** | **−8** |
| FP | 30 | **31** | +1 |
| FN | 0 | 0 | 0 |
| OTHER | 24 | **31** | **+7** |
| byte-precision | 5/5 | **5/5** | 0 |
| valid Finals / running | 90 / 0 | 90 / 0 | — |
| R126-TP retention | — | **24/31** (proxy) | −7 TP |

Strict collapsed 8 below the R126 confirmed floor — far outside the ±3 variance band. FP did **not**
fall; it rose by 1. The apparent (small) FP move is entirely a shadow of non-completion: 13 cases
drained into OTHER while TP itself fell.

## Flip matrix (R128 as R126-proxy → R129)
R126's official per-case `results.json` was not retained (only REPORT/MANUAL); R128 is the standard
per-case proxy (88/90 byte-identical to R126 source — only M16/M17 ever fired `reduce_json`), as
established in `R119_R128_TEN_ROUND_HONEST_NEGATIVE_RESULT.md` §3. M16 is flagged for the proxy caveat.

```
row=R128(proxy) \ col=R129    TP    FP    FN  OTHER
  TP                          24     3     0     4
  FP                           2    24     0     9
  FN                           0     0     0     0
  OTHER                        2     4     0    18
```
- **FP→TP wins: 2** (M03, M07) — both unrelated to the targeted OVER-STRUCTURE class.
- **TP lost: 7** — TP→FP ×3 (B07, B14, B29), TP→OTHER ×4 (H10, LH10, M11, M21).
- **Into OTHER: 13** (M06, M09, H06, H07, H08, H10, LH04, LH08, LH10, B26, M11, M16, M21).
- **FN: 0.**

## Targeted cases (protocol §3 prediction — flip among {H06, M01, LH06, M16})
| Case | Subtype | R128 | R129 | Predicted FP→TP? |
|---|---|---|---|---|
| H06 | OVER-STRUCTURE | FP | **OTHER** | ✗ (suppressed, not flipped) |
| M01 | OVER-STRUCTURE | OTHER | OTHER | ✗ |
| LH06 | OVER-STRUCTURE | FP | FP | ✗ (unchanged) |
| M16 | FIELD-MERGE | FP | **OTHER** | ✗ (suppressed) |

**Zero of four targets flipped to TP.** The mechanism produced no attributable OVER-STRUCTURE FP→TP.

## Gates (preregistered §4, baseline R126)
- **G1 byte-precision == 5/5:** **PASS** (5/5).
- **G2 Strict ≥ 34:** **FAIL** (28; −8 below floor, outside ±3).
- **G3 FP ≤ 30 AND FN ≤ 1:** **FAIL** (FP 31 > 30; FN 0 OK).
- **G4 0 running AND 90/90 valid:** **PASS**.
- **G5 R126-TP retention ≥ 32/34:** **FAIL** (proxy 24/31; 7 TP lost).

KEEP required FP < 30 at Strict ≥ 34, or Strict ≥ 37 at FP ≤ 30 — neither holds. → **REVERT.**

## Actions taken
- REVERT: `rwkv_lh/model.py` restored byte-exact to `baseline/round126-v19p1` (hash match ✓).
- Verified: `pytest -q` 107 passed; `compileall` clean; all `rwkv_lh/*.py` byte-identical to baseline.
- No test was modified for R129 (no test asserted the `_assignment` byte shape), so none to quarantine.
- R132 ledger updated: homogeneous-item decomposition → **EXCLUDED** (E1 fail: completion regression;
  E2 fail: 0 attributable OVER-STRUCTURE FP→TP). See MANUAL_CAUSAL_ANALYSIS.md.
- No push (owner pushes; this is a REVERT — nothing to commit beyond experiment records).
