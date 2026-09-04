# NET-SEL-2P9-S26 current-Harness identifiable-trajectory 2K result

Date: 2026-08-28 (Asia/Shanghai)

## Disposition

Rejected by the frozen subgroup gates.  The zero-state S26 head is not
integrated and was not run on S23.  It remains the corrected current-architecture
baseline and the only admissible source for the separately numbered S27
2.9B Selector state-tuning experiment.

## Frozen identities

- S26 cases SHA-256:
  `4a01c16a2e320e7754529544ea0299e5abdd6015b0b079c78c1f7d9ab24e4465`;
- feature manifest SHA-256:
  `e600921251f22b86cf8d88df8300ab8f61ff3ff056ba1fa1fe710b7c1b289713`;
- training summary SHA-256:
  `03f6bab761982b38c08df609b51f206ac4d95398e7c003586932ffd2f9741cf3`;
- report SHA-256:
  `3802a4cf956e5c1c663131884dacc3fd0f0c54686038e8e14eb8c151791a9228`;
- head file SHA-256:
  `047c0653a07bc397da90fc8ef242b38e377287befb62ecbed4e7bdaab2b7c02b`;
- head hash:
  `b405004a50772c612fb6606178d48bfc9113161fca6c499693e9ff3fd83938e7`;
- physical device: GPU0;
- 2.9B initial Selector state: exact zero.

All 3,000 rows were extracted with one bootstrap followed by zero, one, or two
registered historical Selector steps and the current step through the same
persistent WKV state.  Only the current-step mean hidden was classified.  No
RWKV text was generated, no sampler ran, and every prediction retains all 25
raw logits and the unmodified raw argmax.  There was no threshold, mask,
postprocessing, retry, repair, or Executor fallback.

## Metrics

| split | accuracy | macro-F1 |
|---|---:|---:|
| train | 0.9870 | 0.9869 |
| dev | 0.9280 | 0.9261 |
| blind test | 0.9040 | 0.9021 |

Blind-test subgroup accuracy:

- first decision: 0.888;
- one-action continuation: 0.945;
- two-action continuation: 0.820;
- English held-out surface family: 0.824;
- Chinese held-out surface family: 0.984;
- frozen five-way search boundary: 0.840.

Overall accuracy and macro-F1 passed.  The all-class recall gate failed on
`read_file` (0.45) and `check_command` (0.65); the new-operation gate failed on
`web_search` (0.75).  The five-way boundary, phase, and language gates also
failed.  S23 therefore remains untouched.

## State-tuning justification

Unlike S24/S25, S26 labels are identifiable from the literal current request,
all continuations replay the actual persistent Selector lane, every class has
80 training rows, English and Chinese are balanced, and test paraphrase
families are absent from training.  The remaining failures are concentrated in
unseen English wording, longer recurrent trajectories, and the
local-read/public-web boundary.  They justify one new initial-WKV state trained
only on the frozen 2,000 S26 train trajectories.  The 13.3B Executor state and
all Harness behavior remain out of scope.
