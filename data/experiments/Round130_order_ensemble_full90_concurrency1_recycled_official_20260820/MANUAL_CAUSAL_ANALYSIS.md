# Round130 — Order-Shuffled Self-Consistency — Manual Causal Analysis

## Verdict

**REVERT.** The full per-turn K=3 order ensemble fails four preregistered safety gates and does not
establish the attributable FP→TP evidence required for KEEP or Round132 eligibility. The repaired
canonical default is the configuration in force after this screen.

## Frozen run and observed result

- Official output: `Round130_order_ensemble_full90_concurrency1_recycled_official_20260820`
- Catalog/finals: 90/90, zero running, all final outputs non-empty and byte-identical to the selected
  raw RWKV response.
- Outcome: Strict 33, FP 31, FN 1, OTHER 25; agent-completed 64, interrupted 26.
- Group Strict: B 21/30, M 10/30, H 2/18, LH 0/12.
- Cost: 10,239 physical model requests, 3,987 actions, 216 protocol rejections.
- The ensemble objectively fired: 4,305 ensemble decisions, including 195 canonical overrides in
  44 cases. Agreement was 3/3 on 3,029 decisions, 2/3 on 680, and absent on 596.

## Preregistered gate audit

| Gate | Requirement | Observed | Result |
|---|---|---|---|
| G1 | byte-precision 5/5 | B01/B06/B13/B28 pass; **B19 fails** → 4/5 | **FAIL** |
| G2 | Strict ≥ 34 | 33 | **FAIL** |
| G3 | FP ≤ 30, FN ≤ 1, OTHER ≤ 24 | FP 31, FN 1, OTHER 25 | **FAIL** |
| G4 | 90/90 valid Finals, zero running | 90/90, zero running | PASS |
| G5 | R126-TP retention ≥ 32/34, using the registered R128 proxy set | **27/31** retained; LH10, B14, B19, M11 lost | **FAIL** |

The KEEP rule additionally requires FP < 30 at non-regressed Strict, or Strict ≥ 37, plus at least
one attributable non-canonical-majority FP→TP. Neither score branch is met. Canonical overrides prove
that the mechanism was active, but activity alone is not causal benefit. Comparing this run with a
separate stochastic canonical run cannot identify which selected non-canonical action caused a final
FP→TP, so the attribution requirement is not claimed. Four hard-gate failures already make the
verdict invariant to that unresolved counterfactual.

## Root cause and system-wide impact

The implementation made the R130 experiment flag the constructor default. That leaked K=3 physical
generation into every generic `LongHorizonModel()` consumer instead of limiting it to this screening
round. The effect was global, not case-specific: every multi-pair action checkpoint could issue three
physical generations, allowing a non-canonical permutation to alter the canonical state trajectory.
It affected the production runner, CLI, web worker, direct controller construction, and tests through
their shared model constructor.

The frozen audit shows the resulting cost and instability directly:

- physical requests rose to 10,239;
- 2,967 logical decisions expanded to three generations, while only 1,338 stayed single-generation;
- 195 votes overrode the canonical candidate;
- B19 regressed despite the protocol's claimed byte-safety invariant, falsifying that invariant at
  whole-task acceptance level even though final output bytes themselves were never rewritten.

This is not repaired by a B19 special case. The generic constructor now defaults
`enable_order_ensemble=False`; only the R130-specific unit fixtures opt in. Production runner, CLI,
web, and controller construction therefore use one canonical RWKV generation per decision again.

## Canonical repair validation

The source-frozen repaired Full90 is recorded in
`../R130_canonical_repaired_full90_20260820/CANONICAL_DEFAULT_REPAIR_VALIDATION.md`.

Its result is Strict 35, FP 29, FN 0, OTHER 26; all five byte cases pass. All 2,844 logical model
decisions have generation count 1. Compared with the leaked run, requests fall 10,239→2,844
(−72.22%) and actions 3,987→2,494. The old→repaired outcome matrix is:

```text
              repaired TP  FP  FN  OTHER
old TP (33)            30   2   0      1
old FP (31)             3  25   0      3
old FN (1)              1   0   0      0
old OTHER (25)          1   2   0     22
```

This second run is repair validation, not a retroactive R130 KEEP: it removes the experimental
mechanism and is within the established R126 architecture's 34–36 Strict band. The only source
manifest changes from leaked R130 to the repair are `rwkv_lh/model.py` and the three test fixtures
that explicitly exercise the opt-in path. Focused tests (28), the complete suite (114), compileall,
catalog validation, source-manifest recheck, and 90/90 execution all passed.

## Round132 eligibility and regression risk

- E1 completion-safe: **fail** (Strict below the confirmed floor, G1/G3/G5 regressions).
- E2 attributable FP-directional: **not established** (overrides fired, no valid causal FP→TP proof).
- E3 composition: moot after E1/E2.
- Round132: **EXCLUDED**.

The remaining regression risk is accidental re-enablement of `enable_order_ensemble` in a generic
constructor. The default-off constructor test and explicit opt-in ensemble tests cover that boundary;
future runtime wiring should preserve the same isolation.

