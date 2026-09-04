# Round82 protocol-envelope normalizer recovery

## Scope

This change restores only the semantics-free model-call envelope boundary removed
by the unified architecture rewrite. It is not an answer repair layer and does not
participate in operation selection, parameter construction, verification, scoring,
or final-output delivery.

The accepted input shape is exactly one top-level operation-name key
(`function`, `name`, or `tool`) and exactly one top-level argument-object key
(`params`, `arguments`, or `args`), with no additional top-level fields. The
internal representation is always `function+params`.

Frozen invariants:

- preserve the emitted operation-name value;
- preserve the complete argument object;
- never infer, add, remove, rename, or coerce a semantic field;
- reject ambiguous keys, extra top-level fields, event echoes, non-object params,
  empty output, and malformed/truncated JSON;
- retain the exact RWKV raw output in the candidate transcript;
- record changed input and normalized payloads, their digests, and
  `controller_semantic_fields_generated=false`.

## Round81 complete-output replay

Command:

```bash
uv run python /home/chase/GitHub/RWKV-LH/temp/replay_round81_protocol_normalizer.py
```

All 1,530 recorded RWKV outputs from the fixed E2E-90 run were replayed:

| Source shape | Count | Result |
|---|---:|---|
| `function+params` | 1,501 | accepted unchanged |
| `function+arguments` | 19 | normalized to `function+params` |
| model-event echo | 1 | rejected |
| empty, truncated, or otherwise non-object output | 9 | rejected |

The 19 recovered payloads occurred in 19 distinct cases. Comparing the source
`function` and complete source `arguments` object to the normalized command found
`0` semantic mismatches.

This establishes only that the 19 pure envelope failures are repaired. It does
not reclassify the other Round81 protocol failures: direct operation calls while
the two-stage selector was required, wrong operation names, invalid operation
parameters, and truncated outputs remain separate architecture/model issues.

## Regression

```text
uv run pytest -q -s
79 passed in 10.73s
```

Targeted `tests/test_model_session.py`: `14 passed`. Tests cover canonical input,
three common envelope spellings, ambiguous and extra fields, event echo,
non-object params, exact raw transcript preservation, and normalization audit.

`ruff` was not available in the project environment, so the files were checked
with Python bytecode compilation and the complete pytest suite instead.
