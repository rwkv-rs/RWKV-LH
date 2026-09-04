# NET-SEL-2P9-S22 atomic-objective regression preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Purpose

S22 evaluates the already frozen S21 head on historical atomic stage objectives,
not complete ECRA user tasks.  It measures the Selector boundary after Planner
atomization and before Executor schema disclosure.

The source is the complete S6 query corpus, SHA-256
`d60ad4a2404fda0f9401a5858070bb5e3063d408be68c9f88e1c0431eed1313c`.
Its objective text, label, split, source identity and natural failure cluster are
unchanged.  A mechanical projection removes role/progress fields and renders
only:

`SelectorObjectiveV4: {"objective":...,"schema_version":"rwkv-lh.selector-objective.s20.v1"}`

No ECRA instruction, tool schema, argument, result, Executor text, answer or
reasoning enters the input.

## Frozen candidate

- S21 head SHA-256:
  `73a0c029ddc14ae6681b6a9e543ac0bf5009e62bc146d32d14679924a0310a5f`;
- 2.9B model SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- zero learned state;
- feature: arithmetic mean of all real-token final-layer hiddens;
- feature protocol: `rwkv-lh.vllm-rwkv-final-hidden-mean.v1`;
- raw 25 logits and raw argmax only;
- S21 weights, tool-description anchors and temperature 1.0 unchanged;
- generated RWKV text and sampling invocations: zero.

All 9,076 rows are external to S21 training.  They are a seen historical corpus
for the project, not a blind holdout.  No new head/state may be selected from
their results.

## Gates

On the complete S6 dev (926) and test (750), independently:

- accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- `web_search`, `connector_lookup`, `calculator`, `date_diff`, and
  `current_time` recall >= 0.85;
- boundary accuracy >= 0.85.

On all 176 registered natural dev rows:

- overall accuracy >= 0.90;
- every failure cluster accuracy >= 0.80;
- local-only and deterministic rows must have zero network false takeover;
- privacy-local-first must have zero network false takeover.

Failure rejects full replacement but does not invalidate S21's internal mean
ablation or authorize tuning on ECRA.  Passing permits a fresh post-freeze
Planner/Selector/Executor canary; it does not itself authorize integration.
