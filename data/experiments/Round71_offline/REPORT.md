# Round71 offline validation report

## Result

- Complete pytest: `430/430` passed.
- LH-Control: `30/30` passed.
- Frozen catalogs/reference plus 31-file architecture subset: `5/5` passed.
- Compileall and `git diff --check`: passed.

## Round71-specific coverage

- A successful action whose full Task postcondition is unmet uses RWKV decision
  `open`. Open decisions may retain registered evidence refs; no result-dependent
  empty-ref rule can pressure the decision toward pass.
- Task-decision causal history preserves observations, paths and hashes while
  removing non-selectable `observation_ref` and `artifact_ref` labels. AVAILABLE
  EVIDENCE is the only selectable namespace.
- The exact current action-review packet is rendered after bounded history and
  immediately before the fixed review call.
- Fixed tool-name-key, fixed `type+arguments`, and declared bare arguments for a
  uniquely selected tool normalize with raw/normalized digests. No semantic
  field is generated, dropped or changed.
- Goal proposal and audit JSON/protocol failures are caught inside their
  three-attempt loops. Truncated semantics are not reconstructed.
- `noop` remains executable for explicit internal/test Tasks but is absent from
  the model-visible default catalog.
- Recovery accepts 5 Tasks and rejects 33 at the shared 32-Task safety bound.

The protocol normalizer is `transparent-protocol-boundary.v10`.

## Dataset record

- Source/version: Round71 repository tests, frozen E2E-90 catalogs/reference,
  31-file architecture fixture and LH-Control-30.
- Purpose: validate compact decision boundaries, non-coercive open semantics,
  one evidence namespace, retry placement and quality-oriented capacity before
  live fixed15.
- Generation: full pytest; fresh
  `data/experiments/Round71_offline/lh_control_30`; frozen five-test subset;
  compileall; diff check.
- LH-Control result SHA-256:
  `234fd696c86ba20079544adf76b8669e94195da478d74b559376e8be82683129`.
- No hidden acceptance result or frozen reference answer was available to model
  generation.
