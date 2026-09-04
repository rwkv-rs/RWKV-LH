# NET-SEL-2P9-S3 role-leakage remediation preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Parent and scope

- `NET-SEL-2P9-S2` is rejected: its learned initial state changes no feature or
  prediction after the 878–1352-token Selector input.
- S3 is a zero-state 2.9B Hidden+MLP experiment.  It fixes a demonstrated data
  projection defect before any further state tuning.
- S3 does not modify `NET-EXE-13P3-N0`, retrieval providers, Harness behavior,
  RWKV weights, RWKV output, or the frozen ECRA120 evaluator.

## Registered root cause

S2 projected the data-generation failure cluster directly into
`stage_role`.  The cluster values were strongly label-correlated:

- `natural_connector` -> 400/400 `connector_lookup`;
- `ordinary_web` -> 100/100 `web_search`;
- `mixed_local_first` -> 100 `read_file` + 100 `read_json`;
- `privacy_local_first` -> 200/200 `read_file`.

The external Harness projection correctly uses `stage_role=work`.  Therefore
S2 internal accuracy could be obtained from a provenance field unavailable in
real use.  This is target/provenance leakage, not an acceptable model feature.

## Frozen remediation dataset

Source is the immutable S2 `cases.jsonl` with SHA-256
`b9f0601499790611de23322f8066f09deb8ba9fa6d5071fba78ee36930551922`.
For every row, parse the canonical `SelectorBootstrapV2` and
`SelectorStepV2`, replace only `stage_role` with `work`, and render canonical
JSON again.  Labels, task, objective, progress, menu names/descriptions,
language, failure-cluster audit field, semantic family, source, ordering, and
split remain unchanged.

Counts remain train/dev/test = 2000/276/250.  Exact rendered duplicates must be
zero; family overlap must be zero; all 25 labels must remain in every split;
maximum UTF-8 byte 5-gram cosine against ECRA120 remains below 0.75.  The
generator, source, protocol, cases and manifest receive SHA-256 records.

The failure cluster remains only as an out-of-band audit grouping.  It may not
enter the rendered RWKV input or head feature.

## Fixed model and head

- base: frozen `rwkv7-g1i-2.9b-20260805-ctx16384`, zero initial state;
- local pinned vLLM-RWKV revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- batch 1, FP16 WKV, no generation and no sampling;
- last-real-token and real-token-mean extracted as separate fixed arms;
- same 256-hidden MLP, seed 829 and S2 optimizer/training parameters;
- raw 25 logits and deterministic raw argmax only; no calibration,
  postprocessing, rule override, retry, or output repair.

S3 selects last-hidden in advance because S2 last-hidden passed the internal
gate and is the intended serving feature.  Mean remains an audit arm and
cannot replace last after seeing ECRA.

## Frozen gates

Synthetic retention test:

- accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- web, connector, calculator, date and time recall >= 0.85;
- local/search/web/connector boundary accuracy >= 0.85.

Natural dev leakage check (176 Stage3 rows only):

- overall accuracy >= 0.90;
- every available failure-cluster accuracy >= 0.80.

ECRA120 gates are unchanged from S2:

- local-only >= 24/30;
- public web >= 23/25;
- deterministic >= 14/15;
- connector >= 12/20;
- mixed local-first >= 10/20;
- privacy local-first >= 8/10;
- local-only network false-positive rate = 0;
- required-online false-negative rate <= 0.10;
- web/connector macro-F1 >= 0.70.

Product eligibility also requires zero generated RWKV text, zero sampling,
profile/lane isolation, the full local test suite, live Tavily retrieval, and
the existing non-network Harness regression.  A pass does not revive S2 state
or authorize 13.3B network state tuning automatically.
