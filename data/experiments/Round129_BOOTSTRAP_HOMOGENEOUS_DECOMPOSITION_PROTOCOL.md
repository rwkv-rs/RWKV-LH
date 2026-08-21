# Round129 — Bootstrap Homogeneous-Item Decomposition — PROTOCOL (preregistered)

**Status:** preregistered 2026-08-17, **before the R129 full-90 runs**, derived from the R128 full-90
trace evidence per the R121+ rule ("each architectural change must be derived from the previous
round's full-90 flip matrix and trace evidence, not a predefined backlog"). Baseline = **R126 v19-P1**
(`baseline/round126-v19p1`; official {Strict 36, FP 30, FN 0}; confirmatory {Strict 34, FP 31, FN 0};
single-run Strict variance ±3). This is the **11th round** of the program (R119–R132) and the first of
the three single-variable screens (R129/R130/R131) that feed the terminal combination round R132.

---

## 0. Evidence this round is derived from (R128 trace mining, all 8 multi-read STRUCT FP)

R128 reverted (fold `reduce_json` adopted 2/90, 0 helpful flips). Its decisive value was the trace
mining of the **reachable FP slice** — the ~8 "multi-read STRUCT-echo" FP that §5 of
`R119_R128_TEN_ROUND_HONEST_NEGATIVE_RESULT.md` named as the only mechanistically reachable path to
FP≤24. Read-only mining (public `tasks.json` request + each case's `event_log.json` + written
`workspace/` artifact; **no** `.verifier-private`/acceptance) resolves that "class" into **four
distinct subtypes**:

| Subtype | Cases | #reads | Reachable by a bootstrap-side change? |
|---|---|---|---|
| **A OVER-STRUCTURE** (added wrapper/echoed fields beyond the contract) | H06, M01, LH06 | 3, 3, 8 | **plausibly** — the target slice |
| **B FIELD-MERGE** (folded two required top-level fields into one) | M16 | 6 | partly — but see below |
| **F DATA-WRONG** (correct envelope, wrong business logic) | M22, M26 | 3, 2 | **no** — model logic error, out of reach |
| **G compliant** (shape already satisfies prose) | M15, M29 | 3, 2 | **no** — path-relativity / flat-vs-nested nuance |

Two findings that **redirect** the round away from the R128 "structurally-induced fold" lesson:

1. **A fold is falsified for this class.** M16 is the *only* case that folded (`reduce_json`) and it
   **still** produced the wrong envelope — an id-keyed `{id,source,value}` object instead of the
   requested separate `items` array + `sources` map; the fold's `{source_ref,value}` children *leaked*
   into the output. Compaction does not perform the missing step (prose-contract → JSON-envelope
   projection). The "structurally-induced fold" R129-candidate from the R128 lesson is therefore
   **dead** and is NOT what this round tries.

2. **The reachable slice is smaller than the honest-negative-result estimated.** §5 assumed ~8
   reachable → FP 22 (≤24). Corrected: 2 are pure data-logic (M22, M26 — out of reach), 2 are already
   compliant (M15, M29 — out of reach), leaving **~3–4** (A + M16). Even flipping **all four** →
   FP ≈ 26, **still > 24**. See §7 for the revised reachability arithmetic. **R129 is a mechanism
   screen for R132 eligibility, NOT itself expected to reach terminal FP≤24.**

**Dominant real failure = prose-contract → JSON-envelope translation at a deep write turn.** The
missing ingredient is the *target output shape*, which the red lines forbid me from supplying (no
task-text parsing for required keys, no contract injection). The single lever *adjacent* to the write
turn — the last observation — cannot be reshaped without destroying byte-precision (B01/B06/B13/B19/
B28 need raw bytes in the observation; observation-projection is **disqualified**, gate G1). Every
remaining admissible lever acts on the **bootstrap** (`_assignment`, rendered once at turn 1). This
round screens the strongest such lever.

---

## 1. The one variable (single-variable round)

**Variable: bootstrap homogeneous-item decomposition of `_assignment`.**

Enacts the still-unused RWKV-creator "homogeneous-item decomposition" mechanism and the owner's
first-principle decomposition rule (*"尽量拆细，尽量不要多个特别是同质的信息混杂"* /
[[fixed-state-adjacency-principle]]: minimal competing info, literals nearest the continuation point).

**Current (R126) `_assignment`** returns a single JSON object whose fields mix two *homogeneous lists*
into the same block the model completes from:

```
{"protocol":…,"constraints":[…],
 "workspace_manifest":[…file-entry objects…],
 "recent_exact_action_records":[…action objects with nested result objects…],
 "instruction":…,"immutable_request":<request>}      ← request LAST (R126 adjacency)
```

**R129 change:** split the two homogeneous lists **out** of the terminal JSON into separate,
clearly-labeled blocks placed **above** a compact terminal JSON, while keeping the terminal JSON
**closed** and `immutable_request` its **last** field (R126 adjacency invariant preserved):

```
workspace_manifest:
<canonical_json(manifest)>

recent_exact_action_records:
<canonical_json(recent_actions)>

{"protocol":"single-rwkv-direct-action.v2","constraints":[…],"instruction":…,"immutable_request":<request>}
```

Nothing is added, removed, or reworded in the **content** — the manifest, records, constraints,
instruction, and request bytes are identical to R126; **only their grouping/placement changes** (the
same cost-free class of change as R126's key reorder). `protocol` bumps to `.v2` to mark the wire
shape.

**Invariants deliberately preserved (to avoid known collapse modes):**
- **R126 request-last adjacency:** `immutable_request` remains the last field of the last (terminal)
  closed JSON block → nearest the `Assistant: ```json` continuation point. UNCHANGED.
- **R127 completion geometry:** the request stays **inside a closed JSON object** (adjacent-but-
  *closed*). The decomposed blocks are context placed *above*, never adjacent to the continuation
  point, so they cannot reproduce R127's "adjacent-but-open → never terminates" collapse.
- **No second decision** (R125 failure mode): no verify step, no added directive.
- **No per-turn re-injection** (R125 failure mode): still a turn-1 bootstrap only; append transport
  and `render_event_append` are untouched.
- **Byte-precision safe:** `_assignment` carries file *metadata*, never file *content* (that arrives
  in Function-output observations, untouched) → G1 cannot regress from this change.

## 2. Hypothesis (falsifiable)

The model's output "house style" (nesting depth, wrapper usage) is primed by the most salient JSON
structures in context. Removing the two nested homogeneous lists from the terminal JSON the model
completes from leaves a **flat** terminal object, lowering the "produce nested wrapper objects" prior
and reducing OVER-STRUCTURE FP (H06, M01, LH06; possibly M16 now that `reduce_json` is reverted and
its fold-envelope echo source is gone).

**Honest weak-link caveat (recorded pre-run):** the OVER-STRUCTURE FP occur at a **deep write turn**,
far below the bootstrap where this lever acts; the effect is therefore expected to be **attenuated**
and primarily to influence turn-1 planning and early house-style. A null result is a real
possibility and would be logged as negative knowledge, not massaged. Predicted **maximum** reachable
= the 3 OVER-STRUCTURE cases (+M16 = 4); predicted terminal outcome = **does not reach FP≤24** (§7).

## 3. Prediction (pre-registered, checked against the flip matrix after the run)

- **Helps (FP→TP):** among {H06, M01, LH06, M16}. ≥1 attributable flip ⇒ E2-eligible for R132.
- **No effect:** M22, M26 (data-logic), M15, M29 (compliant), and single-read echo FP
  (M04, M25, M08, B16 — no homogeneous bootstrap structure implicated).
- **Must not regress:** completion (FN, OTHER), byte-precision (5/5), R126-TP retention.

## 4. KEEP / REVERT gates (preregistered, baseline R126)

- **G1 byte-precision == 5/5** (B01,B06,B13,B19,B28 completed + external pass). *(Structurally
  guaranteed unaffected — the change never touches observation content — so any G1 regression is a
  red flag of an unintended interaction and forces REVERT.)*
- **G2 Strict ≥ 34** (R126 confirmed floor; no completion regression).
- **G3 FP ≤ 30 AND FN ≤ 1** (improvement direction is FP↓; FP must not rise).
- **G4 0 running AND 90/90 valid Finals.**
- **G5 R126-TP retention ≥ 32/34** (guards TP→FP/FN/OTHER churn).

**KEEP** iff FP < 30 with Strict ≥ 34 (FN ≤ 1), **or** Strict ≥ 37 with FP ≤ 30 (FN ≤ 1) — i.e. a
genuine dominance-direction improvement over R126 attributable to the decomposition (variable
actually changed the wire shape **and** ≥1 attributable FP→TP flip). Otherwise **REVERT** byte-exact
to `baseline/round126-v19p1`.

**Attribution rule (anti-variance):** because single-run Strict variance is ±3, a raw score delta is
**not** sufficient for KEEP. KEEP requires the flip matrix to show the decomposition *caused* the
improvement (≥1 OVER-STRUCTURE FP→TP with the wire shape confirmed changed), never a bare aggregate
move within the ±3 band (the R128 mistake this program's gates exist to prevent).

## 5. Offline gate (all must pass before freeze)

- `pytest -q` → all green (baseline count; update any test that asserts the exact `_assignment`
  byte shape, since the wire format changes by design — the test must assert the *new* invariant:
  request-last, terminal JSON closed, manifest/records decomposed above).
- `python -m compileall rwkv_lh` → clean.
- e2e catalog → **90/90** (core30 30 + lh12 12 + extension48 48).
- registry / `_validate_registry` clean; definitions↔handlers bijective (unchanged — no op touched).
- **Render-diff check:** dump the rendered bootstrap for a sample goal under R126 vs R129 and confirm
  (a) `immutable_request` is the last field of the last closed JSON block in both; (b) only the
  manifest/records grouping differs; (c) no `\n\nUser:`/`\n\nSystem:`/`\n\nAssistant:`/```` \n``` ````
  stop-sequence substring is introduced by the new block separators.
- source isolation → only `rwkv_lh/model.py` (and its test) differs from `baseline/round126-v19p1`;
  everything else hash-equal.

Then freeze the read-only source manifest
(`temp/generate_round129_source_manifest.py`, `--check` for read-only verify).

## 6. Run (frozen parameters, unchanged)

model `rwkv7-g1i-13.3b-20260805-ctx16384`; endpoint `http://127.0.0.1:29610/v1` (Bearer `rwkv-skills`);
temp 0.05 / top_p 1.0 / top_k 0 / presence 0 / frequency 0 / penalty_decay 0.996; max-transitions 200;
concurrency 1; max_model_len 16384; transport `prompt_replay`; max_output_tokens 1800 action / 1400
terminal. Runner: `scripts/run_rwkv_e2e_benchmark.py --suite all`
(`RWKV_BASE_URL=http://127.0.0.1:29610/v1 RWKV_API_KEY=rwkv-skills`). Then REPORT.md +
MANUAL_CAUSAL_ANALYSIS.md with the full R126→R129 flip matrix; KEEP/REVERT per §4.

## 7. Revised reachability arithmetic (supersedes §5 of the honest-negative-result doc)

The honest-negative-result doc estimated ~8 reachable multi-read STRUCT FP → FP 22 (≤24). The R128
trace mining corrects this:

- **Out of reach (no admissible lever):** M22, M26 (data-logic), M15, M29 (compliant), plus the
  ~15/30 single-read echo and ~3/30 rollover FP already noted.
- **Plausibly reachable (this round's target):** H06, M01, LH06 (OVER-STRUCTURE) + M16 (FIELD-MERGE)
  = **≤4**.
- **Best case if R129 flips all 4:** FP 30 → **≈26**, Strict ↑ — **still > 24**.

**Consequence for the program:** FP≤24 is **not reachable by a single admissible bootstrap-side
mechanism**, because the dominant failure is a deep-write-turn contract-translation whose fix (the
target shape) is red-lined. R129–R131 remain worth running as **E1/E2 screens** for the R132
combination and as durable negative knowledge, but the terminal /goal (FP≤24 + confirmatory) is now
assessed as **likely unreachable** without relaxing a red line. This assessment is recorded pre-run
so it cannot be retrofitted to whatever R129 produces.

## 8. Red lines (unchanged)

No threshold/scoring edits post-run; no per-case special-casing; no reading hidden acceptance
(`.verifier-private`, `*.acceptance.json`, `codex_reference_answers.json`); no reviewer/judge; no
parsing task text for required keys; no guessing missing semantic parameters; Controller never
rewrites Finals; raw Final preserves the model's original bytes; transport stays `prompt_replay`; no
`--no-verify` unless explicitly instructed; no push (owner pushes on a KEEP that beats baseline).
