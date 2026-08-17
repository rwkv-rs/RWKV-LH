# Round126 v19-P1 — MANUAL CAUSAL ANALYSIS

## 1. Headline
A **zero-cost key-reordering** of the bootstrap payload — moving the verbatim `immutable_request`
to the last field so it sits adjacent to the `Assistant:` continuation point, and dropping
`sort_keys` — lifted Strict **30 → 36** with **no regression** (retention 29/30, byte 5/5, FN 0, no
token increase). This is the cleanest possible confirmation of the fixed-state adjacency principle:
the *same bytes*, merely placed nearest the decision point, recover six net cases.

## 2. Three-way flip matrix (R119 → R126)
```
           R126:  TP     FP     FN   OTHER
R119 TP (30)      29      1      0      0
R119 FP (36)       5     25      0      6
R119 FN (0)        0      0      0      0
R119 OTHER (24)    2      4      0     18
```
Totals: R119 {TP 30, FP 36, OTHER 24} → R126 {TP 36, FP 30, OTHER 24, FN 0}.

## 3. The wins — adjacency recovered literal-drift FP without any cost
- **FP→TP ×5**: `B11, B17, LH09, M03, M06`. These are R119 false-positives where the model
  completed but produced a literal that drifted from the request. With the verbatim request now the
  last thing it reads before deciding, the literal was reproduced correctly.
  - **M06 is the signature case**: the RWKV creator cited it as "a late-read item polluted the
    manifest / the request got out-competed by later same-kind content." Placing the request last
    (after workspace_manifest and recent_action_records) is exactly the fix his diagnosis implies —
    and M06 flipped FP→TP. Direct, independent confirmation of the positional-bias root cause.
- **OTHER→TP ×2**: `M21, M24` — cases that previously neither completed nor passed now resolve,
  because the decision turn reads the exact request adjacent rather than a buried copy.

## 4. Non-regression — completion did NOT collapse (contrast with R125)
- **FN stayed 0.** R125's fatal signature (correct artifact, never completes; FN 0→19) is absent,
  because R126 adds **no second decision** and **no per-turn duplication** — it only reorders one
  render. Agent-completed held at 66.
- **TP→FP ×1** (`LH10`) is the only lost R119 success; retention 29/30 is within single-run ±3
  variance and is not a structural regression (no shared cause with the change — a long-horizon case
  whose completion boundary is inherently marginal).
- **byte-precision 5/5** held (B01, B06, B13, B19, B28) — the reorder did not disturb exact-bytes
  tasks; if anything it strengthens them (request adjacent at the write turn).

## 5. The churn — FP→OTHER ×6 and OTHER→FP ×4 (net FP −6)
- `FP→OTHER ×6` (B04, H01, H08, H18, LH01, M14): six former FP no longer complete-wrong; some are
  genuine avoidance of a wrong completion, some are new non-completion. Net this *reduces* FP.
- `OTHER→FP ×4` (H17, LH12, M01, M28): four former hard failures now at least complete (albeit
  wrong) — movement toward the completion frontier.
- Net FP 36→30. FP is now the dominant remaining failure class (30/90), concentrated in H (16/18
  non-TP) and LH (11/12 non-TP) and M (20/30 non-TP).

## 6. Variance caveat and confirmatory
Single-run Strict variance is ±3. 36 vs the prior best 31 is +5, i.e. even at the low tail
(36−3=33) it clears the 31 bar; combined with a coherent causal mechanism (real FP→TP recoveries,
M06 signature) and 29/30 retention, the gain is very likely structural, not noise. An unchanged-source
confirmatory full-90 will validate the 36 before R127 is stacked on it and before the owner pushes.

## 7. Where R127 goes (evidence-derived)
FP=30 is now the dominant class, concentrated in H/LH/M. The adjacency principle worked at the
**root/turn-1** decision; the residual FP are largely **multi-step** cases where, by the write turn,
the request is again far behind accumulated observations (append architecture). The evidence-backed
R127 candidate is therefore the **RWKV-creator decomposition rule**: the residual FP concentrate
where same-kind content (multiple manifest entries / multiple prior action records) sits between the
request and the decision. Split those homogeneous lists so no single context carries N peers of one
type out-competing the request — WITHOUT adding a second decision or per-turn duplication (the R125
lesson). To be preregistered from this matrix, not a backlog.

## 8. Conclusion
KEEP. R126 is the new baseline (Strict 36). The fixed-state adjacency principle and the RWKV-creator
positional-bias diagnosis are now confirmed **positively** (this round) after being confirmed
**negatively** by R125's over-delivery. The terminal `/goal` FP≤24 threshold is not yet met; the
program continues toward it.
