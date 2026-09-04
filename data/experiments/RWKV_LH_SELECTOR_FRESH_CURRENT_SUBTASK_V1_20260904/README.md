# Selector fresh current-subtask v1

Date: 2026-09-04

Purpose: remove cross-call Selector WKV accumulation and make the three menu-order votes independent evaluations of one Planner current subtask.

Root cause: the service accepted a parent checkpoint, replayed only the next delta, persisted the resulting recurrent state, and the model kept three lane heads. Token position therefore grew across actions even though Selector history was not part of its responsibility.

Frozen runtime contract:

- 23 executable operation labels; no `final_answer` or `ABSTAIN` class.
- Input contains only `current_subtask`, eligible labels, and one menu permutation.
- Every service request contains a complete bootstrap plus one current-subtask step.
- Every extraction uses `parent_state=None`, `continuation=False`, and does not export the transient state.
- Three menu-order evaluations vote after independent forwards; no Selector lane head is stored.
- Finalization is controlled by the completed plan and auditors, not selected as a tool class.

Validation plan:

1. Compile every tracked Python source.
2. Run the complete repository pytest suite with the frozen local environment.
3. Assert the reference current-subtask input is `725 / 725 / 727` tokens for the three menu orders and below the 4096-token limit.
4. Search source and tests for retired parent-state, ABSTAIN, 25-class, and v1 Selector protocol symbols.
5. Do not run StateTune or a real model experiment in this change.

Environment limitation: local `.venv` does not install optional Torch, so Torch-only initial-State injection and fused-feature execution tests may be skipped; their non-Torch contracts remain covered.
