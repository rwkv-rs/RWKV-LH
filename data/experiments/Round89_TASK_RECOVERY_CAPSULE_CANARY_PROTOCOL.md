# Round89 Task recovery-capsule canary preregistration

## Purpose and fixed cases

Re-run the unchanged diagnostic set `E2E-B01`, `E2E-B02`, `E2E-B03`,
`E2E-H04` after the two remaining cross-case fixes derived from Round88 manual
call inspection. Sampling, endpoint, evaluator, concurrency and transition budget
remain fixed.

## Registered differences from Round88

1. Task format normalization accepts the two common G1i representations only:
   canonical `lh_task_call(task_id, operation, operation_args)`, or a direct
   displayed operation whose params themselves contain an explicit RWKV-emitted
   `task_id`. Direct calls without `task_id` remain invalid. The adapter never
   infers task identity, operation, or operation argument values.
2. An unchanged/repeated failed transition rebuilds the same Task lane from a
   deterministic recovery capsule containing the immutable Goal, active Task,
   fixed operation catalog, workset, all recent authoritative Attempt
   observations and the rejected transition. Prior Assistant-call bytes are
   archived but excluded. The rebuild makes zero semantic requests and chooses
   no replacement operation.

## Frozen implementation

- Branch/base: `chase/g1i-tool-protocol` / `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- schema: `bf3baec36a407006ac7ff5b0317d8c7d1b99420aa44bfa1f357df6fcd5ff83c8`
- model: `d9c1b9249a37249e290f33d5898cf8892bff8011c923fd5dc9b63f0c4e8a9198`
- model_io: `11c1f3f25e69b77032b59d6bd668f2004eaf14518c69f370986b3ab1e456c753`
- model_session: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- controller: `d33c37fa77642dd4f8520b9efc1aab19df4c40894dd440ad7b4c1b969a518e48`
- harness: `691e610af6d4a3dbcc558bfdd97570933b736c5ce98240d5c8985423063a2021`
- runner: `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- focused `42 passed`; complete offline `87 passed`.
- Endpoint/model: `http://127.0.0.1:29610/v1`,
  `rwkv7-g1i-13.3b-20260805-ctx16384`.
- Concurrency `1`, max transitions `200`, unchanged fixed sampling.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round89_task_recovery_capsule_canary \
  --max-transitions 200 --concurrency 1
```

## Fixed evaluation

Inspect every raw call and capsule. Record Strict/Agent/External, FP/FN, attempts,
answer non-emptiness/raw equality, direct-call normalization, and whether rejected
Assistant bytes occur in the rebuilt prompt. No code/evaluator change is allowed
until completion.
