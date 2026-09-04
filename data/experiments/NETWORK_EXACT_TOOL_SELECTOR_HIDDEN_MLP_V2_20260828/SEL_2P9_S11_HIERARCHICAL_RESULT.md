# NET-SEL-2P9-S11-HIERARCHICAL result

Date: 2026-08-28 (Asia/Shanghai)

## Decision

S11 is rejected for runtime integration. It proves the hierarchical one-forward
design and isolates the remaining failure to the NETWORK/DEFER Gate, but it
does not meet the preregistered complete ECRA120 boundary.

## Fixed run

- dataset: exactly 2,000 rows, SHA-256
  `553208ddf01e9baa6542fbd95ed653a0615111263a0573be4c388a4ca86f0c17`;
- one zero-state 2.9B RWKV forward, Hidden+MLP only;
- two raw-argmax binary heads: Gate (`NETWORK`/`DEFER`) and Tool
  (`web_search`/`connector_lookup`);
- selected candidate: mean hidden feature;
- selected artifact SHA-256:
  `31f68ed76c8ff1db8a68b2b7943f231e2ff70b2232d99d9ce486bb02c06ff361`;
- deterministic rerun produced the same artifact SHA-256;
- generated RWKV text and sampling invocations: zero.

Train, dev and held-out S11 test are 1.0 for Gate, Tool and end-to-end metrics.
All registered natural dev clusters are also 1.0. These internal results permit
the fixed ECRA regression but do not replace it.

## Complete ECRA120 result

- public web: 25/25 exact;
- structured connector: 18/20 exact;
- required-online non-takeover: 0/45;
- privacy false takeovers: 0/10;
- local-only false takeovers: 3/30;
- deterministic false takeovers: 3/15;
- mixed-local-first false takeovers: 6/20;
- web/connector macro-F1: 0.8385965, below 0.90.

The Tool head meets both functional exact thresholds. All 12 false takeovers
are Gate decisions, which motivates the separately preregistered Gate-specific
S12 state rather than widening the Tool head, adding thresholds, or exposing
schemas/results to the Selector.

Authoritative evidence:

- `run_s11_head_r2/TRAINING_REPORT.json`;
- `run_s11_head_r2/ECRA120_HIERARCHICAL_REGRESSION.json`.

