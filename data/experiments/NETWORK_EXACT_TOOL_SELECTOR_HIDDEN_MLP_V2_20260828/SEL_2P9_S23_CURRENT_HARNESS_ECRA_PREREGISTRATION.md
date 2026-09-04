# NET-SEL-2P9-S23 current-Harness ECRA preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Question

Evaluate Selector candidates at the actual current direct-Harness boundary,
not on whole-task raw text alone and not on future Planner atoms.  Each ECRA
case begins with the immutable request and frozen 25-name/description menu.
Continuation decisions advance the same per-case 2.9B recurrent state with the
registered compact operation/outcome projection.  The 13.3B Executor schema,
arguments, raw results and text are excluded.

The frozen labels are the registered ECRA expected operation sequence followed
by `final_answer`.  A continuation row exists only where the historical 13.3B
direct run produced the correct preceding operation(s), so its recorded result
can be projected without inventing an observation.  The historical next
operation at every included decision point is scored on the same rows as the
retention baseline; it is not used as ground truth.

## First diagnostic candidate

- S21 head file SHA-256
  `73a0c029ddc14ae6681b6a9e543ac0bf5009e62bc146d32d14679924a0310a5f`;
- 2.9B model SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- zero learned Selector state;
- current-segment mean hidden, with the full task/menu processed into the same
  recurrent state before the first step feature;
- complete raw 25 logits and raw argmax; no masking, repair, fallback,
  generation or sampling.

S21 was selected on a different internal objective corpus, so this is an
external architecture-fit diagnostic.  Failure cannot be used to change S23
labels, rows, similarity, or gates and does not authorize integration.

## Frozen gates

- all-row exact accuracy must be at least the historical direct baseline;
- first and continuation accuracy must each be at least their corresponding
  historical baseline;
- each ECRA category accuracy must be at least its historical baseline;
- local-only network false takeovers must be zero and no greater than baseline;
- required-online false negatives must be no greater than baseline;
- every emitted record contains 25 finite raw logits and raw argmax is the
  selected class;
- generated RWKV text, sampling calls, logit postprocessing and Executor
  fallback must all equal zero.

Passing permits a full live direct-Harness canary, not deployment.  Failure
starts a fresh S23 training/state-tuning experiment using separately registered
training data; this ECRA decision set remains evaluation-only.

