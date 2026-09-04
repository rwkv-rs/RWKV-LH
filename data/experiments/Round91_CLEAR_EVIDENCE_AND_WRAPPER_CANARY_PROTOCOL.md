# Round91 clear-evidence and wrapper-normalization canary preregistration

Fixed cases, endpoint, sampling, concurrency `1`, and max transitions `200` are
unchanged from Round90.

Registered differences only:

1. Evidence kinds are renamed to explicit outcomes:
   `workspace_mutation`, `file_content_read`, `collection_listing`,
   `command_execution`, `expected_outcome`. Runtime meaning is unchanged.
2. The common flattened Task wrapper
   `function=lh_task_call + task_id + operation_arguments{operation,operation_args}`
   and nested wrapper where `operation` is inside `operation_args` normalize to
   canonical `params`. Every semantic value must already exist in RWKV output;
   raw bytes remain audited and no field is inferred.

Frozen hashes: schema `2c270ef7...b6b200`, model `14f34955...dc6456`,
model_io `28a38605...1fd88`, model_session `f4c9a6a3...f45c`, controller
`de2f09be...1c793`, harness `691e610a...a2021`, task_graph
`517cd37e...b1f45`, runner `2df02384...d6960`. Focused `44 passed`, full
offline `89 passed`.

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round91_clear_evidence_wrapper_canary \
  --max-transitions 200 --concurrency 1
```

Inspect all raw calls/normalization/capsules. Record Strict/External/Agent,
FP/FN, evidence-kind choice, answers nonempty/raw equality and whether B03's
first complete write call executes. No changes before completion.
