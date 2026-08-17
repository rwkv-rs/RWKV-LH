# Round126 v19-P1 — Bootstrap Request-Last Adjacency — PROTOCOL (FROZEN)

**Baseline:** Round119 v18-P0 (Strict 30 / FP 36 / FN 0). Source is currently byte-exact R119
(model.py 49dea587…, model_session.py f4c9a6a3…, 107 tests green).

## 1. Evidence (derived from R125 full-90 flip matrix + R119 FP analysis)
- R119: 21/36 FP are pure exact-literal drift (wrong path segment / dropped byte / reordered key).
- R125 (spec-adjacency anchor, REVERT 12/90) proved the *mechanism* is real — the only genuine
  wins were FP→TP ×3 (B04, B29, M04) where the verbatim request sat adjacent to the write point —
  but the *delivery* was fatal: re-injecting the full request **every turn** added (a) a second
  decision ("verify before completing") → TP→FN ×14, and (b) a homogeneous duplicate of the root
  request + mean 10314 prompt tok/req → TP/FP→OTHER ×33, code-chain 6/6→0/6.
- Current `_assignment` renders the bootstrap payload with `json.dumps(..., sort_keys=True)`.
  Alphabetical order = `constraints, immutable_request, instruction, protocol,
  recent_exact_action_records, workspace_manifest`. So the **verbatim request is buried second**
  and the **bulky workspace_manifest sits LAST** — i.e. nearest the `Assistant:` continuation point.
  This is the exact inverse of the fixed-state adjacency principle ("critical literal nearest the
  continuation point") and is a standing, unfixed violation flagged in the principle doc.

## 2. Hypothesis
Placing the verbatim `immutable_request` as the **last** field of the bootstrap User turn — so it
is the final content before `\n\nAssistant: \`\`\`json` — recovers a subset of the **turn-1-decisive**
literal-drift FP (single-shot writes decide at the root, where this adjacency is exact), at **zero
token cost, no second decision, and no per-turn duplication** (bootstrap/rollover render only; the
append chain is unchanged). This isolates the adjacency variable that R125 conflated with its costly
delivery.

## 3. Exact change (single global root-cause change)
File `rwkv_lh/model.py`, method `_assignment` only:
1. Reorder the `payload` dict literal so keys are:
   `protocol, constraints, workspace_manifest, recent_exact_action_records, instruction,
   immutable_request` — `immutable_request` LAST.
2. Change the return from `json.dumps(payload, ensure_ascii=False, sort_keys=True)` to
   `json.dumps(payload, ensure_ascii=False)` (drop `sort_keys`; CPython dict insertion order is
   deterministic, so bytes are reproducible).

No other file changes. Content is byte-identical to R119; only key **ordering** within the bootstrap
payload changes. No new fields, no re-injection, no instruction text change.

## 4. Expected effects
- **Primary:** several R119 turn-1-decisive literal-drift FP flip FP→TP (target: net FP→TP ≥ +2).
- **Neutral by construction:** identical payload content ⇒ no token increase; no second decision;
  no homogeneous duplicate; multi-step trajectories (request already behind ≥1 observation) largely
  unaffected.

## 5. Non-regressions (pre-registered)
- G1 byte-precision == 5/5 (B01, B06, B13, B19, B28).
- G2 Strict ≥ 31 (must not fall below R119's 30; target > 31 for KEEP-as-best).
- G3 FP ≤ 36 (no FP increase vs R119) AND FN ≤ 1 (no completion collapse — the R125 failure mode).
- G4 0 runs left in running state; 90/90 valid Finals.
- G5 R119-TP retention ≥ 28/30 (adjacency reorder must not destabilize existing successes).

## 6. KEEP / REVERT rule
KEEP only if G1∧G3∧G4∧G5 hold AND Strict ≥ 31 (a genuine, non-regressing result). Declare a **new
historical best** only if Strict > 31 with FP ≤ 24 and FN ≤ 1 (goal thresholds) → then run one
unchanged-source confirmatory full-90 meeting the same thresholds → git checkpoint (local commit
only; owner pushes). Otherwise REVERT: byte-restore model.py to sha 49dea587… (R119) and verify
against the R119 manifest; no commit.

## 7. Frozen configuration (unchanged)
model rwkv7-g1i-13.3b-20260805-ctx16384 · endpoint http://127.0.0.1:29610/v1 · temperature 0.05 ·
top_p 1.0 · top_k 0 · max_transitions 200 · concurrency 1 · uv 0.12.5 · max_model_len 16384.
Runner: `RWKV_BASE_URL=… RWKV_API_KEY=rwkv-skills RWKV_MODEL=… uv run python
scripts/run_rwkv_e2e_benchmark.py --suite all --max-transitions 200 --concurrency 1 --output
outputs/round126_v19p1_full90`.

## 8. Red lines honored
Single RWKV lane; direct operation tools; append-only CausalEvent authority unchanged; raw Final
bytes preserved; no reviewer/judge/DAG/subagent; no hidden-acceptance access; no controller-written
answers; no resampling; no per-case special-casing; transport = prompt_replay (native state is the
owner's future work). Change is a global payload-ordering fix, task-agnostic.
