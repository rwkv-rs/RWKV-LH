# R130 canonical-default repair — Full90 validation

**Run:** `R130_canonical_repaired_full90_20260820`  
**Started:** 2026-08-20 21:49:11 CST  
**Finished:** 2026-08-21 00:50:42 CST  
**Disposition:** **PASS — the R130 order-ensemble experiment is no longer active on canonical runtime paths.**

This is a repair validation, not a second R130 KEEP attempt. The R130 K=3 result remains a REVERT;
the order-ensemble mechanism is retained only behind explicit opt-in for its dedicated tests.

## 1. Root cause and repaired boundary

R130 introduced order-shuffled K=3 self-consistency as a one-round experimental variable. The
implementation was active in the generic `LongHorizonModel` construction path, while the production
runner, CLI, web worker, and Controller fallback all instantiate `LongHorizonModel` without an R130
argument. The experimental variable therefore leaked into the default architecture instead of being
scoped to R130.

That leak was semantically significant, not only a performance issue: after the first history pair,
one logical decision generated three physical RWKV continuations and a vote could replace the
canonical continuation. In the completed R130 run, 2,967 logical decisions generated three physical
candidates and only 1,338 generated one, for 10,239 physical model requests in total.

The repair makes `enable_order_ensemble=False` the constructor default. Production constructors keep
the default; the three R130-aware deterministic fixtures explicitly pass
`enable_order_ensemble=True`. Frozen source-manifest comparison shows exactly four changed files:

- `rwkv_lh/model.py` — introduce the disabled-by-default boundary and canonical single-generation
  path;
- `tests/test_round119_fact_integrity.py` — explicit R130 opt-in in its ensemble fixture;
- `tests/test_round130_order_ensemble.py` — explicit R130 opt-in;
- `tests/test_unified_controller.py` — explicit R130 opt-in in its ensemble fixture.

Repository-wide construction-path inspection confirms that `scripts/run_rwkv_e2e_benchmark.py`,
`scripts/run_long_horizon.py`, `rwkv_lh/web_worker.py`, and the Controller fallback do not opt in.

## 2. Frozen run and validity

- Suite: RWKV-E2E-90, 90 fixed cases, concurrency 1, max transitions 200.
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`.
- Sampling: temperature 0.05, top-p 1.0, top-k 0, presence/frequency penalty 0,
  penalty decay 0.996; prompt replay.
- Source manifest: 55/55 frozen source entries rehashed after the run with zero mismatch.
- Case artifacts: 90/90 `audit.json` files present.
- Runner integrity: zero `failed` states, zero nonempty runner failures, and 90/90 delivered Finals
  match the selected raw RWKV output.
- Byte-precision gate: B01, B06, B13, B19, B28 = **5/5**.

The R130 protocol records single-run Strict variance as ±3. The repaired canonical run scores 35,
between the unchanged canonical R126 official score 36 and its confirmatory score 34. Its group shape
is also adjacent to R126: repaired `{B 23, M 9, H 2, LH 1}` versus R126 official
`{B 23, M 10, H 2, LH 1}`. This satisfies the preregistered similarity scale for restoration of the
canonical path; it does not re-evaluate or KEEP the disabled R130 variable.

## 3. Full90 comparison

| Metric | R130 order ensemble | Canonical repaired | Delta |
| --- | ---: | ---: | ---: |
| Strict / TP | 33 | **35** | +2 |
| Agent completed | 64 | **64** | 0 |
| Interrupted | 26 | **26** | 0 |
| FP | 31 | **29** | -2 |
| FN | 1 | **0** | -1 |
| OTHER | 25 | **26** | +1 |
| Physical model requests | 10,239 | **2,844** | -7,395 (-72.2%) |
| Executed actions | 3,987 | **2,494** | -1,493 (-37.4%) |
| Cases with >=50 requests | 31 | **15** | -16 |
| Cases with >=200 requests | 18 | **6** | -12 |
| Maximum requests in one case | 562 | **202** | -360 |
| Protocol rejections | 216 | 248 | +32 |

Generation audit is decisive: the repaired run has **2,844/2,844 decisions with
`generation_count=1` and zero K=3 decisions**. The old run has 1,338 single-generation decisions and
2,967 K=3 decisions; `1,338 + 3 * 2,967 = 10,239` physical requests exactly.

### First 18 cases (the takeover checkpoint)

| Metric | R130 order ensemble | Canonical repaired |
| --- | ---: | ---: |
| Strict | 12 | 12 |
| Agent completed | 16 | 15 |
| Interrupted | 2 | 3 |
| Model requests | 909 | **131** |
| Actions | 296 | **83** |
| Maximum per-case requests | 562 | **21** |
| Cases with >=50 requests | 3 | **0** |

The identical Strict score with a 85.6% request reduction demonstrates that the early difference is
removal of the K=3 amplification, not a scoring or acceptance change.

### Outcome churn (old row -> repaired column)

|  | TP | FP | FN | OTHER |
| --- | ---: | ---: | ---: | ---: |
| old TP | 30 | 2 | 0 | 1 |
| old FP | 3 | 25 | 0 | 3 |
| old FN | 1 | 0 | 0 | 0 |
| old OTHER | 1 | 2 | 0 | 22 |

The repaired score is inside canonical variance and restores the canonical group signature. Individual
case flips remain stochastic at temperature 0.05 and are not attributed to a new architecture lever.

## 4. Resource-stability evidence

The run used one spawned case worker with `max_tasks_per_child=1`, systemd `MemoryHigh=12G`, and
`MemoryMax=16G`. Long 200-transition cases build large SQLite/audit snapshots and temporarily reached
the 12 GB high watermark; the service reported a 12.0 GB memory peak and 4.0 GB swap peak. Each such
case nevertheless completed export, the worker PID changed, and memory fell back before the next
case. The run reached 90/90 without a WSL restart, process-pool failure, missing audit, or resumed
case. This confirms the worker-recycle amendment fixes cross-case retained heap; it does not eliminate
the per-case audit-export peak.

The benchmark executable returns exit status 2 when any cases fail. The transient systemd unit had an
on-failure restart policy, so after the valid 90/90 result it briefly retried and correctly failed
closed on the existing output directory. The unit was stopped/garbage-collected; no artifact was
overwritten. Future benchmark units should use `Restart=no` or treat exit 2 as an expected scored-run
exit to avoid this harmless restart loop.

## 5. Offline regression evidence

- `python -m compileall -q rwkv_lh` — PASS.
- Focused repair/ensemble/controller suite — **28 passed**.
- Full repository suite — **114 passed**.
- Frozen source-manifest rehash — PASS.
- Full90 audit count — **90**.

The first pytest invocation inherited Windows `TEMP`/`TMP` paths inside WSL and lost pytest's capture
file before collection; no test ran. Re-running with `TMPDIR`, `TMP`, and `TEMP` fixed to the project
`temp/` directory produced the 28/28 and 114/114 results above.

## 6. Conclusion and remaining scope

The system-wide defect is repaired: canonical runtime paths make one RWKV decision per transition,
while R130 K=3 remains explicit and testable without silently replacing the RWKV canonical spine.
Full90 quality returned to the preregistered canonical variance band and byte precision stayed 5/5.

Residual canonical failures remain real model/architecture work: 29 completed-but-wrong cases and 26
OTHER/interrupted cases, concentrated in hard and long-horizon tasks. Six cases still reached roughly
200 requests, and several hard cases exhausted the 12-rejection budget. They are not resource crashes
and are not repaired by re-enabling ensemble; any future change must be a separately preregistered
RWKV-state/decision-path intervention on the fixed dataset and scoring protocol.
