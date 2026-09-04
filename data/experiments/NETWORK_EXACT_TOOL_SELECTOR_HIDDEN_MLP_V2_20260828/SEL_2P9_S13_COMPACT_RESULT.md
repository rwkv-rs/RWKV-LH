# NET-SEL-2P9-S13-COMPACT result

Date: 2026-08-28 (Asia/Shanghai)

## Decision

S13 is rejected. It confirms that compact-natural coverage changes the Gate
boundary, but replacing all 600 Stage3 rows removes important natural online
Tool coverage and does not reduce total local false takeovers.

The first internal report is invalid because the legacy evaluator compared
22/22 deterministic rows to the old literal count 6. The registered R2
evaluator amendment was rerun with the original experiment identity; the
selected artifact reproduced R1 SHA-256
`0389b010c4d73b7bf5c0883bfc300c944a3d2257df5abf88a1edcb6ec4750670`.
Its internal Gate, Tool, end-to-end test and all dev clusters are 1.0.

The complete ECRA result fails:

- public web 23/25, structured connector 14/20;
- local/deterministic/mixed/privacy takeovers 2/1/7/2;
- web/connector macro-F1 0.7333333;
- five S11 false takeovers rescued, five new false takeovers introduced;
- six formerly exact required-online rows regress.

Evidence: `run_s13_compact_head_r3/ECRA120_HIERARCHICAL_REGRESSION.json`.

This result prevents a misleading conclusion from the perfect internal split:
generated compact surfaces alone do not reproduce the complete Harness
distribution, and the removed Stage3 positive rows are causally important to
the Tool head.

