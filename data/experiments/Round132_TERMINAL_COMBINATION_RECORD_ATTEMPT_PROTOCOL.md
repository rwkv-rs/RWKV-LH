# Round132 — Terminal Combination Record Attempt (组合最优冲纪录轮) — PROTOCOL (preregistered)

**Status:** preregistered **2026-08-17, before R129/R130/R131 run** — the decision rule below is
locked now precisely so it cannot be bent to fit whatever data those screens produce. This is the
**14th and final round** of the program (R119–R132; extended from R119–R131 by +1 on owner's
instruction 2026-08-17 to add a terminal composition round). Baseline at R132 time = the best
**confirmed** configuration then in force (R126 v19-P1 today: Strict 36 official / 34 confirmatory,
FP 30, FN 0 — or whatever KEEP supersedes it in R129–R131).

## 0. Role and the one deliberate exception to "one variable per round"

Every prior round changed **exactly one** variable so a flip matrix could attribute cause. R132 is
the **single, deliberate exception**: it **stacks** the individually-validated mechanisms into one
configuration and makes the terminal record attempt. This is legitimate *only* because:

1. **R132 invents nothing.** It may compose **only** mechanisms already individually screened in
   R119–R131. No new mechanism, no new code path, may debut here. (Red line, §7.)
2. Every ingredient therefore carries its **own** single-variable causal evidence from its screening
   round; R132 tests the **composition**, not any mechanism in isolation.
3. It is the terminal step: attribution of the *interaction* is subordinate to the record, and the
   anti-interaction guard (§6) protects the program from a non-additive regression by falling back to
   the best single-round configuration.

This is the RWKV-creator ensembling posture applied at the program level: screen candidates
individually, then combine the winners ([[rwkv-creator-order-ensembling-advice]]).

## 1. Ingredient-selection rule (LOCKED — applied after R129–R131 resolve, not before)

An earlier-round mechanism **M is ELIGIBLE** for inclusion in R132 iff, in **its own** preregistered
screening round, **all** of the following held (i.e. M was completion-safe **and** FP-directional
**and** actually fired):

- **E1 Completion-safe:** Strict **non-decreasing** vs that round's baseline, **FN ≤ 1**, and
  R126-TP retention **≥ 32/34**. (Excludes every completion-collapse mechanism: R125 per-turn
  re-injection, R127 request-extraction, and any change that pushed TP→FN/OTHER.)
- **E2 FP-directional & attributable:** the variable **actually fired** and produced **≥ 1
  attributable FP→TP flip** where the mechanism was the cause (not seed variance). (Excludes
  no-ops where the mechanism was never adopted/never fired — e.g. R128 `reduce_json` at 2/90
  adoption with 0 helpful flips.)
- **E3 Compositionally admissible:** M does not structurally conflict with another included
  mechanism (see §2). On conflict, keep the dominant one and record the exclusion.

**KEEPs qualify automatically** (a KEEP already satisfies E1+E2). Individually-neutral no-ops and
any completion-harmful change are **excluded** — R132 does **not** stack neutral/harmful parts merely
to have something to combine. The baseline mechanisms (everything already inside R126) are the floor;
R132 stacks the **eligible new** mechanisms **on top** of that baseline.

## 2. Candidate mechanism pool (LIVE LEDGER — fill as each screen resolves)

The pool R129–R131 draw from = the still-unused RWKV-creator mechanisms and any orphaned-but-
promising direction. Each row is marked ELIGIBLE / EXCLUDED by the §1 rule once its round reports.

