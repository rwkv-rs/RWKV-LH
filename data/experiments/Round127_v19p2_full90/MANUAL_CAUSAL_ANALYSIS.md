# Round127 v19-P2 — MANUAL CAUSAL ANALYSIS

Variable: `_assignment` renders the verbatim request as a standalone trailing block
(`… + "\n\nimmutable_request:\n" + request`) instead of R126's last-field-inside-the-JSON form.
One copy, no per-turn re-injection, no second decision, request/instruction bytes identical.
Full-90: Strict 36→30, FP 30→25, FN 0→4, OTHER 24→31, byte 5→4/5. **REVERT.**

## Claim: the FP drop is a shadow of completion collapse, not a contract-fidelity gain
The round's purpose was to cut the output-contract-drift FP class by re-framing the request as a
distinct-kind directive. If it had worked, FP cases would move to **TP** (same completion, now
correct shape). Instead:

| R126 FP exits (11) | count | meaning |
|--------------------|------:|---------|
| FP → TP            |     2 | genuine win (B05, B29) |
| FP → OTHER         |     9 | stopped completing (B18,H06,LH04,LH10,LH12,M01,M16,M18,M28) |

FP fell by 5, but 9 of the 11 departures were cases that **stopped emitting a completed Final** —
you cannot be classified FP without completing. Only 2 were real fixes. The FP metric moved for
the wrong reason.

## Cross-check: confirmed successes were destabilized in the same direction
Seven R126 TP were lost, all toward non-completion:

- **TP → FN ×4 (B02, B06, B20, M05):** verified from case artifacts —
  `external_passed=True, agent_completed=False, status=interrupted`. The artifact is correct/near
  correct but the run never terminated. B06 also broke exact-byte precision (G1 5→4/5). These are
  the strongest evidence: the *work was right*; only the *completion boundary* failed.
- **TP → OTHER ×3 (M02, M06, M24):** completion lost without a passing artifact. M06 is the
  RWKV-creator's signature late-item case that R126 had just *won* (OTHER→TP in R126) — R127 undid
  that win, confirming the intervention acted on the completion/positional pathway.
- TP → FP ×1 (LH09): the lone TP that stayed completed but drifted shape.

Net completed-Final population: R126 66 (TP+FP) → R127 55. Eleven fewer completions; the entire
Strict loss (−6) and the FN/OTHER rise are downstream of that.

## Mechanism
The append transcript places the continuation marker (`Assistant:`) at the end of a growing
transcript. R126 keeps the request as the terminal field **inside** the machine-context JSON, so
the continuation begins from a closed, well-formed object. R127 appends the request as loose,
labeled free text *after* the JSON, immediately before the marker. Read from that position, the
free-floating request reads as fresh material to act on rather than a settled contract already
satisfied — so the model re-engages the request (B06/B02 spent 15–16 model requests on 2–3-action
tasks) instead of deciding `final_answer`. Loose adjacent request text destabilizes termination.

This is the **completion-collapse family** — the same terminal symptom as R125 (Strict→12, FN 19),
reached by a different route. R125 collapsed completion with a *second copy* + a *second decision*;
R127 collapsed it with *no duplicate and no second decision*, merely by moving the single copy out
of the structured object into trailing prose. That isolates the cause precisely: it is not
duplication or an added decision — it is **the request's structural embedding**. Inside the JSON,
adjacent-but-closed → stable completion. Outside as trailing prose, adjacent-but-open → the model
keeps working.

## What this proves about the design space
1. **Turn-1 request adjacency is solved (R126) and should not be touched further.** Request last,
   inside the JSON, is optimal. Every attempt to make the request "more prominent" by lifting it
   out of structure (R125 re-injection, R127 extraction) collapses completion.
2. **The residual write-turn output-contract drift (FP≈30) is not a request-placement problem.**
   Moving the one request copy cannot fix it — R127's 2 genuine FP→TP are swamped by the completion
   damage. The exact output spec being far from the write turn is a *positional-bias-over-the-whole-
   transcript* problem, not a *where-does-the-request-sit* problem.
3. Therefore R128 must use a still-unused RWKV-creator mechanism that attacks positional bias
   without moving/duplicating the request or adding a decision: **order-permutation ensembling**
   (vote across input-order permutations so no single late-item position dominates) or
   **hierarchical reduce** (fold homogeneous observations so the write turn sees a compact,
   order-robust summary rather than a long same-kind tail). Both are within red lines (no second
   Final decision, no task-text parsing, no hidden-acceptance read, transport stays prompt_replay).

## Red-line compliance
No threshold/scoring edits post-run; no per-case special-casing; no hidden-acceptance read; no
reviewer/judge; no task-text key parsing; Controller did not rewrite Finals; transport
prompt_replay; source reverted byte-exact to R126; no commit (REVERT).
