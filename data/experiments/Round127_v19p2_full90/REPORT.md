# Round127 v19-P2 — Request-Contract Decomposition — REPORT

**Verdict: REVERT.** Source restored byte-exact to R126 baseline
(`rwkv_lh/model.py` sha256 `399bf5225ef384d98e4994246aa0c1e6460f177fd836820caec70d7b57ff0212`,
identical to `baseline/round126-v19p1:rwkv_lh/model.py`; 107 pytest green). No commit.

## 1. What R127 changed (single variable, `rwkv_lh/model.py::_assignment`)
R126 kept the verbatim `immutable_request` as the **last field inside** the one JSON payload.
R127 lifted it **out** of the JSON and rendered it as a standalone trailing block
(`json.dumps(context) + "\n\nimmutable_request:\n" + request`) — one copy only, no per-turn
re-injection, no second decision, request bytes and instruction text byte-identical to R126.
The hypothesis: framing the governing request as a distinct-kind trailing directive (rather than
one homogeneous JSON field among `workspace_manifest`/`recent_exact_action_records`) would reduce
write-turn output-contract drift (the residual FP=30 class), per the founder decomposition rule.

## 2. Result (full-90, frozen source, 90/90 valid, 0 running)

| metric      | R126 baseline | R127 | Δ    |
|-------------|--------------:|-----:|-----:|
| Strict (TP) |            36 |   30 | −6   |
| FP          |            30 |   25 | −5   |
| FN          |             0 |    4 | +4   |
| OTHER       |            24 |   31 | +7   |
| byte (5)    |           5/5 |  4/5 | −1 (B06) |
| R126-TP retention | —       | 28/36 | −8 |

**All KEEP gates FAIL** except G4: G1 byte 4/5 (B06 lost); G2 Strict 30 < 34; G3 FN 4 > 1;
G5 retention 28/36 < 32. `genuine improvement` False.

## 3. Flip matrix R126(rows) → R127(cols)
```
              TP      FP      FN   OTHER
     TP       28       1       4       3
     FP        2      19       0       9
     FN        0       0       0       0
  OTHER        0       5       0      19
```
- **FP→TP ×2 (genuine wins): B05, B29.**
- **FP→OTHER ×9: B18, H06, LH04, LH10, LH12, M01, M16, M18, M28.**
- TP→FN ×4: B02, B06, B20, M05.  TP→OTHER ×3: M02, M06, M24.  TP→FP ×1: LH09.
- OTHER→FP ×5.

## 4. The decisive finding (why REVERT, not variance)
The FP drop (30→25) is **not** a reduction in output-contract-drift — it is a **shadow of
completion collapse**, the same signature family as R125:

- Of the 11 R126 FP that left the FP bucket, only **2 became correct (FP→TP)**; **9 stopped
  completing (FP→OTHER)**. You cannot be scored FP if you never emit a completed Final, so FP fell
  because completion fell, not because contracts got fixed.
- Simultaneously **7 confirmed R126 successes were destabilized** (TP→FN ×4 + TP→OTHER ×3). The
  TP→FN cases produced the **correct or near-correct artifact** (`external_passed=True`) but
  finished `status=interrupted` — e.g. B06/B02 ran 15–16 model requests for a 2–3 action task,
  re-deciding instead of calling `final_answer`. B06 also broke byte-precision.

**Mechanism:** extracting the single request copy from the structured JSON into loose trailing
text destabilized the completion boundary. The model, reading the request as a free-floating
labeled block adjacent to the continuation, kept re-exploring the request rather than converging
to `final_answer`. This is the completion-collapse family (loose adjacent request text →
non-termination), distinct from R125's failure (a *second* copy + a *second* decision) but landing
in the same place: net Strict down, FP down only as a byproduct of not completing.

## 5. Conclusion carried to R128
R126's form — **request as the last field, inside the JSON** — is optimal. Extraction into loose
trailing text is **net-negative even without a duplicate or a second decision**. This closes the
request-*placement*/request-*framing* line of inquiry: turn-1 adjacency is already solved by R126,
and further re-framing of the single request copy does not help (it hurts). The residual
write-turn output-contract drift (FP≈30) must be attacked by a different, still-unused
RWKV-creator mechanism — **order-permutation ensembling / hierarchical reduce** — not by moving
the request. See `MANUAL_CAUSAL_ANALYSIS.md`.

## 6. Provenance
- Protocol (preregistered): `Round127_V19P2_REQUEST_CONTRACT_DECOMPOSITION_PROTOCOL.md`.
- Frozen source manifest: `Round127_v19p2_source_manifest.json` (`--check` 0 mismatch; only
  `model.py` differs from R126).
- Run: `data/experiments/Round127_v19p2_full90/` (results.json + cases/), log
  `temp/round127_v19p2_run.log`. Analysis: `temp/round127_analysis.py`.
- Frozen run params: model `rwkv7-g1i-13.3b-20260805-ctx16384`, endpoint
  `http://127.0.0.1:29610/v1`, temp 0.05 / top_p 1.0 / top_k 0, max-transitions 200,
  concurrency 1, max_model_len 16384.
