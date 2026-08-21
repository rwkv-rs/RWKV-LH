# Round127 v19-P2 — Request-Contract Decomposition — PROTOCOL (preregistered)

**Status:** preregistered before any R127 run. Baseline = Round126 v19-P1 (KEEP, the new
historical best). Single variable, one file (`rwkv_lh/model.py`).

## 1. Evidence (derived from the R126 full-90 flip matrix + FP traces)
R126 is Strict 36 (official) / 34 (confirmatory), FP 30, FN 0. `/goal` terminal success is
**not** met: FP 30 > 24. FP is now the dominant failure class. I classified all 30 R126 FP
from their `external_checks` observations:

- **STRUCTURE — output-contract key/shape drift (~11): B18, H06, LH04, LH06, M01, M15, M16,
  M19, M22, M26, M29.** The model completes with the right *values* in the wrong *shape/keys*:
  - M16: wanted `{items:[…], sources:{…}}`, produced `{"01":{…},"02":{…},…}` — **output keyed
    exactly like the per-id input files it just read.**
  - LH04: wanted `{events, count, total_amount}`, produced `{count, entries, total_amount}` —
    `entries` is a synonym of `events` (drift).
  - M22: wanted `{updated_config, applied, rejected}`, produced `{applied_keys, rejected_keys,
    updated_config}` — synonym drift on the companion keys.
  - M27: wanted `{order, node_count}`, produced `{build_order, node_count}` — synonym drift.
  - H06: wanted `{migrated:[…]}`, produced `{migrated_environments:[…], schema_version:…}`.
  - M01: wanted per-service `{name,version,runtime,theme}` (preserve unrelated `theme`),
    produced `{name,runtime,version}` — **dropped the preserved key**; and summary shape wrong.
- **FORMAT — text/markdown drift (~6): B05, B16, B22, M04, M08, M25.** Extra blank lines,
  missing `- [ ]` checkbox tokens, split headings, wrote JSON where Markdown was required.
- **VALUE/LOGIC (~4): B24 (no dedup+sort), M13 (revenue arithmetic), M27 (tie-break), M28
  (cutoff set).**
- **INCOMPLETE-but-claimed (~7): H03, H09, H17, LH10, LH12, M10, M23.**

**STRUCTURE + FORMAT = ~17/30 (57%) are one phenomenon: output-contract infidelity.** The
model does the work but, at the *write* turn, reconstructs the required output contract (exact
key names, nesting, format tokens) from memory and from the **adjacent input data** rather than
from the request's literal specification. Direct confirmation of contamination: M16's output
shape is a byte-for-byte echo of its per-id input file layout.

**Transcript-structure root cause (read from `model_io.render_bootstrap` /
`render_event_append`):** the request lives in the very first `User:` turn (root). Each tool
result appends `…\n\nUser: Function output: {data}\n\nAssistant: ```json`, so by the write
turn the **adjacent** content is the just-read data blob and the exact output contract (in the
request) is many turns back. R126 fixed **turn-1** adjacency (request last in the bootstrap
payload → +6 Strict, M06 flipped); the residual FP are **write-turn** drift.

**Why not simply re-present the request every turn:** that is exactly the **R125 REVERT**
(Strict 30→12). A second verbatim copy of the request is a *homogeneous duplicate* of the root
copy → the model cannot tell which governs (TP/FP→OTHER ×33), and R125 also added a second
decision (TP→FN ×14). Both are red lines now. R127 adds **no second copy** and **no second
decision**.

## 2. The RWKV-creator decomposition principle (the mechanism under test)
Founder guidance (2026-08-16, recorded as governing): *"尽量拆细，尽量不要多个特别是同质的
信息混杂"* — decompose finely; do not mix multiple, **especially homogeneous**, pieces of
information in one call. In R126's `_assignment`, the verbatim request sits **inside** one JSON
object as a peer field alongside the homogeneous lists `workspace_manifest` and
`recent_exact_action_records`. That is a textbook homogeneous-mixing: the governing request is
rendered as "one JSON field among same-kind peers."

**R127 = the minimal, safe first test of the decomposition principle:** lift the verbatim
request **out** of the JSON-field soup and render it as a **single standalone governing block**
as the LAST thing in the assignment (nearest the `Assistant:` continuation), so it reads as a
distinct-kind directive rather than one homogeneous field among peers. This is the corrected,
cost-free extension of R126: still **one copy**, no per-turn re-injection, no second decision,
content byte-identical (only the request's *framing* changes, JSON-field → trailing labeled
block).

## 3. The single variable (only `rwkv_lh/model.py`, method `_assignment`)
Before (R126): payload is one JSON object with `immutable_request` as the last **field**.
After (R127): payload JSON carries only the machine context (`protocol`, `constraints`,
`workspace_manifest`, `recent_exact_action_records`, `instruction`); the assignment string is
that JSON, then `"\n\nimmutable_request:\n"`, then the verbatim request. Same key name
(`immutable_request`, no new directive semantics), same request bytes, decomposed out of the
JSON. No other file changes. `instruction` text is **unchanged from R126** (to keep this a pure
framing A/B; no added instruction = no second decision).

## 4. Offline gate (must pass before any model run)
- `pytest -q` == 107 passed.
- `python -m compileall rwkv_lh` clean.
- e2e catalog selects 90/90.
- render smoke: assignment ends with `immutable_request:\n<request>` as the last block before
  the Assistant continuation; the JSON context no longer contains an `immutable_request` key.
- frozen source manifest written + `--check` 0 mismatch; **only `rwkv_lh/model.py` differs from
  R126**.

## 5. KEEP / REVERT gates (preregistered; baseline = R126 confirmed floor)
R126 official {Strict 36, FP 30, FN 0}; confirmatory {Strict 34, FP 31, FN 0}; 32 TP stable
across both runs. Single-run Strict variance ±3.

- **G1 byte-precision == 5/5** (B01, B06, B13, B19, B28 exact-bytes hold).
- **G2 Strict ≥ 34** (hold the confirmed R126 floor — no regression below the confirmatory).
- **G3 FP ≤ 30 AND FN ≤ 1** (R127's purpose is FP reduction; FN ≤ 1 guards the R125
  over-completion collapse).
- **G4 0 running AND 90/90 valid Finals.**
- **G5 R126-TP retention ≥ 32/34** (do not destroy confirmed successes).

**KEEP** iff all gates pass **and** there is a genuine improvement: **FP < 30 with Strict ≥ 34**
(a real reduction in output-contract-drift FP while holding completion), **or** Strict clearly
up (≥ 37) with FP ≤ 30 and FN ≤ 1. If FP does not drop with Strict held, **REVERT** — the
conclusion would be that re-*framing* the single request copy is insufficient and the write-turn
positional bias needs the founder's designated remedy (order-permutation ensembling), which R128
would then test. A KEEP that also improves the result is committed **locally only** (branch off
`baseline/round126-v19p1`); the owner pushes.

## 6. Red lines (unchanged)
No threshold/scoring edits post-run; no per-case special-casing; no reading hidden acceptance;
no reviewer/judge; no parsing task text for the required keys; Controller never rewrites Finals;
transport stays `prompt_replay`; no `--no-verify`; no push.
