# Round130 — Order-Shuffled Self-Consistency (full per-turn K=3) — PROTOCOL (preregistered)

**Status:** preregistered 2026-08-18, **before the R130 full-90 runs**, derived from the R129 full-90
trace evidence + the standing RWKV-creator advice ([[rwkv-creator-order-ensembling-advice]]). Baseline
= **R126 v19-P1** (`baseline/round126-v19p1`; official {Strict 36, FP 30, FN 0, OTHER 24};
confirmatory {Strict 34, FP 31, FN 0}; single-run Strict variance ±3). This is the **12th round** of the
program (R119–R132) and the second of the three single-variable screens (R129/R130/R131) that feed the
terminal combination round R132. **Owner directive 2026-08-18:** implement the *full* faithful
per-turn K=3 order-ensemble (accepting ~3× compute), not the minimal within-observation form.

---

## 0. Evidence this round is derived from

- **R129 (homogeneous decomposition) REVERT** established that any *bootstrap* restructuring collapses
  completion (Strict 36→28); the `_assignment` wire shape is CLOSED on all three axes (key order R126,
  request placement R127, object grouping R129). → the next admissible lever must NOT touch the
  bootstrap; it must act on the **decode/decision path**.
- The residual R126 FP (≈30) was diagnosed across R126/R127 as **whole-transcript positional bias**
  ("the model attends to the front/back items and drops the middle"), NOT a request-location problem.
  M06 is the signature case: a late-read item polluted the manifest.
- The RWKV creator's flagship remedy for exactly this failure is **order-permutation parallel
  ensembling**: fixed-state models have front/back positional bias because items have only ONE
  ordering; generate with multiple orderings in parallel and aggregate. This mechanism was **drafted
  as R125** (`Round125_V18P6_ORDER_SHUFFLED_SELF_CONSISTENCY_PROTOCOL.md`) but never run (R125 became
  the spec-adjacency anchor). It has therefore **never been screened.** R130 screens it.

The R125 draft assumed the R123 rebuilt-working-set as a prerequisite; R123 was aborted (deterministic
fixed-point). This protocol **re-hosts** the mechanism on the live **R126 append-transcript** spine.

---

## 1. The one variable (single-variable round)

**Variable: per-decision order-shuffled self-consistency, K=3, on the append transcript.**

At every action-lane decision point, instead of one generation, generate **K=3** candidates from three
deterministic orderings of the accumulated (action+observation) history, then execute the
**majority-voted** action. The model is never shown the vote; the bootstrap is untouched.

### 1a. Permutation unit (byte-exact, proven)

The rendered transcript is `bootstrap + raw₁ + append₁ + … + rawₜ + appendₜ`, where every bootstrap and
`append_k` segment ends with the exact anchor **D = `"\n\nAssistant: ```json\n"`**. Because observations
are `canonical_json`-encoded (real newlines escaped to `\n`) and the stop sequences forbid the model
emitting `\n\nAssistant:`, **D occurs in the transcript only as a segment terminator**. Splitting the
transcript on D yields:
```
seg₀ = "System: Tools: … \n\nUser: {request}"          (bootstrap minus trailing D — NEVER permuted)
seg_k = rawₖ + [scopeₖ] + "\n\nUser: Function output: {obsₖ}"   (k = 1..t — the permutable pairs)
```
so `transcript == seg₀ + D + seg₁ + D + … + segₜ + D`. The **pairs P = [seg₁ … segₜ]** are the
permutation unit. Rejoining `seg₀ + D + join(π(P), D) + D` for a permutation π reconstructs a valid
transcript that (a) always ends at a continuation anchor D and (b) is **byte-identical to the current
transcript when π = identity**. Each pair begins with an Assistant action (a valid continuation of the
preceding anchor) and ends just before the next anchor, so any ordering is structurally consistent.

### 1b. The three orderings (K=3, deterministic)

`canonical = P`, `reversed = P[::-1]`, `rotated = P[1:]+P[:1]`. `seg₀` (request/constraints/instruction
literal, most-salient at turn 1) is fixed in all three. For **t ≤ 1** the three are identical → the
mechanism is an **identity no-op** (single generation). For t = 2, reversed == rotated (2 distinct).

The logical voter order remains canonical/reversed/rotated. For t > 1 the three physical requests are
submitted concurrently; returned candidates are mapped to their submitted permutation, never to
completion order. Final byte audit follows the request_id of the accepted `final_answer` decision,
so response scheduling cannot change or falsify the selected raw model bytes.

### 1c. Aggregation (mechanical, preregistered — no judge, no synthesis)

