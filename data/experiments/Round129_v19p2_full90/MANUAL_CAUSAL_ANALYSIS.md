# Round129 v19-P2 — Manual Causal Analysis

**Question the round asked:** does splitting the two homogeneous lists (`workspace_manifest`,
`recent_exact_action_records`) out of the terminal `_assignment` JSON — leaving a *flat* terminal
object the model completes from — lower the model's "nested-wrapper house style" prior and flip the
OVER-STRUCTURE FP class (H06, M01, LH06; +M16 FIELD-MERGE) to TP, without regressing completion?

**Answer: no, on both halves.** The mechanism (a) produced **zero** attributable OVER-STRUCTURE
FP→TP flips and (b) triggered a broad completion regression (Strict 36→28, OTHER 24→31). The
hypothesis is falsified and the change is completion-harmful. This is an R127-family collapse.

---

## 1. The prediction vs the outcome

Protocol §2/§3 predicted the *maximum* reachable was the 3 OVER-STRUCTURE cases (+M16 = 4), with an
explicit pre-registered weak-link caveat: *"the OVER-STRUCTURE FP occur at a deep write turn, far
below the bootstrap where this lever acts; the effect is expected to be attenuated... a null result
is a real possibility."* The outcome is worse than the null: not only did none of the four targets
flip to TP, the restructuring **suppressed completion** across unrelated cases.

| Target | Subtype | R128(proxy) | R129 | Interpretation |
|---|---|---|---|---|
| H06 | OVER-STRUCTURE | FP | OTHER | did not complete — no projection to TP |
| M01 | OVER-STRUCTURE | OTHER | OTHER | unmoved |
| LH06 | OVER-STRUCTURE | FP | FP | unmoved (still over-structured envelope) |
| M16 | FIELD-MERGE | FP | OTHER | did not complete |

The two actual FP→TP wins (M03, M07) are **not** in the targeted class and are within the churn a
±3-variance re-run produces (R119→R126 already flipped M03 FP→TP once; this is the same case
oscillating, not new signal from decomposition). No causal chain links the decomposition to a
targeted flip.

## 2. Why completion collapsed (the real effect)

The dominant transition is **movement into OTHER: 13 cases** (FP→OTHER ×9, TP→OTHER ×4), against 2
unrelated wins. TP fell 36→28. This is the exact signature the program has now seen three times:

- **R125** (per-turn re-injection + verify): TP→FN ×14, →OTHER ×33 — completion collapse.
- **R127** (request lifted OUT of the JSON): FP→OTHER ×9, TP→FN ×4 — "adjacent-but-open → never
  terminates"; the FP fall was a *shadow* of not completing.
- **R129** (homogeneous lists lifted OUT of the terminal JSON): FP→OTHER ×9, TP→OTHER ×4 — same
  shadow; FP did not even fall (30→31).

R129 was designed to avoid R127's failure by keeping `immutable_request` **inside a closed** terminal
JSON and **last** (both adjacency invariants preserved). It did — and completion **still** collapsed.
The decisive new negative knowledge: **completion is sensitive to the wire shape of the bootstrap
context above the terminal JSON, not only to the request's position within it.** Splitting the two
homogeneous lists into labeled prose-headed blocks (`workspace_manifest:\n{…}\n\nrecent_…:\n{…}\n\n{…}`)
changed the turn-1 geometry the model plans from: the continuation point is now preceded by two loose
JSON blobs under prose headers rather than a single self-contained object. Under near-greedy decoding
at temp 0.05 that perturbation was enough to push many cases off the "emit one JSON call → complete"
trajectory into the interrupted/no-final basin. The flat-terminal-object idea did not lower the
nesting prior enough to be observed at the deep write turn (as the caveat feared); its only measurable
effect was upstream, on whether the model completes at all.

## 3. M06 — the canary that confirms causation

M06 is the positional-bias signature case: R119 FP → **R126 FP→TP** was the single clearest
attributable win of the request-last adjacency change (documented in R126 REPORT §"Flip matrix"). In
R129 M06 regresses **TP→OTHER**. Because the *only* source delta from R126 is the decomposition, and
M06's win was causally tied to the R126 bootstrap geometry, its regression is direct evidence that the
decomposition **degraded the very geometry R126's KEEP established** — not a variance artifact. The
mechanism is not neutral-with-noise; it is actively harmful to the completion path R126 secured.

## 4. Byte-precision unaffected (as structurally predicted)

B01/B06/B13/B19/B28 all held TP (5/5). Confirms the pre-registered structural guarantee: `_assignment`
carries file *metadata*, never file *content*; observation bytes are untouched; G1 cannot regress from
a bootstrap-grouping change. The collapse is purely a completion/planning effect, cleanly separated
from byte-precision — which is why G1 passing alongside G2/G3/G5 failing is coherent, not contradictory.

## 5. Consequence for R132 eligibility (§1 rule)

Homogeneous-item decomposition is judged against the R132 ingredient-selection rule:

- **E1 Completion-safe** (Strict non-decreasing, FN≤1, R126-TP retention ≥32/34): **FAIL.** Strict
  −8, retention 24/31. This is a completion-collapse mechanism, exactly the class E1 exists to exclude.
- **E2 FP-directional & attributable** (≥1 attributable FP→TP the mechanism caused): **FAIL.** 0
  targeted flips; the 2 wins are unrelated variance-band oscillation.

→ **EXCLUDED from R132** (E1 fail ∧ E2 fail). Recorded in
`Round132_TERMINAL_COMBINATION_RECORD_ATTEMPT_PROTOCOL.md` §2.

## 6. Durable negative knowledge (adds to the falsified-hypotheses ledger)

> **Restructuring the bootstrap context — even losslessly, even while preserving request-last-inside-
> closed-JSON — degrades completion.** Lifting homogeneous lists out of the terminal `_assignment`
> object into labeled blocks above it collapsed Strict 36→28 with 13 cases into OTHER and 0 targeted
> FP→TP. The bootstrap's single-self-contained-object wire shape is itself load-bearing for
> completion; the adjacency invariant (request last, inside closed JSON) is **necessary but not
> sufficient**. This is the third confirmation (R125, R127, R129) that any change reshaping the
> bootstrap/turn-1 geometry away from R126's exact form drains completion into OTHER. **The R126
> `_assignment` wire shape is now treated as CLOSED — not just its key order (R126) and request
> placement (R127), but its single-object grouping (R129).**

This makes the reachability picture from `R119_R128_TEN_ROUND_HONEST_NEGATIVE_RESULT.md` §5
(corrected) firmer: the OVER-STRUCTURE FP class is not reachable by *any* bootstrap-side lever screened
so far, because every bootstrap restructuring strong enough to move house-style also breaks
completion. The dominant failure remains prose-contract → JSON-envelope translation at a deep write
turn, whose fix (the target output shape) is red-lined.
