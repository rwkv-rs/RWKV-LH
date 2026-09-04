# Live-network RWKV E2E V2 evaluator freeze

Frozen on 2026-08-29 (Asia/Shanghai), before any G6 checkpoint evaluation,
candidate selection, or V2 live-network execution. This document completes the
mechanical interpretation of the already preregistered V2 gates; it does not
change the frozen cases, thresholds, or acceptance rule.

## Frozen inputs

- preregistration SHA-256:
  `8fa675e5b7db26094990a7278c128be474c06c2b7145630b3115a37eeb77ecef`
- cases SHA-256:
  `d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31`
- case manifest SHA-256:
  `77572aca4d6afcfc0ba4d2c217c93d32f2b2f7476fa506fbbc44060c8dd604f4`
- frozen current-architecture V3 runner SHA-256:
  `e7f0cfdf1ae8897866204da6cf59e848c2b3d4a72752f0b721aea011666ab041`
- grounded/profile-stable V4 evaluator SHA-256:
  `2dbc1b1a0e978bea8726ad7cd46ced9b25dd05189a774002326a4717d2f8bc25`

## Fixed grounding algorithm

Only successful `web_search` or `connector_lookup` actions whose
`metadata.external_evidence.status` is `evidence_committed` and which contain at
least one record enter the evidence corpus. The corpus is serialized as sorted,
compact, UTF-8 JSON and is never rewritten into the model output.

For JSON artifacts, each field marked `grounded` is converted to text, Unicode
case-folded, and whitespace-collapsed. The resulting non-empty value must occur
verbatim in the equivalently normalized serialized committed evidence.

For text artifacts, evidence fragments are fixed contiguous five-token windows
from committed `exact_spans[].text`. A window must contain at least 24
characters and must not begin with an HTTP URL. The normalized artifact must
contain at least the case's frozen `minimum_grounded_fragments` count. The
result records only matched-fragment hashes, not a replacement artifact.

## Fixed state-stability algorithm

Every persisted model checkpoint is grouped by lane and ordered by creation
time plus checkpoint ID. Each action-lane checkpoint must carry the one expected
Executor profile pair, and each selector-lane checkpoint must carry the one
expected Selector profile pair. Both lane kinds must exist. Any adjacent profile
change, missing lane, or identity mismatch fails the case. The aggregate gate
requires zero within-run profile switches.

The inherited evaluator continues to require exact S60 requirement-byte-tail
inputs, Executor requirement/question-at-tail inputs, all 25 raw Selector
logits, raw Executor bytes and token IDs, append-only journal validity, completed
state, required network operations, committed evidence, and valid requested
artifacts. V2 passes only at 6/6 cases; one raw attempt per generation remains
fixed.
