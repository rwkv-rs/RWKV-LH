# Round66 fixed-15 manual causal analysis

## Outcome

- Strict E2E: `4/15`.
- External acceptance: `6/15`.
- Agent completion: `4/15`.
- False positives: `0`.
- False negatives: `2` (`E2E-M03`, `E2E-M12`).

This misses the preregistered canary gate of Strict >= `6/15`, FP <= `3`,
FN <= `1`, with B01/B02/B10 Strict. B01/B02/B10 passed, but Strict and FN
did not. Full90 is therefore not run and this working tree is not uploaded.

## Case-by-case causal chain

### E2E-B01 — Strict pass

Goal parsing, the two-task write/read plan, exact `write_file`, task-local
postcondition decisions, Goal evidence and final answer all remained aligned.
This is a positive control for the direct G1i action path.

### E2E-B02 — Strict pass

RWKV read the real input, derived `Orion` and `14`, wrote exactly the requested
two-field JSON, and repeatedly read the current file before Goal completion.
The extra verification Tasks were redundant but did not change the artifact.

### E2E-B10 — Strict pass

RWKV first wrote an implementation without the required import, then later
wrote the complete implementation and ran the real test command successfully.
The format boundary accepted common action forms without selecting or changing
the code. This remains a positive control for coding plus command verification.

### E2E-M01 — Strict pass; prior false positive removed

Unlike Round65, RWKV read all three service JSON files before writing them. It
preserved `port`, `theme`, and `threads`, changed the requested fields, created
the summary, and completed. The new preserving-update primitive was available
but RWKV chose complete `write_json` values; the improvement came from the
model-visible tool/effect and observation structure, not controller rewriting.

### E2E-M03 — external pass, agent blocked (false negative)

RWKV read the original `users.json`, wrote the exact migration, read the current
file completely, and produced an extra report. Goal GC1–GC4 were supported.
For tag preservation, the prompt contained complete original and current
sources, both marked `truncated=false`, plus a factual same-path revision chain.
RWKV nevertheless claimed the current source was truncated and chose
`insufficient`. Its recovery then emitted a bare `tasks` argument copied from
persisted Task state; the fixed G1i tool name was omitted and the format layer
rejected it twice. The first harmful semantic event is the incorrect Goal
evidence reading; the terminal structural amplifier is the recovery boundary.

### E2E-M06 — correct block after a model semantic error

RWKV correctly read `selection.txt` and listed `assets/`, but selected
`read_files` for a Task whose postcondition required copying. Task adjudication
correctly said the copy had not occurred. RWKV repeated `read_files` twice.
Failure analysis correctly requested replan, and the second replan contained
the right copy/manifest strategy, but used schema `2025-06-03`; the free-JSON
replan interface rejected it. The root semantic error remains RWKV's action
choice; the architecture then lacked a robust single Task-batch replan boundary.

### E2E-LH02 — Goal error propagated into an externally wrong artifact

RWKV created all 15 checkpoint files correctly and used one `read_files` call
to observe all of them. However, Goal parsing ignored the explicit grounding
instruction and added `step` to the final config criterion. The action faithfully
wrote `step:15` into `final/config.json`, which external acceptance rejects. It
also split one artifact contract into several redundant criteria. Recovery later
attempted step16+ and then copied task state into invalid G1i output. The first
harmful event is the accepted, unreviewed Goal proposal.

### E2E-LH05 — partial real observations, recovery output too wide

RWKV listed primary/fallback directories, read the recovery rules, and read
only shards 01–04. Goal adjudication correctly found the summary absent. The
first recovery attempted a long sequential Task batch and was truncated before
the outer JSON closed. The correction emitted bare `tasks`, which was rejected.
The recovery schema allowed up to 32 Tasks even though a small iterative
frontier would have been safer and sufficient.

### E2E-LH11 — pagination and task-effect semantics both failed

The initial Tasks claimed five eight-file pages, but four calls reset
`start_after` to null; a later 40-entry list exposed all paths. Recovery created
five checkpoint Tasks before reading the phase contents. For phase 1 RWKV used
`read_files` and then incorrectly passed the postcondition “checkpoint created”
because the data was available; for phases 2–5 it invented the same `F1/F2`
values. A later recovery again copied persisted Task fields and then a large
batch was rejected. Tool effects were stated correctly, but one RWKV pass did
not reliably apply them.

### E2E-B24 — malformed Goal accepted, then errors amplified

Goal output copied the Goal-normalization instruction into `objective`, made
`required` an array instead of a boolean, and reduced the real transform to a
vague verification criterion. The parser coerced the non-boolean with `bool()`
instead of rejecting the contract. Planning then tried to read absent
`sorted.log`; recovery wrote it empty. Later replan Tasks read instead of
deduplicating, one Task incorrectly passed a read as removal, and generated
large repeated content until action JSON truncated. The first root is strict
Goal protocol validation, followed by missing RWKV review of its own action.