Parse each of the K candidates (a parse failure = its own "unparseable" bucket). Then:
1. **final_answer guard:** if **≥2/3** candidates chose the `final_answer` *operation* → terminate;
   the executed final text is the **canonical** candidate's verbatim text if canonical chose
   final_answer, else the last final-voter in the frozen physical generation order (the rotated role)
   supplies its verbatim text (never compared/merged/regenerated). A
   **non-canonical** Final can therefore override canonical only with ≥2/3. If no bucket has a
   majority, rule 3 remains authoritative even when canonical itself is the sole Final; this keeps
   the R126 canonical fallback byte-exact instead of silently adding a new termination veto.
2. Else vote on the **exact canonical digest** (operation+args) of the non-final candidates: if some
   digest has **≥2/3** → execute that action; the executed candidate is the **canonical** one if it
   carries the winning digest, else the winning variant's candidate **rebased onto the canonical
   checkpoint** (its raw — a real model output — appended to the true append history; nothing
   synthesized).
3. Else **no majority → execute the canonical candidate** (deterministic fallback == exactly current
   R126 behavior, including a canonical parse-rejection which raises as today).
4. Agreement type (3/3, 2/3, none) + all K digests + permutation ids are logged to the causal ledger
   as objective facts. This round does **not** act on the agreement rate (no temperature coupling —
   that would be a second variable).

### 1d. Invariants preserved (avoid known collapse modes)
- **Bootstrap untouched** (`_assignment` byte-identical to R126) → R129 collapse family cannot recur
  from a bootstrap change; `seg₀` never permuted.
- **No second decision** (R125): the vote is a parallel aggregation, not a serial verify step the model
  must cross.
- **No per-turn re-injection** (R125): no added literal; the model sees exactly one ordering per call.
- **Byte-precision safe (proven):** byte-precision cases (B01/B06/B13/B19/B28) are single dominant-read
  (≤1 pair at the final turn) → identity permutation → canonical executed → byte-identical. Even with
  more pairs, **final_answer text is always taken verbatim from the canonical candidate**, so the raw
  bytes of any deliverable equal the current-behavior bytes. G1 cannot regress by construction.
- **Persistence spine intact:** permuted transcripts are used **only** for voting; the executed action
  is always committed onto the **canonical** append history (real order). No history is rewritten.

## 2. Hypothesis (falsifiable)

Front/back positional bias makes the model echo the layout of the front/back homogeneous items and
drop the middle at the write turn. Voting the exact action across three orderings suppresses
single-ordering minority errors (tool drift, premature Final, over-structured echoes that appear in
only one ordering), flipping a subset of the positional-bias FP (M06-family) to TP without a second
decision or added competing info.

**Honest weak-link caveat (pre-run):** at temp 0.05 the three orderings may produce **highly
correlated** outputs (near-greedy decoding is not very order-sensitive), in which case the vote is
frequently 3/3 == canonical and the mechanism is a near-no-op (Strict within ±3, few flips). The
converse risk: reordering the *most-recent* pair changes what is adjacent to the continuation anchor —
R126/R129 showed that position is load-bearing for completion, so a reordered tail could induce the
same OTHER-drift R129 showed. Both a null result and a completion regression are real possibilities and
will be logged as negative knowledge, not massaged. R130 is a **mechanism screen for R132 eligibility**,
NOT itself expected to reach terminal FP≤24 (§7 of R129: FP≤24 assessed likely unreachable).

## 3. Prediction (checked against the flip matrix after the run)

- **Helps (FP→TP):** among the positional-bias multi-read FP (M06 canary, H06, LH06, M01) and tool-drift
  cases where a minority ordering produced the wrong call. ≥1 attributable flip where the vote executed
  a **non-canonical majority** action ⇒ E2-eligible for R132.
- **Attribution requirement:** a KEEP requires the flip to be caused by a **2/3 or 3/3 vote that
  overrode the canonical minority** — a flip on a 3/3==canonical turn is variance, not the mechanism.
- **Must not regress:** completion (FN, OTHER not risen), byte-precision (5/5), R126-TP retention.

## 4. KEEP / REVERT gates (preregistered, baseline R126)

- **G1 byte-precision == 5/5** (structurally guaranteed by §1d; any regression ⇒ implementation bug ⇒
  REVERT).
- **G2 Strict ≥ 34** (R126 confirmed floor; no completion regression).
- **G3 FP ≤ 30 AND FN ≤ 1 AND OTHER ≤ 24** (improvement direction FP↓; guards the completion-collapse
  family — OTHER must not rise vs R126 baseline).
- **G4 0 running AND 90/90 valid Finals.**
- **G5 R126-TP retention ≥ 32/34** (proxy via R128-TP set; guards TP→FP/FN/OTHER churn).

**KEEP** iff FP < 30 with Strict ≥ 34 (FN ≤ 1, OTHER ≤ 24), **or** Strict ≥ 37 with FP ≤ 30 — AND the
flip matrix shows **≥1 attributable non-canonical-majority FP→TP** (variable actually fired). Otherwise
**REVERT** byte-exact to `baseline/round126-v19p1`.

