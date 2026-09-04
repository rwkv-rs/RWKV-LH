# NET-SEL-2P9-S19-CONNECTOR-S1 function-state preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Root cause and candidate

S18 passed its internal distribution but failed the fixed ECRA history by
classifying most short natural requests as connector.  Its binary function head
received only a generic compact task hidden; the judged function description
was outside that RWKV forward.  The failure is therefore an input/function
alignment defect, not evidence that a threshold or wider class head is needed.

S19 renders each row as one compact pair containing only:

- the atomic stage objective;
- `connector_lookup` name and its frozen one-sentence description;
- no schema, arguments, tool result, Executor text, reasoning, answer or other
  tool description.

It compares zero learned state (`S19-N0`) with one connector-specific 2.9B
learned state (`S19-S1`) using the same data, prompt, feature, head, parameters
and gates.  A state is retained only for a preregistered causal net benefit.

## Data and state tuning

- source selection: the exact 2,000 S18 rows, SHA-256
  `1983f1b0c2195eadf08b17a1747ac863225d09c7d3f80f59e29453c0da76c662`;
- train: 2,000, CONNECTOR/OTHER = 690/1,310;
- dev: all 926 untouched S6 dev rows, including all 176 registered natural
  residual rows; no S6 test or ECRA row enters training/head selection;
- target suffix: `FunctionLabelV1: CONNECTOR|OTHER` with exact suffix loss;
- G1i 2.9B zero base, BF16, batch 1, FLA, state PEFT, DeepSpeed stage 1,
  gradient checkpointing, BOS 0, context 512;
- exactly 2,000 optimizer steps, seed 857, LR `2e-5 -> 4e-6` cosine, warmup 40,
  checkpoints 500/1000/1500/2000; final 2000 is selected unless invalid;
- checkpoint orientation, shapes, dtype, finiteness, nonzero values, model and
  state SHA-256 must pass before local extraction.

The generator must record sources, version, purpose, prompt/target hashes,
token bounds, family isolation, ECRA similarity identity, generation command
and generated-output count zero.  Training does not sample or retain RWKV text.

## Frozen Hidden/MLP comparison

For both N0 and S1:

- batch 1, FP16 WKV, final hidden at last real input token only;
- MLP `2560 -> 128 -> 2`, train-only mean/std, GELU, LayerNorm, dropout 0.1;
- class-balanced cross entropy, seed 859, AdamW `1e-3`, weight decay `1e-3`,
  batch 64, maximum 80 epochs, cosine, clip 1.0, patience 12;
- best epoch by connector dev F1 then dev loss;
- raw two logits and raw argmax only.

No mean/prefix/WKV feature sweep, threshold, calibration, retry or output repair
is allowed.  Complete logits from both N0 and S1 are retained.

## Gates and state causality

On complete dev and each natural cluster:

- connector recall/precision >= 0.90;
- OTHER recall >= 0.95;
- natural connector recall >= 0.95;
- mixed/privacy false connector rate <= 0.02.

S1 may beat N0 only if it changes at least three dev decisions, has at least
three net exact rescues, regresses at most one previously exact row and passes
every gate.  If N0 passes and S1 has no registered causal benefit, deployable
profile count remains zero for this function.

The S6 test and ECRA120 are fixed seen regressions, not blind holdouts.  They
may run only after dev candidate selection and may not change the artifact.
Active routing additionally requires a newly frozen live canary after protocol
implementation, exact menu authority, raw-score retention, persistent
function-lane identity, crash recovery, real 2.9B-to-13.3B handoff and full
local Harness regression.

S19 cannot modify S8/S18, the 13.3B Executor profile or any RWKV generated
output.  All N0/S1 failures and checkpoints remain append-only under their own
numbers.
