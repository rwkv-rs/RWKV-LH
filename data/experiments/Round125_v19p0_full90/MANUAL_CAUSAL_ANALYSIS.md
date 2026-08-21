# Round125 v19-P0 — MANUAL CAUSAL ANALYSIS

## 1. Three-way flip matrix (R119 → R125, by outcome class)

Classes: TP = strict pass; FP = completed ∧ ¬external_pass; FN = external_pass ∧ ¬completed; OTHER = neither (wrong artifact and never completed — failed/interrupted).

```
           R125:  TP     FP     FN   OTHER
R119 TP (30)       8      0     14      8
R119 FP (36)       3      4      4     25
R119 FN (0)        0      0      0      0
R119 OTHER (24)    1      0      1     22
```

Totals: R119 {TP 30, FP 36, OTHER 24, FN 0} → R125 {OTHER 55, FN 19, TP 12, FP 4}.

## 2. What the anchor was supposed to do — and did, narrowly
- **FP→TP = 3**: `E2E-B04`, `E2E-B29`, `E2E-M04`. Plus `OTHER→TP` = 1 (`E2E-M21`). These are the only cases where the anchor delivered its intended win: the verbatim request adjacent to the write point fixed literal drift **and** the model still completed.
- Of the 21 predicted literal-drift FP, only **1** (B04) actually recovered to TP; the other 20 did not — because the same anchor that could fix their literal also pushed them out of *completion* (17 of the 21 landed in FN/OTHER).
- So the mechanism is real but tiny (+3–4 net TP from the FP pool), and it is dwarfed by the damage.

## 3. The damage — two mechanisms, both principle violations

### (a) TP→FN = 14 — the "verify before completing" second decision
`B03, B07, B08, B13, B20, B21, B23, B25, B27, B28, LH10, M05, M07, M12`.
These 14 R119 successes now produce the **correct external artifact** but **never declare completion** (9 interrupted at/near the transition ceiling, rest failed). Cause: the anchor's instruction "verify your artifact against this text **before completing**" added a *second decision* on top of "act." Once the artifact was already correct, the model obeyed the verify-loop instead of emitting `final_answer` — it kept re-reading/re-checking against the re-stated spec. FN went 0→19. This is the exact failure the fixed-state adjacency principle predicts: **a second decision per call degrades a fixed-state model.**

### (b) TP→OTHER = 8 + FP→OTHER = 25 — token bloat + homogeneous duplication
`TP→OTHER: B09, B10, B12, B30, H10, M02, M20, M30` (includes all 6 code-chain cases → code-chain 0/6). `FP→OTHER: 25 cases`.
The anchor re-injected the **full verbatim request every turn**, driving **mean effective prompt tokens to 10314/req** (anchor fired on 7768/7920 = 98% of requests). Score is strictly inversely correlated with per-request prompt tokens (adjacency-principle evidence). Worse, the re-stated request is **homogeneous** with the root request already sitting at the transcript head — two same-kind copies of the assignment in one context. That is precisely the RWKV-creator decomposition rule's forbidden pattern (multiple homogeneous items mixed → positional bias drops the middle). Multi-step/code-chain tasks, which carry the longest transcripts, were hit hardest (code-chain 6/6 → 0/6).

## 4. Why FP dropping 36→4 is NOT a win
G3 (FP≤31) passed only because **completion itself collapsed**: you cannot be a false-positive if you never say "done." 32 of the 36 R119 FP simply moved into FN/OTHER (non-completion), not into TP. FP is not a safe gate when FN/OTHER are exploding — the joint reading (Strict down 18, FN up 19) is unambiguous.

## 5. Byte-precision / code-chain per-case
- **byte-precision 3/5**: held `B01, B06, B19`; lost `B13, B28` (both TP→FN — artifact byte-correct, never completed).
- **code-chain 0/6**: all of `B10, B20, B30, M02, M12, M20` → OTHER. Longest transcripts + full-request re-injection every turn = worst token bloat.

## 6. Causal conclusion (feeds the next rounds)
The R125 result **confirms, in the negative, both the fixed-state adjacency principle and the RWKV-creator decomposition rule.** Adjacency of the literal spec is the right idea (it produced the only genuine wins, FP→TP ×3), but the *delivery* was wrong on two counts the principles name explicitly:
1. **It added a second decision** ("verify before completing") → TP→FN ×14.
2. **It duplicated homogeneous information every turn** and inflated per-request tokens → TP/FP→OTHER ×33, code-chain 6→0.

**Corrected direction for R126:** achieve spec adjacency **without** (a) a second decision and **without** (b) a homogeneous duplicate re-injected each turn. Candidates consistent with the principles:
- Restructure the *single bootstrap* so the verbatim request sits adjacent to the continuation point **once** (fix `_assignment`'s `sort_keys` burial), rather than re-injecting it every turn.
- Or the homogeneous-decomposition round: split the same-kind lists (workspace_manifest / recent_action_records) out of one JSON block so no context carries N peers of one type.

The anchor is removed; source reverts byte-exact to R119.
