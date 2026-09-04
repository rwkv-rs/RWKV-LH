# NET-SEL-2P9-S10-GATE preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Purpose

S10 is a function-scoped 2.9B Hidden+MLP takeover gate, not a broad tool
replacement and not a learned RWKV state.  It emits exactly one of
`web_search`, `connector_lookup`, or `DEFER`.  Only the first two values permit
the independent Selector to take over.  `DEFER` preserves the current 13.3B
path and therefore prevents a networking change from deleting local project,
command, repair, or finalization capability.

After selection, function-scoped Executor profiles may be trained as
`NET-EXE-13P3-N1-web_search` and
`NET-EXE-13P3-N2-connector_lookup`.  A function profile is never chosen before
the tool identity is committed.

## Frozen data and projection

- Source: `rwkv_lh_state_router_2k_v1/samples.jsonl`, 2,000 rows, SHA-256
  `b345e98f0e58fe291767218f7c27da6c766a100145193f0e4be46051896de29f`.
- The source is frozen from historical failures and explicit system
  boundaries.  Its registered ECRA/E2E maximum UTF-8 byte-5gram cosine is
  0.4703572224332457, below the fixed exclusive 0.75 threshold.
- Projection keeps only `input.request` as objective and controller facts
  `mode`, `evidence_state`, and `policy_state` as progress.
- It appends exactly three frozen name/description records.  No parameter
  schema, Summary, result, history, rationale, source metadata, expected label,
  workspace listing, or Executor state/text is rendered.
- Source rows with identical rendered input are deterministically deduplicated
  by first source order.  Contradictory duplicates are forbidden.  Semantic
  families and original train/dev/test splits are retained.
- Source route `web` maps to `web_search`, `connector` maps to
  `connector_lookup`, and every other route maps to `DEFER`.

## Frozen model and head

- Model: pinned local RWKV7-G1i 2.9B through the clean local vllm-rwkv engine.
- Initial profile: zero.  Generated RWKV text and sampling are forbidden.
- Candidates: final-layer last-real-token and real-token mean from the same
  forward pass; maximum 384 tokens; batch size 1 for parity with service.
- Head: per-feature normalization, Linear(2560,256), GELU, LayerNorm, dropout
  0.2, Linear(256,3); inverse train-class-frequency cross entropy.
- Seed 829, AdamW lr 1e-3, weight decay 1e-3, batch 64, at most 60 epochs,
  patience 10.  Best epoch uses dev macro-F1 then dev loss.  The last/mean
  candidate is selected by dev macro-F1 then dev loss; test is not used for
  selection.
- Deployment decision is unmodified raw argmax in label order
  `(web_search, connector_lookup, DEFER)`.  Temperature is diagnostic only.

## Fixed internal gates

The selected candidate must satisfy all checks on the frozen test split:

1. accuracy >= 0.90;
2. macro-F1 >= 0.90;
3. `web_search` recall >= 0.90;
4. `connector_lookup` recall >= 0.90;
5. `DEFER` recall >= 0.95;
6. every raw-logit vector contains exactly three finite values;
7. generated RWKV text and sampling counts are zero.

Only an internal pass permits one ECRA-120 read.  ECRA uses the S9 function
takeover gates unchanged: web exact >=23/25, connector exact >=18/20,
required-online non-takeover <=0.10, web/connector macro-F1 >=0.90, and zero
takeovers in all 75 local/deterministic/mixed/privacy rows.  Failure rejects
S10 without threshold tuning, keyword rules, or product integration.

