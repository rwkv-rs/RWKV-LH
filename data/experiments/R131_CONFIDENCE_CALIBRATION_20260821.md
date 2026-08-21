# R131 — Final-Operation Confidence Calibration

**Recorded:** 2026-08-21, before R131 implementation and Full90.

## Source and purpose

This is a read-only calibration over the source-frozen repaired canonical run
`R130_canonical_repaired_full90_20260820`. It determines one population-level confidence threshold
for R131. It does not change the RWKV-E2E-90 data, hidden acceptance, scoring, sampling parameters,
or case selection.

- source `results.json` SHA-256:
  `c67133adb21261eadc23e3a8ef47bb276d724a383645811243495d7b46853166`
- calibration script:
  `/home/chase/GitHub/RWKV-LH/temp/calibrate_r131_final_confidence_20260821.py`
- population: the 64 normal action-lane `final_answer` prompts from the repaired run (35 TP, 29 FP);
  interrupted/forced terminal-boundary Finals are excluded because R131 will never defer them.
- replay parameters: the frozen model and sampling values, canonical prompt replay, `logprobs=5`.
  The confidence metric only uses `token_logprobs`; requesting one top logprob in R131 is equivalent
  for this metric.

## Metric and label-blind selection

Metric = arithmetic mean of token logprobs for every generated token whose character interval
overlaps the literal `final_answer` operation name in the raw JSON output.

Of 64 replayed prompts, 63 again selected `final_answer`; one (`E2E-LH12`, archived FP) selected
`read_file` and is excluded from the numeric quantile. Forty-one raw outputs were byte-identical to
the archived output. The operation name occupied three tokens in every measured replay.

The threshold is the linearly interpolated empirical p10 of the 63 metrics, selected **without
category labels**:

| Quantile | Mean operation logprob |
|---|---:|
| min | -0.5183379995238889 |
| p05 | -0.4291867521165841 |
| **p10** | **-0.40040510160761184** |
| p15 | -0.3755443655785712 |
| p25 | -0.35394603598706453 |
| p50 | -0.27072757205617864 |
| p75 | -0.16197614483159367 |
| max | -0.012972046836997228 |

Locked candidate rule: defer iff `metric < -0.40040510160761184`.

## Post-selection label audit (not used to move the threshold)

Seven calibration rows fall below p10: five archived FP (`M06`, `H08`, `M15`, `M23`, `M26`) and
two archived TP (`B08`, `M11`). This weakly supports a useful screen but also exposes the central
risk: operation confidence is not correctness confidence. R131 must retain the two at-risk TP and
show a mechanism-attributable FP→TP; otherwise it is reverted. No threshold search or label-based
optimization is permitted after this record.

