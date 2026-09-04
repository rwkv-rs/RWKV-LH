# NET-SEL-2P9-S26 current-Harness identifiable-trajectory 2K preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Architecture boundary

S26 is a corrected offline baseline for the already implemented product
architecture.  It does not introduce a Planner or change the Harness:

`LongHorizonModel -> independent 2.9B exact-tool Selector -> one disclosed
tool schema -> persistent 13.3B Executor -> Harness`.

The Selector sees the immutable literal request, all 25 tool names and compact
descriptions, the generic `CurrentDirectStageV1`, and only bounded latest-action
facts.  It never sees parameter schemas, arguments, full results, Executor
text, references, or generated RWKV text.  Selector and Executor learned
profiles and dynamic recurrent states remain separate.  An independent
Selector failure is fail-closed; the old 13.3B selection route is not a
fallback.

## Why S24/S25 cannot be reused

S24/S25 removed a legacy label-bearing stage objective but retained labels
that were not always identifiable from the remaining high-level request.  The
whole 250-row balanced test used those rows.  Their feature extractor also
bootstrapped every continuation independently, whereas the product service
bootstraps once and advances later steps from the prior Selector WKV state.
S26 corrects those two input-contract defects; it is not allowed to change the
mean-hidden feature, MLP, tool menu, raw argmax, or current runtime projection.

## Frozen dataset construction

The generator must create exactly 2,000 train, 500 development, and 500 blind
test decision points: respectively 80/20/20 rows for each of all 25 labels.
Within every label and split, half the literal requests are English and half
are Chinese.

English operation-intent surfaces are taken only from the frozen v2.4
operation-contract fixtures, SHA-256
`78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc`.
The explicit legacy `stage_objective` is promoted to the immutable literal
request; it is not retained as a hidden current-stage field.  Chinese surfaces
are deterministic, independently authored translations of the same frozen
tool responsibility contract.  No ECRA instruction, historical prediction,
Executor output, or model-generated text may enter a request.

For both languages, six paraphrase families are frozen per operation.  Families
0-3 are train-only, family 4 is development-only, and family 5 is test-only.
Unique entity/path identifiers and exact semantic-family ids may not cross
splits.  Exact rendered-input duplicates and cross-split family overlap must be
zero.

Every 40-row language/label train block contains 20 first decisions, 16
one-action continuations, and four two-action continuations.  Every 10-row
development or test block contains five, four, and one respectively.  A
continuation stores all prior Selector steps needed to reconstruct its state.
The literal request explicitly orders prerequisite operations before the
current operation, so the current label remains identifiable without result
content.  `final_answer` is valid only when its request says no operation is
needed or all explicitly ordered prerequisites have succeeded.  `ABSTAIN` is
valid only for an ambiguous, unsupported, unsafe, or under-observed current
request.  Each current and historical step is rendered by the product
`build_network_selector_input` path.

The complete S23/ECRA120 set, SHA-256
`7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a`,
is evaluation-only.  UTF-8 byte 5-gram cosine similarity over literal
`task_request` has an exclusive 0.75 ceiling against every ECRA instruction.
The fixed generator must abort instead of editing a row after this check.

## Frozen serving and head baseline

- physical GPU0 only;
- local modified vLLM-RWKV engine revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- 2.9B model weights SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- initial Selector state: exact zero;
- bootstrap once per decision-point trajectory, then replay every registered
  historical step and current step through the same persistent state;
- classifier input: mean final hidden over only the current step segment,
  protocol `rwkv-lh.vllm-rwkv-final-hidden-mean.v1`;
- no text generation or sampling;
- MLP 2560 -> 256 -> 25, GELU, LayerNorm, dropout 0.2;
- class-balanced cross entropy, seed 829, batch 128, AdamW LR 1e-3,
  weight decay 1e-3, maximum 60 epochs, patience 10;
- epoch selection uses development loss only; blind test is read once after
  selection;
- all 25 raw logits and the unmodified raw argmax must be retained.

## Frozen internal gates

The candidate must satisfy all gates on the 500-row blind test:

- accuracy >= 0.90;
- macro-F1 >= 0.90;
- recall >= 0.75 for every class;
- recall >= 0.85 for each of `web_search`, `connector_lookup`, `calculator`,
  `date_diff`, and `current_time`;
- search boundary accuracy >= 0.85 across `web_search`,
  `connector_lookup`, `search_text`, `read_file`, and `read_json`;
- first, one-action continuation, two-action continuation, English, and
  Chinese accuracy each >= 0.85;
- zero generated text, sampling, logit postprocessing, retry, class mask,
  threshold, output repair, or Executor fallback.

Only an internally passing immutable candidate may run once on frozen S23,
where it must be compared with the historical 13.3B direct route at the same
245 valid decision points.  If the corrected zero-state baseline fails, S23
remains untouched; its fixed failure clusters may justify a separately
numbered 2.9B state-tuning experiment using only the 2,000 S26 train rows.
