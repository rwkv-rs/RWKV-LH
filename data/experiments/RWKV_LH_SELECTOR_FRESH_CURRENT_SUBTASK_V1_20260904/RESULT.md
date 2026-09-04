# Validation result

Date: 2026-09-04

Status: architecture and non-model regressions passed; StateTune and real-model evaluation were intentionally not run.

Validated production chain:

1. Planner frontier projects only `objective`, `phase`, `read_roots`, `write_roots`, `success_evidence`, and `constraints` into Selector input.
2. `canonical`, `rotate_8`, and `rotate_17` are three complete independent requests with `parent_state=None`, `continuation=False`, and `export_state=False`.
3. The Controller aggregates the three 23-class results and creates one staged operation handoff.
4. Executor receives that fixed operation and its single tool schema; an argument-protocol retry consumes the same handoff and does not invoke Selector again.
5. `final_answer` is produced only after plan completion by Finalizer and checked by Final Auditor; it is not a Selector class.

Commands and results:

```text
python -m pytest -q
525 passed, 3 skipped in 43.41s

python -m scripts.run_rwkv_e2e_benchmark --suite all --validate-only
suite=RWKV-E2E-90 tasks=90 selected=90 catalog_valid=true

python -m compileall (repository Python sources)
passed

git diff --check
passed
```

The three reference menu inputs were measured with the current RWKV tokenizer as `725 / 725 / 727` tokens. All are below the service limit of 4096 tokens and do not grow across actions.

The three skips require the optional local Torch runtime and cover State injection/fused tensor execution. Their protocol paths are covered by non-Torch tests; they must be executed on the model server before publishing a trained State/Head pair.

No StateTune dataset was generated, no training was started, and no old Head was accepted as compatible with the new protocol.
