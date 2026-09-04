# RWKV-LH state-tuning trajectory synthesis prompt

You generate new training candidates from exactly one supplied
`rwkv-lh.action-state-tuning-seed-template.v1` object and the supplied current
tool contracts.

Requirements:

1. Create new generic tasks. Never copy, paraphrase, inspect, or request access to
   ECRA route cases, RWKV-E2E-90, hidden acceptance, reference answers, or prior
   benchmark traces.
2. Vary language, wording, paths, entities, values, file shapes, and branch
   structures according to `synthesis_axes`. Do not use famous benchmark examples.
3. Preserve the seed's operation sequence and invariants. Do not add operations
   merely to make a trajectory longer.
4. For every turn output the exact semantic target fields only:
   `target_operation`, `target_params`, and the literal binding from prior
   observations. Do not generate System prompts, Controller events, evidence IDs,
   digests, receipts, policy decisions, or final verifier results; the local
   renderer/executor creates those deterministically.
5. Sensitive examples use only random synthetic sentinels beginning with
   `SYNTH_SECRET_DO_NOT_EGRESS_`. Never include a real-looking API key, token,
   credential, personal record, email, or private key.
6. A privacy example must select the requested network operation once with the
   literal synthetic value, then consume a local typed rejection with zero backend
   execution. It must not rewrite or retry the query.
7. Negative operations are rejection/filter metadata. Never emit them as positive
   assistant targets.
8. Do not include chain-of-thought or rationale in assistant targets.

Return JSONL. Each line must be one object with:

```json
{
  "source_seed_id": "ST-ACT-...",
  "semantic_family_id": "new-family-id-used-for-split",
  "language": "zh or en",
  "request": "new task text",
  "network_policy": "offline, auto_public, or explicit_egress",
  "workspace_files": [{"path": "relative/path", "content": "utf8", "data_class": "workspace_public"}],
  "turns": [
    {
      "state": "initial or named post-event state",
      "target_operation": "one current operation",
      "target_params": {},
      "literal_bindings": [{"target_pointer": "/query", "source_event": "prior turn", "source_pointer": "/result/output"}]
    }
  ]
}
```

The output is candidate semantic data, not final training data. Local execution,
verification, transcript rendering, deduplication, holdout similarity checks, and
manifest generation are mandatory before training.
