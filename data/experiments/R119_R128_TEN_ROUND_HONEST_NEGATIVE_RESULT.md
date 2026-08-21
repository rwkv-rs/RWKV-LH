# R119–R128 — Ten-Round Program: Honest Negative Result

**Scope:** the original preregistered `/goal` — "at most ten rounds, Round119–Round128," improve
only the harness/architecture (model, benchmark, official v1 scoring, datasets, frozen parameters all
unchanged) to achieve a source-frozen full-90 with **Strict>31 ∧ FP≤24 ∧ FN≤1 ∧ 90/90 valid ∧ 0
running**, then a confirmatory full-90 at the same thresholds, then a git checkpoint.

**Outcome: the ten-round terminal `/goal` was NOT met.** All ten rounds are complete. This is the
honest negative result the goal requires at the ten-round mark.

---

## 1. Terminal-threshold status (best achieved = Round126)

| Threshold | Target | Best (R126 official) | Met? |
|---|---|---|---|
| Strict | > 31 | **36** | ✅ |
| FP | ≤ 24 | **30** | ❌ (gap −6) |
| FN | ≤ 1 | **0** | ✅ |
| 90/90 valid, 0 running | yes | yes | ✅ |
| confirmatory at same thresholds | yes | Strict 34, FP 31, FN 0 | ❌ (FP) |

**Two of three metric thresholds are met; FP≤24 is the sole, decisive blocker.** R126 is a genuine
**new historical best on Strict (36 > R46's 31) and FN (0 ≤ 1)** and was committed locally to
`baseline/round126-v19p1` (commit 50754a2; owner pushes). But it does **not** dominate R46
(Strict 31, FP 24, FN 1): it trades **+5 Strict for +6 FP**. The composite "beat R46 on all three at
once," which the terminal criteria encode, was not reached.

---

## 2. Complete round ledger (R119–R128)

| Round | Change (one variable) | Strict | FP | FN | Verdict | Decisive finding |
|---|---|---|---|---|---|---|
| R119 | fact-integrity architecture (v18 baseline) | 30 | 36 | 0 | **KEEP** | append-only growing transcript is the viable spine; established baseline |
| R120 | step-index + projection scaffolding | 22 | — | — | REVERT | step echo → repetition attractor |
| R121 | repetition guard | 27 | — | — | REVERT-by-rule | guard quality-neutral (−43% tokens); losses were ±3 noise |
| R122 | guard retest | ~27 | — | — | REVERT | guard dead as standalone; only decoding divergence could help |
| R123 | rebuilt working set each turn | 0/29 | — | — | **INVALID/ABORTED** | prompt_replay rebuild = deterministic fixed-point at temp 0.05 (input(t+1)≈input(t) → identical output forever); every case looped to the 200 ceiling |
| R124 | stuck-escalation sampling (temp↑) | 27 | 42 | 0 | REVERT | **temperature is the WRONG layer**: INTR→TP = 0; escalation broke success-loops but they landed FP, never TP |
| R125 | per-turn spec re-injection + "verify before completing" | 12 | 4 | 19 | REVERT | completion collapse: a 2nd decision (TP→FN ×14) + homogeneous per-turn duplicate (→OTHER ×33) |
| **R126** | **bootstrap request-last adjacency** (immutable_request LAST inside JSON, sort_keys off) | **36** | **30** | **0** | **KEEP — new best** | cost-free key reorder; +6 Strict; FP→TP ×5 incl. M06 (the positional-bias signature case) |
| R127 | request lifted OUT of JSON into trailing prose | 30 | 25 | 4 | REVERT | completion collapse: adjacent-but-**open** → model never terminates (B06/B02 ran 15–16 reqs for 2–3-action tasks); FP drop is a *shadow* of not completing |
| R128 | optional read-time fold `reduce_json` (18th op) | 31 | 35 | 0 | REVERT | **2/90 adoption, 0 helpful flips**; envelope became a new echo source; whole-run = a 3rd R126 variance sample |

---

## 3. Flip history (the causal chain)

- **R119→R126** (the only KEEP→best path): FP→TP ×5 (B11, B17, LH09, M03, **M06**), OTHER→TP ×2
  (M21, M24), TP→FP ×1 (LH10, within ±3). R119-TP retention 29/30.
- **R126→R127**: FP→TP ×2 genuine (B05, B29) but **FP→OTHER ×9** and **TP→FN ×4** — the FP fall was
  completion collapse, not correctness. Completed-Final population 66→55.
- **R126→R128**: `reduce_json` fired only in M16 (FP→FP) and M17 (→OTHER/interrupted); 88/90 cases
  ran R126-identical source. Strict samples across the three R126-equivalent runs = {36, 34, 31},
  FP = {30, 31, 35} — both exactly the ±3 single-run variance.

**Single-run Strict variance is ±3** (measured, not assumed). Every KEEP/REVERT was decided on
causal attribution (did the changed variable actually fire and flip the targeted cases), never on a
raw score delta — this is what kept the program out of the R47–R77 symptom-chasing death spiral.

---

## 4. Falsified hypotheses (durable negative knowledge)

1. **Step-index / progress scaffolding helps** — NO (R120): step echo becomes a repetition attractor.
2. **Repetition penalties/guards improve quality** — NO (R121/R122): quality-neutral; only token cost.
3. **A compact working set can be rebuilt each turn under prompt_replay** — NO (R123): near-greedy
   decoding over an unchanging rebuilt input is a deterministic fixed-point. **Append is mandatory.**
4. **Sampling temperature/escalation is the lever for stuck loops** — NO (R124): INTR→TP = 0. The
   loop is a *symptom* of "the model does not know the correct deliverable," not a decoding defect.
5. **Re-injecting/re-emphasizing the request each turn aids completion** — NO (R125): catastrophic
   collapse. Adding any second decision or homogeneous per-turn duplicate destroys completion.
6. **Making the request structurally *more prominent* (lift it out of the JSON) helps** — NO (R127):
   adjacent-but-open → the model never calls final_answer. **Request-placement is CLOSED; R126's
   request-last-inside-JSON is optimal.**
7. **An optional, model-elected read-time fold reduces multi-read shape-echo FP** — NO (R128):
   2/90 adoption; the lossless envelope is itself an echoable container. A fold must be
   **structurally induced**, not offered.

**Confirmed positive:** (a) append-only growing transcript is the only viable spine; (b) request-last
adjacency inside the JSON is the single largest Strict lever discovered (+6, cost-free); (c) both
governing principles hold — [[fixed-state-adjacency-principle]] and
[[rwkv-creator-order-ensembling-advice]] (R126 confirmed positively; R125/R127 confirmed negatively).

---

## 5. Why FP≤24 was not reached, and whether it is reachable

Anatomy of R126's 30 FP: **~15/30 are single-read echo** (incl. M04, M25, M08, B16 — the model
reconstructs the deliverable from a single adjacent blob/target path; no homogeneous tail to fold,
no permutation to vote over → structurally out of reach of fold/ensemble/decompose); **3/30 roll
over** (fold-time dead); **~8/11 are multi-read STRUCT-echo** (H06, LH06, M01, M15, M16, M22, M26,
M29 — the model echoes the collective layout of N homogeneous reads). Only that last ~8-case slice
is mechanistically reachable.

