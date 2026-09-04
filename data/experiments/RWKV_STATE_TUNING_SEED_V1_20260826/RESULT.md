# RWKV action-state tuning seed v1 result

- Date: 2026-08-26 (Asia/Shanghai)
- Protocol: `rwkv-lh.action-state-tuning-seed.v1`
- Outcome: seed package passed; expanded training corpus is not yet generated

## Existing-data decision

- `rwkv_lh_operation_selection_v1` is a historical archive for the deleted
  `lh_select_operation` protocol and is not a positive source for the current
  progressive G1i lane.
- `rwkv_lh_ecra_route_v1`, the three canonical RWKV-E2E suites, hidden
  acceptance, and reference answers remain evaluation holdouts.
- Existing R9 and historical Full90 traces are diagnostic seeds only. Failed or
  false-positive whole trajectories are not labeled positive.
- No current-protocol, execution-verified, deduplicated and holdout-clean expanded
  state-tuning corpus existed before this work.

## Delivered seed package

- 20 systemic behavioral seed families.
- Recommended minimum expansion: 1824 verified trajectories.
- 22 current Harness operation contracts plus `final_answer`, mechanically exported
  from the current registry.
- Exact progressive selector target and direct-call target blueprints per turn.
- Separate observation, protocol rejection, Network Gate, provider failure,
  mutation verification, and completion states.
- A synthesis prompt that prohibits evaluation access, chain-of-thought targets,
  invented Controller fields, real secrets, and negative-as-positive conversion.

## Holdout integrity

- Holdout request count: 210 (ECRA route120 plus canonical RWKV-E2E-90).
- Metric: `utf8-byte-ngram-cosine.v1`, UTF-8 byte 5-gram cosine.
- Exact seed-blueprint/holdout overlap: 0.
- Maximum seed-blueprint/holdout similarity: 0.5819143739626464.
- Frozen acceptance requirement: maximum `<0.75`; passed.
- Manifest records SHA-256 for all seed artifacts, the generator, current tool
  contracts, and every visible holdout task file.

## Validation

- Generator execution: passed; 20 seeds, 1824 recommended expansions, 210 holdout
  requests checked.
- Dataset/retrieval focused regression:
  `uv run pytest -q -s tests/test_state_tuning_seed_dataset.py tests/test_retrieval_harness.py tests/test_ecra_route_benchmark.py`
  — 20 passed in 4.72 seconds.
- Complete repository regression after adding the seed package:
  `uv run pytest -q -s` — 260 passed in 53.38 seconds.
- Python compilation, `git diff --check`, and trailing-whitespace checks: passed.

## Training boundary

The package intentionally stops before natural-language expansion. A synthesis
candidate becomes training data only after the current local renderer creates the
exact progressive G1i transcript, the Harness executes every action in a sandbox,
the frozen verifier accepts the local transaction, literal observation bindings are
checked, and internal/holdout deduplication passes.

RWKV-PEFT's current state-tuning example uses `--peft state --op fla` and binidx
input. The base checkpoint, vocabulary, model generation, `n_layer`, and `n_embd`
must match the deployed RWKV-7 13.3B model exactly. Training `ctx_len` is selected
for trajectory coverage and available memory rather than state-shape identity; the
serving context can remain 16384. After training, the frozen R9 Canary remains the
first gate; route120 and Full90 are not training/dev sets.
