# NET-SEL-2P9-S8 result

Date: 2026-08-28 (Asia/Shanghai)

S8 is rejected before ECRA.  The immutable artifact is retained only as an
experimental input for a separately preregistered function-scoped takeover.

## Frozen result

- artifact SHA-256:
  `36728736ce539039f5af132872edbf0f179aa66112ce57dbf16a578cf2586c23`
- natural dev: 176/176; every registered natural cluster is 1.0
- full-coverage test accuracy: 0.9066666960716248
- full-coverage test macro-F1: 0.9058760475913512
- boundary accuracy: 0.8777777552604675
- minimum per-class recall: `read_file` 0.70, below the fixed 0.75 gate
- `connector_lookup` recall: 0.7666666666666667, below the fixed 0.85 new-tool
  gate

The exact S8 pre-ECRA gate therefore fails.  The S8 experiment does not read
ECRA and does not replace the product Selector.  No additional source-weight
sweep is permitted under the S8 protocol.