**Arithmetic of reachability:** flipping the ~8 multi-read STRUCT FP to TP would bring FP to ~22
(≤ 24) while raising Strict — i.e. FP≤24 **is** in principle reachable *if and only if* that specific
class can be flipped. R128 proved the *optional-tool* delivery cannot do it; the remaining open
mechanisms are **structurally-induced hierarchical reduce** and **order-permutation ensembling**,
neither of which relies on the continuation model electing an extra step.

> **Correction (2026-08-17, from the R128 full-90 trace mining that opened R129 — see
> `Round129_BOOTSTRAP_HOMOGENEOUS_DECOMPOSITION_PROTOCOL.md` §7):** the "~8 reachable → FP 22"
> estimate above was **too optimistic**. Read-only mining of the 8 cases (public request + model's
> own outputs) resolves them into four subtypes: 3 OVER-STRUCTURE (H06, M01, LH06), 1 FIELD-MERGE
> (M16), **2 pure data-logic errors (M22, M26 — out of reach)**, and **2 already shape-compliant
> (M15, M29 — out of reach)**. The reachable slice is therefore **~3–4, not 8**; even flipping all
> four leaves **FP ≈ 26 > 24**. Moreover **hierarchical reduce is falsified for this class** — M16
> actually folded (`reduce_json`) and still produced the wrong envelope. The dominant failure is
> prose-contract → JSON-envelope translation at a deep write turn, whose fix (the target output
> shape) is red-lined (no task-text parsing, no contract injection). **FP≤24 is now assessed as
> likely unreachable by any single admissible bootstrap-side mechanism.** R129–R131 continue as
> mechanism screens / negative knowledge, not as an expected path to the terminal threshold.

---

## 6. Disposition

- **Original ten-round `/goal`: terminal success NOT achieved.** Honest negative result recorded.
  Best architecture = **R126** (`baseline/round126-v19p1`), a new Strict/FN historical best but
  FP 30 > 24. Source is at R126 baseline, byte-verified; 107 tests green; nothing running.
- **Owner-authorized follow-on (separate mandate, 2026-08-16 / 2026-08-17):** the program was
  extended to **R129–R131** (single-variable screens of the reachability mechanisms above) **→ R132**
  (组合最优冲纪录轮, terminal combination). That continuation targets exactly the ~8-case multi-read
  STRUCT slice that arithmetic §5 shows is the only path to FP≤24. It is preregistered
  (`Round132_TERMINAL_COMBINATION_RECORD_ATTEMPT_PROTOCOL.md`) but is **not** part of satisfying the
  original ten-round goal — it is a new attempt beyond it.
