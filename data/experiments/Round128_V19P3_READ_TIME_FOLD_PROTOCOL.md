# Round128 v19-P3 — Read-Time Hierarchical Fold (`reduce_json`) — PROTOCOL (preregistered)

**Status:** preregistered before any R128 model run. Baseline = Round126 v19-P1 (KEEP, current
historical best: Strict 36 official / 34 confirmatory, FP 30, FN 0). Single variable: one new
direct operation `reduce_json` (18th) wiring the dormant `chunks.py` reduce scaffold. Source diff
vs R126 is exactly: `rwkv_lh/harness.py` (definition + handler + verification spec + import),
`rwkv_lh/model.py` (`preferred_order` += `reduce_json`, one line), and `tests/test_reduce_json.py`
(new). Everything else byte-identical to R126 (chunks.py / model_io.py / model_session.py hashes
verified equal to `baseline/round126-v19p1`).

## 0. Mechanism replan — why `reduce_json` and not extract-by-locate (owner decision 2026-08-17)
The owner proposed **extract-by-locate** (model points at a rough source span — line range /
function name / regex "样子" — and the harness copies the exact bytes, avoiding model re-emission
so whitespace/format is byte-preserved). It is a sound mechanism for **large verbatim reproduction**
and is recorded as a to-do for the `rwkv_lh_large_code_31_v1` coding suite. It was **evaluated
against real E2E-90 FP artifacts (R127 full-90 cases) and set aside for this benchmark**, because
the E2E-90 FP are not verbatim-copy whitespace drift:

- **M04** (`release/RELEASE.md`, wanted `# <name> <version>` / `Released: <date>`): produced
  `# Nebula` then **echoed the write-target filename** `# RELEASE.md` twice, then the right last
  line. `release.json` values were byte-perfect. → **positional/target echo + composition miss**,
  not whitespace drift.
- **M25** (wanted Markdown `## VERSION` + `- [type] text`): produced a **JSON object** instead of
  Markdown. → **wrong output shape / input-shape echo**, no verbatim span to copy.
- **M08** (`STATUS.md`): extra blank lines — but the bullets are **computed** from `metrics.json`;
  there is no source span to extract.
- **B16** (`app.env`): task is to **remove** comment/blank lines; you cannot "extract verbatim"
  a file you must edit down.

