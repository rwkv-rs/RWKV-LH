# Round105 manual causal analysis

## Result versus Round104

| Case | Strict | Requests | Tasks | Attempts | Structural result |
| --- | --- | ---: | ---: | ---: | --- |
| E2E-H08 | fail | 14 vs 134 | 1 vs 15 | 3 vs 43 | identical replacement chain suppressed |
| E2E-LH07 | fail | 43 vs 230 | 10 vs 54 | 24 vs 107 | duplicate replacement batches suppressed |
| E2E-H13 | fail | 27 vs 44 | 7 vs 11 | 11 vs 18 | duplicate replacement batches suppressed |

All Finals were non-empty raw RWKV output. Request reduction is diagnostic only and is
not counted as correctness; Strict remained `0/3`.

## E2E-H08 call chain

1. RWKV again created one combined read/create/idempotency Task with
   `file_content_read` evidence for `ledger.json`.
2. The first read returned all source content plus explicit EOF and source size.
3. RWKV again requested byte 30 and then byte 60 instead of producing the ledger.
4. Four unchanged reads triggered Goal recovery. All five replacement proposals repeated
   the exact failed Task structure and were rejected as no-progress graph deltas.
5. The run blocked with one immutable Task and a useful non-empty Final. No ledger existed.

The controller amplification was fixed. The remaining failure begins in RWKV Task planning
and persists in RWKV's post-EOF operation choices.

## E2E-LH07 call chain

1. RWKV created ten discovery Tasks: eight service reads, the rules read, and the verifier
   read. It did not yet create mutation/report/verification Tasks.
2. The first action in each service Task correctly read that Task's declared service file.
3. After receiving each correct result, the lanes drifted one file forward: T1 selected
   service 02, T2 selected service 03, and so on. T7/T6 eventually invented service 09.
4. The execution layer accepted those cross-subject reads because evidence-subject matching
   was checked only at completion, not when an action was selected.
5. T7 entered an unchanged loop. Its replacement proposals duplicated active read Tasks;
   all were rejected, so the graph remained at ten Tasks rather than expanding to 54.
6. No migration occurred and all external checks failed. Final was non-empty but was a
   meta-level blocked response rather than a useful task summary.

The next earliest architecture defect is action-scope enforcement: a single-subject
`file_content_read` Task must not execute path-bound operations against another subject.

## E2E-H13 call chain

1. RWKV again declared checkpoint-producing phase Tasks as `file_content_read` Tasks whose
   subjects were the checkpoint output paths.
2. Phase 1 observed all four correct source files, including `doc_02` with
   `PRIORITY: yes`, but RWKV wrote an empty list. This remains a direct model value error.
3. Structural checks allowed the exact checkpoint read and RWKV committed the wrong phase.
4. Phase 2 repeated the same empty-list behavior and entered an unchanged write loop.
5. Duplicate/no-progress replacement proposals were rejected, leaving seven Tasks rather
   than expanding the graph. Remaining phases never ran.

The structural amplification is fixed. The wrong list is not controller-generated and
cannot be repaired by a format converter. The phase Task also violates the new intended
single-subject boundary because it reads corpus inputs while declaring only a checkpoint
read subject; that mismatch should be rejected before those actions execute.

## Next registered change

Enforce, at action materialization and continuation, that every path-bound operation in a
single `file_content_read` Task targets the exact RWKV-declared `evidence_subject`. A
different subject requires RWKV to use an explicit dependency, workset, or Task replacement.
This is a protocol boundary, not a content rule and not an answer selector.
