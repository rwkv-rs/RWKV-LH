# Round90 Task evidence-contract canary preregistration

## Purpose

Re-run fixed cases `E2E-B01/B02/B03/H04` to test the Round89 H04 false-positive
root fix. No hidden acceptance, expected value, answer, operation, argument, or
completion choice is exposed or inferred by the controller.

## Only architecture difference from Round89

Every RWKV Goal-lane Task proposal must declare one structural `evidence_kind`:
`workspace_change`, `content_observation`, `collection_observation`,
`command_observation`, or `outcome_observation`. The Task runtime accepts
`lh_task_done` only when that Task's own real Attempt/chunk/workset records contain
the declared class. The controller does not derive the class from natural
language and does not check an answer value. The existing independent read after
mutation remains required.

This should reject H04's Round89 `list_directory -> task_done` sequence if the
model declares its create Task as `workspace_change`, without globally forbidding
directory-listing tasks.

## Frozen implementation/runtime

- Branch/base: `chase/g1i-tool-protocol` / `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- schema `31a412f231724b2641a10e09e61b8d8a9d09b3468cda3efac6c87983ec00c618`
- model `14f34955f0dcbf047a1a4d98cef9663a3cae06353ead3fa19f14940bb4dc6456`
- model_io `7b1bda629d0530cfdd3ca403c546c86e76349c4ed57c4d60c8cab870d14ca713`
- model_session `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- controller `afd0bc9afc3f22e516aaa3cd70a2e9d2f711e50c48e0c1c4207dd81b26f8c794`
- harness `691e610af6d4a3dbcc558bfdd97570933b736c5ce98240d5c8985423063a2021`
- task_graph `c55983b427b6c953913d2f4e32e7371ca922e8501fddd6e704a9b46d924a6f0d`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- focused `43 passed`; full offline `88 passed`.
- Endpoint/model unchanged: `http://127.0.0.1:29610/v1`,
  `rwkv7-g1i-13.3b-20260805-ctx16384`.
- Concurrency `1`, max transitions `200`, fixed sampling unchanged.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round90_task_evidence_contract_canary \
  --max-transitions 200 --concurrency 1
```

## Fixed evaluation

Inspect every proposal and call. Record emitted evidence_kind, Strict/External/
Agent, FP/FN, attempts, terminal-answer nonempty/raw equality, and whether every
accepted Task completion has a matching Task-owned structural observation. No
changes before completion.
