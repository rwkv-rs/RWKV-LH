# Round71 preregistered protocol: compact decision boundaries and open Tasks

## Frozen evidence

- Uploaded Round46 full90 baseline: Strict `31/90`, External `32/90`, Agent
  `55/90`, FP `24`, FN `1`.
- Round70 unchanged fixed15: Strict/External/Agent `1/15`.
- Manual source analysis:
  `data/experiments/Round70_canary/MANUAL_CAUSAL_ANALYSIS.md`.

## Preregistered changes

1. **Review recency:** action review renders bounded history first and repeats one
   compact exact decision packet immediately before the fixed `review_action`
   response boundary.
2. **Open Task semantics:** Task commitment uses `pass|open`. An open decision
   means the successful action did not yet establish the entire postcondition.
   Both decisions may cite any distinct registered evidence refs; the runtime
   never requires refs to be empty based on the decision.
3. **Single evidence namespace:** Task-decision context removes non-selectable
   artifact/observation ref labels outside AVAILABLE EVIDENCE. Values and
   observations remain visible.
4. **Closed common wire forms:** normalize only (a) a fixed tool name used as
   the sole object key with argument object value, and (b) a uniquely selected
   tool name plus its declared arguments inline. Conflicts, unknown fields and
   non-fixed boundaries remain rejected and audited.
5. **Retry placement:** Goal proposal and Goal audit invocation/parsing are
   inside the existing three-attempt loops. Truncated output is retried; missing
   semantic fields are never reconstructed.
6. **Quality limits:** `noop` is hidden from model action catalogs and recovery
   task batches may use the existing 32-Task global batch limit rather than the
   four-Task efficiency cap.

Independent-ready-Task continuation is deferred unless source inspection shows
it can be changed without altering terminal/failure semantics in this round.
Plan self-review is also deferred to a separately measured round so that the
causal effect of the more foundational decision-boundary fixes remains visible.

## Non-intervention

- Every Goal, Task, action, review decision, evidence selection and final answer
  remains RWKV output.
- The boundary changes only representation, state projection, retry behavior
  and capacity. It does not infer values, add Tasks, choose actions, flip
  decisions or repair model content.
- Hidden acceptance and frozen reference answers remain unavailable to model
  calls.

## Validation and gate

- Full pytest, LH-Control `30/30`, frozen subset `5/5`, compile/diff checks.
- New tests for review packet order, open-with-evidence, exact ref projection,
  the two closed wire forms, Goal retry and recovery >4.
- Unchanged fixed15 gate: Strict `>=6`, FP `<=3`, FN `<=1`, and B01/B02/B10
  strict before full90.
- Upload only if full90 Strict exceeds `31/90`, External does not regress below
  `32/90`, FP improves below `24`, FN remains `<=1`, and output
  non-intervention remains exact.
- Efficiency metrics are recorded but are not gates.