**Anti-variance rule:** because single-run Strict variance is ±3 and at temp 0.05 the vote may be
3/3==canonical on most turns (mechanism a no-op), a raw score delta is **not** sufficient. KEEP requires
the ledger to show the vote *overrode canonical* on the flipped cases. A whole-run that is merely
another R126 variance sample (vote never overrode canonical on a flip) ⇒ REVERT-by-rule (E2 fail), the
R128 lesson.

## 5. Offline gate (all must pass before freeze)

- `pytest -q` → all green (baseline 107 + any new ensemble unit tests; new tests must assert: identity
  permutation reproduces the canonical transcript byte-for-byte; t≤1 ⇒ single generation; no-majority ⇒
  canonical executed; final_answer text taken from canonical).
- `python -m compileall rwkv_lh` → clean.
- e2e catalog → **90/90**.
- registry / `_validate_registry` clean; definitions↔handlers bijective (unchanged — no op added).
- **Byte-identity proof:** a deterministic test drives a multi-pair transcript through the ensembler
  with a stub client and asserts (a) the canonical permuted transcript == the original transcript
  (sha256), (b) with a client that returns the same command for all orderings the executed checkpoint
  digest == the single-generation checkpoint digest.
- **Determinism:** permutations are index-based (reversed/rotated), NOT random — no `random`/`Date`
  dependence (resume-safe, reproducible).
- source isolation → runtime differences from `baseline/round126-v19p1` are only
  `rwkv_lh/model.py` + `rwkv_lh/model_session.py`; tests add
  `tests/test_round130_order_ensemble.py` and adapt only the deterministic QueueClient fixtures in
  `tests/test_model_session.py`, `tests/test_unified_controller.py`, and
  `tests/test_round119_fact_integrity.py` to supply the K=3 physical calls. Everything else is
  hash-equal.

Then freeze the read-only source manifest
(`temp/generate_round130_source_manifest.py`, `--check` for read-only verify).

## 6. Run (frozen parameters — unchanged except the K=3 ensemble)

model `rwkv7-g1i-13.3b-20260805-ctx16384`; endpoint `http://127.0.0.1:29610/v1` (Bearer `rwkv-skills`);
temp 0.05 / top_p 1.0 / top_k 0 / presence 0 / frequency 0 / penalty_decay 0.996; max-transitions 200;
case concurrency 5 (at most 15 simultaneous K=3 requests); max_model_len 16384; transport
`prompt_replay`; max_output_tokens 1800 action / 1400
terminal. **K=3 order-ensemble per decision (identity-collapsed when t≤1).** Runner:
`scripts/run_rwkv_e2e_benchmark.py --suite all --concurrency 5`. The first serial implementation was
stopped at 32/90 and retained as `Round130_order_ensemble_SERIAL_ABORTED_32of90_20260818`; it is not
scored. Then REPORT.md +
MANUAL_CAUSAL_ANALYSIS.md with the full R126→R130 flip matrix + vote-override attribution; KEEP/REVERT
per §4.

## 7. Red lines (unchanged + explicit ensemble compatibility)

Standing: no threshold/scoring edits post-run; no per-case special-casing; no reading hidden acceptance
(`.verifier-private`, `*.acceptance.json`, `codex_reference_answers.json`); no reviewer/judge; no parsing
task text for required keys; no guessing missing semantic parameters; Controller never rewrites Finals;
raw Final preserves the model's original bytes; transport stays `prompt_replay`; no `--no-verify`; no
push (owner pushes on a KEEP that beats baseline).

**Ensemble compatibility (why this is admissible):**
- **Not a reviewer/judge:** the K candidates are generated in parallel; there is no second semantic
  boundary the model must cross (R53's failure was a serial same-model review). Aggregation is a
  mechanical exact-digest majority, preregistered, with a deterministic canonical fallback.
- **Not semantic resampling after a first decision:** all K are sampled together and all logged; the
  selection rule is fixed in advance; ties/no-majority fall back to the deterministic canonical default.
  There is no "decide, then re-decide."
- **Controller synthesizes nothing:** every executed action is a real model output (canonical, or a
  winning variant's own raw rebased onto the true history); final_answer text is verbatim from a model
  candidate; no business content is generated or preferred by content.
- **Model-invisible:** the model never sees the vote, the other orderings, or the agreement rate → zero
  added competing information per call ([[fixed-state-adjacency-principle]]).

## 8. Invalid implementation smoke before the valid frozen run

The first frozen implementation attempt was stopped after two completed cases because both had
`external_passed=true` but `final_output_matches_raw_rwkv=false`. Root cause: canonical supplied the
executed Final text, while the physical generation order canonical→reversed→rotated made the runner's
last observed Final the unselected rotated candidate. No score or verifier rule changed. The invalid
2-case artifacts are preserved at `Round130_order_ensemble_INVALID_final_trace_aborted/` with the
source manifest and sibling log. Sections 1b–1c now preregister the audit-compatible physical order
and selected Final rule before the valid Full90 restart.
