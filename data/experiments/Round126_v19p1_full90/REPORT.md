# Round126 v19-P1 — Bootstrap Request-Last Adjacency — REPORT

**Verdict: KEEP — new historical Strict best 36/90** (R119 30 → 36; prior all-time best was R46's 31).
All five preregistered KEEP gates pass. **Note:** the `/goal` *terminal-success* thresholds are not
all met (FP 30 > goal's FP≤24), so this is a new best baseline to build on, not the terminal stop.

## Setup
- **Baseline:** Round119 v18-P0 (Strict 30 / FP 36 / FN 0).
- **Single variable (only `rwkv_lh/model.py`):** `_assignment` bootstrap payload reordered so
  `immutable_request` is the **last** field (nearest the `Assistant:` continuation point) and
  `sort_keys` dropped. Content byte-identical to R119; only key ordering changed. No per-turn
  re-injection, no second decision, **zero token delta** (this is the corrected, cost-free form of
  the R125 adjacency idea).
- **Run:** frozen manifest `Round126_v19p1_source_manifest.json` (`--check` 48 files, 0 mismatch;
  only model.py differs from R119); model rwkv7-g1i-13.3b-20260805-ctx16384; temp 0.05 / top_p 1.0 /
  top_k 0; max-transitions 200; concurrency 1; 90/90 valid Finals; 0 running.

## Results
| Metric | R119 | R126 | Δ |
|---|---|---|---|
| **Strict (TP)** | 30 | **36** | **+6** |
| External passed | 30 | 36 | +6 |
| Agent completed | 66 | 66 | 0 |
| FP | 36 | 30 | −6 |
| FN | 0 | 0 | 0 |
| byte-precision | 5/5 | 5/5 | 0 |
| R119-TP retention | — | 29/30 | — |

### Per-group Strict
| Group | R126 |
|---|---|
| B (core, 30) | 23/30 |
| M (medium, 30) | 10/30 |
| H (hard, 18) | 2/18 |
| LH (long-horizon, 12) | 1/12 |

## Flip matrix (R119 → R126)
```
           R126:  TP     FP     FN   OTHER
R119 TP (30)      29      1      0      0
R119 FP (36)       5     25      0      6
R119 FN (0)        0      0      0      0
R119 OTHER (24)    2      0      0     18
   (OTHER→FP 4 folded into row; see analysis)
```
Key transitions: **FP→TP ×5** (B11, B17, LH09, M03, **M06**), **OTHER→TP ×2** (M21, M24),
TP→FP ×1 (LH10, the sole regression — within ±3 noise, retention 29/30), FP→OTHER ×6, OTHER→FP ×4.

## Gates (preregistered, baseline R119)
- G1 byte==5/5: **PASS** (5/5)
- G2 Strict≥31: **PASS** (36)
- G3 FP≤36 & FN≤1: **PASS** (FP 30, FN 0 — no completion collapse; the R125 failure mode did not recur)
- G4 0 running & 90/90 valid: **PASS**
- G5 R119-TP retention≥28/30: **PASS** (29/30)

**All 5 gates pass → KEEP.** R126 becomes the new baseline.

## /goal terminal-success check
| Threshold | Value | Met |
|---|---|---|
| Strict > 31 | 36 | ✅ |
| FP ≤ 24 | 30 | ❌ |
| FN ≤ 1 | 0 | ✅ |
| 90/90 valid, 0 running | yes | ✅ |

Not terminal success (FP 30 > 24). Next round (R127) targets FP reduction from the now-dominant
FP=30 pool while holding Strict, toward the terminal FP≤24.

## Actions
- KEEP; R126 is the new baseline (source already frozen; model.py is the only change vs R119).
- Run one unchanged-source confirmatory full-90 to validate 36 against ±3 single-run variance before
  building R127 on it and before the owner pushes.
- Per owner instruction ("commit locally when a round is better; owner pushes"): local git commit of
  the R126 KEEP after confirmatory; **no push**.
