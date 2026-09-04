# NET-SEL-2P9-S20-SHORT-DESCRIPTION preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Root cause and scope

S19-N0 proves that putting one judged function description in the same 2.9B
forward repairs the connector class on S6 dev/test, but the complete ECRA120
history still shows a broad short-natural-instruction shift.  Even after the
connector pair rejects some false positives, the old S8 query head confuses
local, deterministic, ordinary-web and connector operations.  S9 also records
the same S8 connector takeover before S19 existed.  The residual defect is
therefore the full Selector's long/template-heavy query distribution, not a
connector threshold.

S20 is a zero-learned-state data/protocol remediation for all 25 tools.  It
does not modify S8/S18/S19, the 13.3B Executor, retrieval providers, controller
permissions, generated RWKV text or any historical result.

## Exact Selector boundary

The strong planner supplies one atomic stage objective but cannot name or pick
a concrete tool.  The controller supplies the authorized menu but cannot rank
it.  The 2.9B Selector receives only:

`SelectorObjectiveV4: {"objective":"..."}`

and the frozen tool name/one-sentence description anchors.  It receives no
tool schema, arguments, result, Executor text, reasoning, answer, failure
cluster, provenance, task history or planner tool hint.  Menu projection is an
authorization boundary; raw scores of displayed candidates remain unchanged.

## Frozen data

- exactly 2,000 train, 500 dev and 500 test rows;
- all 25 labels: train/dev/test = 80/20/20 per label;
- six independent short natural frames per label: four train, one dev, one
  test; 20 distinct scenario targets per frame;
- English and Chinese frames are both present for every label;
- local-only, local-first mixed, privacy, deterministic, public-web and exact
  structured-source boundaries are covered by their owning tool rows;
- every objective, rendered query, sample id and semantic family is unique;
- train/dev/test semantic families do not overlap;
- maximum UTF-8 byte 5-gram cosine against ECRA120 is strictly below 0.75;
- source, version, purpose, hashes, generator, command, split/label/language
  counts, token bounds and generated-output count zero are recorded.

ECRA120 may be used only for contamination measurement and, after internal
selection, as a fixed seen historical regression.  It is not training data and
is not a blind holdout.

## Frozen model and head

- frozen G1i 2.9B base, zero initial state, pinned local vllm-rwkv revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- batch 1, FP16 WKV, last real input token only; query maximum 128 tokens;
- frozen zero-state S5 tool-description features and exact 25-label order;
- shared description-conditioned scorer `2560 -> 256`, query/tool projections,
  normalized interaction, one shared scalar scorer; no class-specific head;
- seed 863, AdamW `1e-3`, weight decay `1e-3`, class-balanced cross entropy,
  batch 64, 100 epochs maximum, cosine, clip 1.0, patience 15;
- best epoch by dev macro-F1, then dev loss;
- complete raw 25 logits and raw argmax only.  No threshold, calibration,
  retry, rule override, output repair or generated RWKV text.

## Frozen gates

On complete dev and test independently:

- accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- web, connector, calculator, date and time recall >= 0.85;
- local/search/web/connector boundary accuracy >= 0.85.

Only after both internal splits pass, run ECRA120 with the actual fixed
read-only menu and unchanged historical gates:

- local-only >= 24/30;
- public web >= 23/25;
- deterministic >= 14/15;
- connector >= 12/20;
- mixed local-first >= 10/20;
- privacy local-first >= 8/10;
- local-only network false positives = 0;
- required-online false-negative rate <= 0.10;
- web/connector macro-F1 >= 0.70.

Active integration additionally requires a newly frozen live canary, exact
menu authority, raw-logit retention, persistent Selector lane identity, crash
recovery, the real 2.9B-to-13.3B numbered handoff and the complete local
Harness regression.  If S20 passes without a learned state, Selector profile
count remains zero; S19-S1 cannot be promoted without its separately frozen
causal gate.