Conclusion (owner-selected direction "攻 E2E-90 回显病灶"): E2E-90's residual FP are the
**shape/positional-echo** family — the write turn reconstructs the output from an adjacent salient
shape (a last-read blob, the input JSON's shape, or the write-target path) instead of from the
request contract. That is what `reduce_json` attacks. Extract-by-locate is deferred (off this
/goal, right tool for the coding suite). **Honest limit stated up front:** the clearest echo cases
(M04, M25, M08, B16) are *single-read* and therefore out of reach of any fold/permutation/decompose
mechanism; `reduce_json`'s reachable slice is the *multi-read homogeneous* subset only (below).

## 1. Evidence (R126 full-90 flip matrix + FP anatomy; R127 case artifacts)
R126 is Strict 36/34, FP 30, FN 0. Goal FP≤24 unmet (gap −6). R127 (request lifted out of the JSON)
REVERTED — completion collapse (Strict 30, 9 FP→OTHER, 4 TP→interrupted), proving the
**request-placement line is closed**: R126's form (request last, inside the JSON) is optimal, and
the residual FP≈30 is **whole-transcript positional/shape bias**, not a request-location problem.

Per-case anatomy of the 30 R126 FP:
- **Only 3/30 roll over** (LH10, LH12, M01) → a rollover-time fold is essentially dead (out).
- **15/30 read exactly one file** → no homogeneous read tail; a fold structurally cannot reach these.
- **8/11 STRUCT-drift FP read ≥2 homogeneous files** (H06=3, LH06=4, M01=10, M15=3, M16=10, M22=3,
  M26=2, M29=2). These are the shape-echo cases: multiple same-kind read results accumulate in the
  append tail and the write turn reconstructs the output contract from the **adjacent (last-read)
  blob's shape** instead of the request spec. Direct confirmation: M16 read 10 per-id files and
  produced output **keyed by id** — a byte-for-byte echo of its inputs' collective layout.

**Root cause (founder decomposition rule, [[rwkv-creator-order-ensembling-advice]]):** N homogeneous
items co-located in one context is what positional/single-ordering bias feeds on — the model attends
to the salient (last) one and its shape dominates the write turn.

## 2. Mechanism under test — hierarchical reduce (append-compatible, model-executed at read time)
The append read tail is **immutable causal history** (R123: rebuild/reorder → deterministic
fixed-point, fatal), so the fold cannot be done by the controller over past turns. It is
**model-executed at read time via an intermediate file**: the model folds the N homogeneous items it
has read into ONE combined scratch artifact, then reads that single artifact, so at the write turn
there is no dominant per-item input shape to echo — the model must consult the request spec for the
output contract. The reduce scaffold already exists but was **dormant**
(`chunks.py::reduce_input_digest`, `pack_reduce_fan_in`, `LaneTokenBudget`, `split_text_source`,
unit-tested, unwired). R128 wires `reduce_input_digest` as a tool.

## 3. The single variable — new operation `reduce_json` (18th direct op)
Deterministic, lossless, no business logic, no interpretation of task meaning:
- **Inputs:** `sources` (array of workspace-relative JSON files already observed; any order,
  minItems 1) and `path` (output scratch file).
- **Behavior:** resolve each source (must_exist), parse JSON, build children
  `{"source_ref": <rel posix>, "value": <parsed value>}`; **sort children by `source_ref`** (fold is
  order-independent → identical bytes and digest for the same source set); wrap losslessly into a
  uniform envelope `{"reduce_schema":"read-time-fold.v1","count":N,
  "reduce_digest":<reduce_input_digest(children)>,"sources":[…]}`; write with the canonical dump
  idiom (`json.dumps(…, ensure_ascii=False, indent=2, sort_keys=True)+"\n"`, atomic). Every input
  value is preserved verbatim; the envelope is uniform and obviously **scratch** (a `reduce_schema`
  marker, not any task's answer shape), so it cannot itself be a deliverable — the model must still
  reshape to the request contract at write time.
- **Availability:** exposed as a normal optional operation with a clear "this is scratch, never a
  deliverable" description, placed among the read/aggregate ops (`preferred_order`: after
  `file_digest`, before `write_file` → read → reduce → write). The model invokes it **autonomously**
  when it has many homogeneous reads. If never used, the round is a no-op (REVERT, no harm). **No
  instruction/directive added** to `_assignment` (avoids R125's second-decision collapse); **no
  content moved out of the JSON payload** (avoids R127's completion collapse). `_assignment` is
  **byte-identical to R126** (verified).

## 4. Offline gate — RESULT (all passed before freeze)
- `pytest -q` → **111 passed** (107 prior + 4 new `reduce_json` tests; no regression).
- `python -m compileall rwkv_lh` → clean.
- e2e catalog → **90/90** (core30 30 + extension48 48 + lh12 12).
- registry → **18 direct operations + `final_answer`**; `_validate_registry` clean; `noop` excluded
  from g1i defs; `reduce_json` present and at read→reduce→write position (index 4).
- `_assignment` render → **byte-identical to R126** (immutable_request last, inside the JSON; no new
  instruction; tool list is passed separately and is not part of `_assignment`).
- new-op smoke (unit tests): lossless envelope over multiple sources; `reduce_digest` deterministic
  and **order-independent**; non-empty-sources guard; round-trips every input value.
- source isolation → only `rwkv_lh/harness.py`, `rwkv_lh/model.py`, `tests/test_reduce_json.py`
  differ from `baseline/round126-v19p1`; chunks.py/model_io.py/model_session.py hash-equal.

## 5. KEEP / REVERT gates (preregistered; baseline = R126 confirmed floor)
R126 official {Strict 36, FP 30, FN 0}; confirmatory {Strict 34, FP 31, FN 0}; single-run Strict
variance ±3.
- **G1 byte-precision == 5/5** (B01, B06, B13, B19, B28 exact-bytes hold).
- **G2 Strict ≥ 34** (hold the confirmed R126 floor; no completion regression).
- **G3 FP ≤ 30 AND FN ≤ 1** (R128's purpose is FP reduction; FN ≤ 1 guards over-completion collapse).
- **G4 0 running AND 90/90 valid Finals.**
- **G5 R126-TP retention ≥ 32/34** (do not destroy confirmed successes).

**KEEP** iff all gates pass **and** genuine improvement: **FP < 30 with Strict ≥ 34**, **or**
Strict ≥ 37 with FP ≤ 30 and FN ≤ 1. Otherwise **REVERT** (restore harness.py/model.py byte-exact to
R126, quarantine the new test).

**Honest expected ceiling (pre-run):** the fold can, at most, reach the ~8 multi-read STRUCT FP
(H06, LH06, M01, M15, M16, M22, M26, M29); the ~15 single-read FP (incl. the M04/M25/M08/B16 echo
cases) and the 3 rollover FP are structurally out of reach. Terminal FP≤24 (−6) would need ~6 of the
8 to flip to TP — optimistic for one round. R128 is expected to be a **partial** step within
R128–131. Risks: (a) optional op not adopted → no-op; (b) the uniform envelope could itself become a
NEW echo source (output wrapped as `{sources:[…]}` — M25 shows the model readily echoes JSON
containers) → watch the flip matrix; (c) any completion destabilization (TP→FN/OTHER) → immediate
REVERT under G2/G5.

## 6. Frozen parameters (unchanged)
model `rwkv7-g1i-13.3b-20260805-ctx16384`; endpoint `http://127.0.0.1:29610/v1`; temp 0.05 /
top_p 1.0 / top_k 0; max-transitions 200; concurrency 1; max_model_len 16384; transport
prompt_replay. Runner: `scripts/run_rwkv_e2e_benchmark.py --suite all`.

## 7. Red lines (unchanged)
No threshold/scoring edits post-run; no per-case special-casing; no reading hidden acceptance; no
reviewer/judge; no parsing task text for required keys; no guessing missing semantic parameters; the
fold is lossless/deterministic (no controller-generated business answer, no rewritten Final);
Controller never rewrites Finals; transport stays `prompt_replay`; no `--no-verify`; no push. A KEEP
that beats baseline is committed **locally only** (branch off `baseline/round126-v19p1`); the owner
pushes ([[commit-local-user-pushes]]).