### E2E-M12 — external pass, agent blocked (false negative)

RWKV wrote correct `safe_divide` and `median` implementations and the real tests
passed. The Goal evidence prompt displayed the current correct code, the original
wrong code, the successful command, and revision status accurately. RWKV still
claimed the current snapshot returned `a * b` and chose `insufficient`. G1i
recovery then successfully produced Tasks, but subsequent correct `write_file`
calls carried a copied top-level `execution_capsule`; the closed format boundary
rejected that decoration. The first harmful event is a factual self-contradiction
in Goal evidence; the format rejection is a later amplifier.

### E2E-M16 — recovery lost the immutable id range

The base plan correctly covered ids 01–05 and successfully used
`fallback/item_04.json`. Goal evidence correctly observed that `recovered.json`
was still absent. The recovery capsule contained only the unresolved criterion,
Goal digest, and history—not the original request “ids 01 through 05”. RWKV
continued the visible numeric pattern and proposed ids 06–10. Failures then
cycled through nonexistent primary/fallback paths; correct fallback proposals
carrying `execution_capsule` were rejected, and a correction copied an absolute
runtime path from the error. The primary architecture defect is omission of the
immutable original Goal from the recovery capsule.

### E2E-M18 — wrong first tool, repeated without a compact self-review

The first Task's exact postcondition was one listing page, and the manifest
contained `inputs/a.txt` and `inputs/b.json`. RWKV nevertheless selected
`read_files` with invented `file1.txt`–`file3.txt`. Failure analysis recognized
wrong paths but repeated the same list twice. Scope/error handling worked and no
wrong digest map was written. A model-owned pre-execution review of Task,
selected tool effect, and observed paths is needed; the controller must not
substitute its own path list.

### E2E-H12 — all 15 shards read, recovery protocol blocked production

RWKV listed and read every real shard successfully. No aggregate producer was
in the initial frontier, so recovery was required. Its first bare `tasks` output
described per-shard aggregate work but was rejected for missing the fixed G1i
tool envelope. Its correction repeated 15 completed reads as immediately-ready
Tasks and was rejected by the eight-ready limit. The history was present, but
the recovery interface was too wide and did not consistently anchor the full
immutable Goal.

### E2E-H13 — cursor state was used once, then lost

T1 and T2 correctly listed docs 01–08 using `next_cursor`. Later Tasks reset the
cursor or used `read_files` on already observed paths while claiming new listing
pages; RWKV passed those mismatched postconditions. Goal evidence correctly
found checkpoints absent. Recovery's first bare Task batch was rejected and its
G1i correction truncated while describing many checkpoints. This combines
Task-effect self-contradiction, repeated-state projection, and an oversized
recovery frontier.

## Cross-case root causes

1. **Immutable Goal is incomplete in recovery state.** M16 is direct evidence;
   H12/H13 also repeat visible history instead of continuing the original goal.
2. **Goal proposal validation is not strict and has no RWKV grounding review.**
   B24 accepted a malformed required field; LH02 accepted an invented final
   field; M03 split one output into seven criteria despite explicit guidance.
3. **Task-batch boundaries are inconsistent.** Goal recovery and failure replan
   still accept different free-JSON/G1i forms; bare `tasks`, persisted Task
   records, tool_calls, and wrong schema recur across cases.
4. **Recovery frontiers are too large for reliable completion.** LH05 and H13
   truncated; H12 returned 15 immediately-ready repeats.
5. **A single RWKV pass often contradicts visible tool effects or evidence.**
   LH11/H13 passed read-only actions as creation/listing effects; M03/M12 read
   complete current evidence as absent or stale. This must be addressed by an
   RWKV-owned compact review, not a rule that chooses the preferred answer.
6. **One more observed common decoration exists.** `execution_capsule` appears
   beside otherwise complete single calls and is never an action argument. It
   should be separated only as an audited closed-format decoration.

## Direction for the next preregistered round

- Preserve immutable original request, objective, constraints and unresolved
  criteria in every Goal-obligation capsule.
- Strictly validate Goal proposal types/fields, then ask RWKV for one explicit
  grounding review before freezing the Goal.
- Use the same one-tool G1i Task-batch protocol for failure replans and Goal
  recovery; support the observed bare-arguments form only when that one tool is
  already fixed, and project registered persisted Task fields with full audit.
- Limit each recovery response to a small total Task frontier (four), allowing
  iterative continuation under the existing 64-round budget.
- Add one compact RWKV action review before execution and one compact evidence
  review before an `insufficient` Goal decision becomes recovery. The reviewer,
  not controller rules, owns the final semantic choice.
- Register `execution_capsule` as a typed, top-level, otherwise-complete-call
  decoration; retain raw payload and reject conflicts/mixed calls.
