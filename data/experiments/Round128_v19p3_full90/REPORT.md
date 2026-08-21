# Round128 v19-P3 — Read-Time Hierarchical Fold (`reduce_json`) — REPORT

**Verdict: REVERT.** New 18th optional operation `reduce_json`. Baseline = R126 v19-P1 (official
{Strict 36, FP 30, FN 0}; confirmatory {Strict 34, FP 31, FN 0}; single-run Strict variance ±3).

## Result (source-frozen full-90, suite `all`, 90/90 valid, 0 running)

| Metric | R126 official | R126 confirmatory | **R128** | vs official |
|---|---|---|---|---|
| Strict (TP) | 36 | 34 | **31** | −5 |
| FP | 30 | 31 | **35** | +5 |
| FN | 0 | 0 | **0** | 0 |
| OTHER | 24 | 25 | **24** | 0 |
| byte-precision | 5/5 | 5/5 | **5/5** | = |

Runner summary line: `{"total": 90, "passed": 31, "failed": 59}`.

## Gate evaluation (preregistered, baseline R126)

| Gate | Requirement | R128 | Result |
|---|---|---|---|
| G1 | byte-precision == 5/5 | 5/5 (B01,B06,B13,B19,B28 all completed+external) | **PASS** |
| G2 | Strict ≥ 34 (R126 confirmed floor) | 31 | **FAIL** (−3 below floor) |
| G3 | FP ≤ 30 AND FN ≤ 1 | FP 35, FN 0 | **FAIL** (FP +5) |
| G4 | 0 running AND 90/90 valid | 0 running, 90/90 | **PASS** |
| G5 | R126-TP retention ≥ 32/34 | Strict fell to 31 → retention < 32 | **FAIL** |

**KEEP** required FP<30 with Strict≥34, **or** Strict≥37 with FP≤30 & FN≤1. R128 (Strict 31, FP 35)
satisfies neither. G2/G3/G5 fail. → **REVERT.**

## Why this is not attributable to the mechanism (the decisive finding)

`reduce_json` was **adopted in exactly 2 of 90 cases** — M16 and M17, one accepted call each
(verified: `data.operation=="reduce_json"` with `wire_command_digest`, and
`temp_decision.result_summary=="reduce_json"` which is set only on an accepted call, `model.py:370`).
The **88 other cases never used it**, so their behaviour is identical to R126 source
(`_assignment` byte-identical to R126; `chunks.py`/`model_io.py`/`model_session.py` byte-identical).
R128 is therefore effectively a **third independent sample of the R126 architecture**:

```
R126 architecture Strict samples: 36 (R126 official), 34 (R126 confirmatory), 31 (R128) → mean ~33.7, range 31–36
R126 architecture FP     samples: 30,               31,                     35            → mean ~32,   range 30–35
```

Both spreads are exactly the stated ±3 single-run variance. R128's 31/35 sits at the low-Strict /
high-FP edge of that band — noise, not a mechanism effect.

**And where the fold WAS used, it did not help:**

| case | R126 | R128 (fold used) | reading |
|---|---|---|---|
| M16 (reads 10 per-id files) | FP (echoed input layout) | **FP** `completed external=False` | fold did not break the shape-echo → **protocol risk (b)**: the uniform envelope became just one more adjacent blob to echo at the write turn |
| M17 | not in R126's 30-FP set (FN=0 → TP or OTHER) | **OTHER** `interrupted` | the extra fold step consumed budget / destabilized completion → **protocol risk (c)**; a TP→OTHER regression if M17 was a R126 TP |

So the only two cases carrying the variable show it to be **neutral-to-harmful**: 0 helpful flips, 1
completion regression. Protocol risks (a) low-adoption, (b) envelope-as-new-echo, and (c)
completion-destabilization **all materialized** in the tiny adopted set.

> A full per-case R126→R128 flip matrix is not reconstructable: R126's per-case `cases/` were pruned
> after that round (only its REPORT.md + MANUAL_CAUSAL_ANALYSIS.md survive). This does not affect the
> verdict — with 2/90 adoption and 0 helpful flips, the aggregate movement is definitionally variance.

## Revert (executed, verified byte-exact)

- `rwkv_lh/model.py` restored to `baseline/round126-v19p1` — sha256
  `399bf5225ef384d98e4994246aa0c1e6460f177fd836820caec70d7b57ff0212` ✔ identical.
- `rwkv_lh/harness.py` restored to `baseline/round126-v19p1` — sha256
  `1bb75f457bc033d8f27ac0f45159b0138d69c7435639090867feb6fffd46d252` ✔ identical.
- `tests/test_reduce_json.py` → quarantined to `temp/quarantined_tests/`.
- `pytest -q` → **107 passed** (back to pre-R128 count); `compileall rwkv_lh` clean.
- No commit (REVERT). Baseline remains R126.

## Lesson carried forward

An **optional** read-time fold offered as a tool is the wrong delivery: the model almost never adopts
it (2/90), and when it does, the lossless envelope is itself an echoable adjacent shape. If the fold
mechanism is to be retried (R129+), it must be **structurally induced** — the harness folds
homogeneous observations automatically so the write turn *cannot* see the per-item tail — not offered
as a choice the continuation model declines. Recorded in the R132 candidate pool as
"hierarchical reduce (structurally induced, not an optional tool)".