| Mechanism | Screening round | Touches | Individual result | E1 | E2 | E3 | → R132 |
|---|---|---|---|---|---|---|---|
| Order-permutation ensembling (vote across input-order permutations) | **R130** (REVERT) | input ordering | full-90 Strict **33**, FP **31**, FN 1, OTHER **25**, byte **4/5**, R126 proxy retention **27/31**; 195 canonical overrides prove the mechanism fired, but no valid attributable FP→TP was established; the generic-default leak was repaired and source-frozen separately | ✘ | ✘ (fired, causal benefit unproved) | — | **EXCLUDED (safety gates + attribution fail)** |
| Hierarchical reduce / order-robust observation fold (**structurally induced**, not an optional tool — see R128 lesson) | — (dropped) | observation folding | **falsified for this class** by R128 trace mining: M16 *did* fold (`reduce_json`) and *still* produced the wrong envelope (fold's `{source_ref,value}` leaked into the output) — compaction does not perform prose→envelope projection | ✘ | ✘ | — | **EXCLUDED (falsified, not screened)** |
| Homogeneous-item decomposition (split same-kind lists out of one JSON block) | **R129** (REVERT) | `_assignment` payload split (v19-P2) | full-90 Strict 36→**28**, FP 30→**31**, OTHER 24→**31**; **0/4 targeted OVER-STRUCTURE FP→TP** (H06/M16 FP→OTHER, M01 unmoved, LH06 unchanged); 13 cases→OTHER, 7 TP lost incl. M06 (R126's signature win) TP→OTHER — completion collapse (R127 family) | ✘ (Strict −8, retention 24/31) | ✘ (0 attributable targeted flips; 2 wins = variance-band oscillation) | — | **EXCLUDED (completion-harmful + no-op on target class)** |
| Confidence deferral | **R131** (REVERT) | terminal decision | repaired full-90 Strict **35**, FP **29**, FN 0, OTHER **26**, byte 5/5; 73/73 eligible Finals had metadata and the rule fired in 9 runs, but **all 9 immediately re-issued `final_answer` with zero intervening direct action**; 0 attributable FP→TP; R126 retention 33/36 and R128 proxy 27/31 | ✘ (OTHER 26>24; retention gates fail) | ✘ (fired, but 0 helpful continuation / FP→TP) | — | **EXCLUDED (terminal veto is behaviorally non-directive)** |
| — R126 request-last adjacency | R126 (KEEP) | `_assignment` key order | Strict 36, FP 30, FN 0 | ✔ | ✔ (FP→TP ×5) | baseline | **in baseline** |
| — R128 `reduce_json` optional fold | R128 (REVERT) | optional tool | 2/90 adopted, 0 helpful flips (M16 FP→FP, M17 TP→OTHER) | ✔ | ✘ (never usefully fired) | — | **EXCLUDED (no-op/harmful)** |

> Composition independence note (E3): order-ensembling (input ordering) and hierarchical reduce
> (observation folding) act on disjoint stages. **Homogeneous decomposition (payload split) is now
> EXCLUDED** (R129: it re-structures `_assignment` in a way that collapses completion — Strict −8 —
> and is not merely non-additive but actively harmful; see §2 row and the R129 MANUAL_CAUSAL_ANALYSIS).
> Two mechanisms that both re-structure `_assignment` in incompatible ways cannot both be included —
> pick the one with the larger individual FP→TP set. R129 shows any `_assignment` **grouping** change
> (beyond R126's key-order + request-placement) breaks completion, so R132 must not stack a second
> `_assignment`-reshaping mechanism on top of the R126 baseline geometry.

## 3. Empty-pool fallback (LOCKED)

If **no** new mechanism qualifies under §1 (all of R129–R131 REVERT), R132 does **not** invent a
combination. Instead it becomes a **best-configuration terminal confirmation**: a fresh
source-frozen full-90 of the current best baseline (R126). Rationale: single-run Strict variance is
±3 and R126 has already produced Strict 36 once; a clean terminal attempt at the record is legitimate
because terminal success is defined as a full-90 clearing thresholds **plus a confirmatory full-90**
(§6). This fallback stacks nothing neutral/harmful.

## 4. Composition assembly (deterministic, auditable)

R132's source is built by applying each ELIGIBLE mechanism's **exact** screening-round diff onto the
current best baseline. No mechanism is re-implemented for R132; each is transplanted byte-for-byte
from its screening branch/manifest. The offline gate (§5) verifies the assembled tree is exactly the
intended superposition.

## 5. Offline gate (must all pass before freeze)

- `pytest -q` → all green (baseline test count + each included mechanism's tests, no regression).
- `python -m compileall rwkv_lh` → clean.
- e2e catalog → **90/90** (core30 30 + lh12 12 + extension48 48).
- registry / `_validate_registry` clean; definitions↔handlers bijective.
- **Composition fidelity check:** for each included mechanism, the relevant file region is
  byte-identical to its screening-round frozen manifest; and the rendered `_assignment` + tool list
  + bootstrap are exactly the intended superposition (diff each against the individual-mechanism
  render, confirm no unintended interaction in the wire format).
- source isolation → only the union of the included mechanisms' files differs from the current best
  baseline; everything else hash-equal.

Then freeze the read-only source manifest
(`temp/generate_round132_*_source_manifest.py`, `--check` for read-only verify).

## 6. KEEP / REVERT + terminal-success gates (preregistered)

Let **B** = current best confirmed baseline (R126 floor: official {Strict 36, FP 30, FN 0},
confirmatory {Strict 34, FP 31, FN 0}); single-run Strict variance ±3. Let **S** = the best single
prior round's confirmed result.

- **G1 byte-precision == 5/5** (B01,B06,B13,B19,B28 exact-bytes hold).
- **G2 Strict ≥ B's confirmed floor** (no completion regression vs baseline).
- **G3 FN ≤ 1 AND OTHER not risen vs baseline** (guards the R125/R127 completion-collapse family — the
  standing failure mode of every "make the request more prominent" attempt).
- **G4 0 running AND 90/90 valid Finals.**
- **G5 R126-TP retention ≥ 32/34.**
- **G6 anti-interaction guard:** Strict(R132) **≥ S** on the same-scored run. If the stacked
  combination is **below** the best single ingredient round, the composition is non-additive-harmful
  → **REVERT** and declare **S the program's terminal result**.

**TERMINAL SUCCESS** (the /goal) = a **source-frozen full-90** with
**Strict > 31 ∧ FP ≤ 24 ∧ FN ≤ 1 ∧ 90/90 valid ∧ 0 running**, THEN a **confirmatory full-90 meeting
the SAME thresholds**, THEN a git checkpoint. On terminal success: commit locally as the terminal
checkpoint; **owner pushes** ([[commit-local-user-pushes]]).

**NON-TERMINAL KEEP** = beats B (Strict higher, **or** FP lower at non-worse Strict & FN) but misses
FP≤24 → commit locally as the new baseline; program has no rounds left, so this stands as the best
achieved result.

**REVERT** = fails G1–G6 → restore byte-exact to B (or to S under G6); the record stands at the best
prior round.

## 7. Red lines (unchanged + one addition)

Standing: no threshold/scoring edits post-run; no per-case special-casing; no reading hidden
acceptance (`.verifier-private`, `*.acceptance.json`, `codex_reference_answers.json`); no
reviewer/judge; no parsing task text for required keys; no guessing missing semantic parameters;
Controller never rewrites Finals; transport stays `prompt_replay`; no `--no-verify` unless explicitly
instructed; no push; no controller-generated business answers.

**R132 addition:** **no NEW mechanism may debut in R132.** It composes only mechanisms already
individually screened in R119–R131 (§1). This is what makes the sole multi-variable round of the
program legitimate — the interaction is the only thing untested, and G6 fences it.

## 8. Frozen parameters (unchanged)

model `rwkv7-g1i-13.3b-20260805-ctx16384`; endpoint `http://127.0.0.1:29610/v1`; temp 0.05 /
top_p 1.0 / top_k 0 / presence 0 / frequency 0 / penalty_decay 0.996; max-transitions 200;
concurrency 1; max_model_len 16384; transport `prompt_replay`; max_output_tokens 1800 action / 1400
terminal. Runner: `scripts/run_rwkv_e2e_benchmark.py --suite all`.
