# Round128 v19-P3 — Manual Causal Analysis

## Hypothesis under test
Multi-read STRUCT-echo FP arise because N homogeneous read results accumulate in the append tail and
the write turn reconstructs the output contract from the **adjacent (last-read) blob's shape** instead
of from the request spec. A model-executed read-time fold (`reduce_json`) that collapses the N
homogeneous files into ONE lossless scratch envelope should remove the dominant per-item input shape,
forcing the model to consult the request contract at write time → flip multi-read STRUCT FP to TP.

Preregistered reachable slice: the ~8 multi-read STRUCT FP (H06, LH06, M01, M15, M16, M22, M26, M29).
Preregistered honest ceiling: single-read echo (M04, M25, M08, B16) and rollover FP (LH10, LH12, M01)
structurally out of reach.

## What actually happened
`reduce_json` was **adopted in 2/90 cases (M16, M17)** and **helped in 0**. The mechanism therefore
never got a fair test at population scale — but the two data points it did produce, plus the
whole-run variance, are jointly decisive.

### 1. Adoption failure (protocol risk (a)) — the dominant effect
The prime targets did **not** invoke the fold despite reading many homogeneous files:
- M01 (10 reads), H06 (3), LH06 (multi), M15 (3), M22 (3), M26 (2), M29 (2) — none folded.
- Only M16 (10 reads) and M17 folded, once each.

The continuation model, offered the fold as **one option among 18**, overwhelmingly kept doing what
it already does (read → write). An optional tool does not change the geometry the model actually
follows; it just adds a branch the model declines. This is the same class of finding as R121 (a
mechanism that is individually inert when not structurally forced).

### 2. Where it fired, it was neutral-to-harmful (risks (b) and (c))
- **M16 — FP → FP.** The model folded 10 files into the `read-time-fold.v1` envelope, then at the
  write turn still produced output keyed by the folded layout. The envelope
  `{reduce_schema, count, reduce_digest, sources:[{source_ref, value}, …]}` is *itself* a salient
  homogeneous container — exactly the shape M25 showed the model readily echoes. So the fold moved
  the echo source from "10 files" to "one `sources[]` array" without removing the echo. **Protocol
  risk (b) confirmed:** the uniform envelope became a new echo source.
- **M17 — (R126 non-FP) → OTHER `interrupted`.** Adding the fold as an extra step before the write
  turn pushed this case into non-termination. Whether M17 was a TP or OTHER in R126, the fold did not
  produce a TP and introduced an interruption. **Protocol risk (c) confirmed:** the extra step
  destabilized completion.

### 3. Whole-run numbers are a variance sample of R126
Because 88/90 cases ran identical-to-R126 source, R128's {Strict 31, FP 35, FN 0, OTHER 24} is a
third R126 sample. Across the three R126-equivalent runs Strict = {36, 34, 31} and FP = {30, 31, 35}
— both ranges = the stated ±3 variance. There is **no signal** attributable to `reduce_json` in the
aggregate; attempting to read the −5 Strict / +5 FP as a mechanism effect would be the falsified-
hypothesis error the program's gates exist to prevent.

## Root cause of the mechanism's failure
The read tail is immutable causal history (R123), so the fold had to be model-executed at read time.
But the fold's value depends on the model **choosing** to fold **and** then **not** echoing the fold
product — two behaviours a strong continuation model with no endogenous stop/contract criterion will
not reliably exhibit when the fold is merely *available*. The geometry has to be imposed, not
offered.

## Consequences for the program
- **R128 REVERT** (byte-exact restore verified; see REPORT.md). Baseline remains R126.
- **R129+ direction:** if hierarchical reduce is retried, make it **structurally induced** — the
  harness auto-folds the Nth homogeneous read so the write turn cannot see the per-item tail, and the
  fold product is presented in a form that is *not* itself an echoable container (e.g. a digest +
  count, not a `sources[]` array). Otherwise pick a different positional-bias mechanism
  (order-permutation ensembling) that does not rely on the model electing an extra step.
- **R132 (组合最优冲纪录轮):** `reduce_json` is **EXCLUDED** from the terminal combination — it fails
  eligibility E2 (never usefully fired) and shows a completion regression (E1 risk). Recorded in the
  R132 candidate ledger.

## Governing principles touched
- [[fixed-state-adjacency-principle]]: an optional operation adjacent to nothing changes no geometry.
- [[rwkv-creator-order-ensembling-advice]]: hierarchical reduce is sound **only** when the reduction
  is imposed on the observation stream, not left to the model's discretion.
