# NET-SEL-2P9-S11-HIERARCHICAL preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Decision and numbering

S10 is rejected and remains immutable. S11 keeps the same independent 2.9B
Selector boundary but decomposes the decision into two learned heads over one
RWKV hidden-state forward pass:

1. `NET-SEL-2P9-S11-GATE`: `NETWORK` versus `DEFER`;
2. `NET-SEL-2P9-S11-TOOL`: `web_search` versus `connector_lookup`, evaluated
   only when the Gate emits `NETWORK`.

The two heads do not generate text and receive only the objective, compact
progress facts, and the three frozen tool names/descriptions. Parameter
schemas, provider results, history, Executor text/state, expected labels and
reasoning are forbidden.

Both heads initially use the 2.9B zero profile. This is the one-forward
latency-minimal ablation. A learned Selector state is not kept merely to fit an
architectural preference. If S11 fails, later preregistered candidates may use
separate `NET-SEL-2P9-S12-GATE` and `NET-SEL-2P9-S13-TOOL` profiles. Function
states for the 13.3B Executor are selected only after the tool is committed:
`NET-EXE-13P3-N1-web_search` and
`NET-EXE-13P3-N2-connector_lookup`.

## Failure evidence and data

S10 passed public web (23/25) but only 2/20 structured connectors. Its 17
connector-to-web errors cover GitHub, package registries, scholarly records and
weather. It also took over 24/75 local, deterministic, mixed and privacy rows.
The local ECRA implementation confirms that Tavily, Bing, Wigolo and page
fetching are internal `web_search` providers, while exact repository/package/
paper/weather records belong to `connector_lookup`. No ECRA120 instruction is
copied into S11 training.

S11 contains exactly 2,000 rows:

- all 1,354 immutable S10 rows;
- 600 failure-grounded Stage3 natural rows: train/dev connector 280/32,
  ordinary web 70/8, mixed-local-first 100/20, privacy-local-first 70/20;
- 46 v2.4 deterministic retention rows: train 40 and dev 6, balanced as
  closely as possible across calculator, date difference and current time.

Final splits are train 1,506, dev 289, test 205. Stage3 and v2.4 rows are
projected using their already-frozen stage objective and use the fresh/no
evidence progress boundary. Every non-network source label maps to `DEFER`.
Source order is the only sampling rule. Exact rendered duplicates and
contradictory labels are forbidden; semantic families cannot cross splits.

The UTF-8 byte 5-gram cosine algorithm and exclusive 0.75 contamination
threshold remain unchanged. ECRA120 and E2E90 are contamination-only sources;
their instructions, labels and entities are excluded from training.

## Frozen features and heads

- Base model: pinned local RWKV7-G1i 2.9B via the clean local vllm-rwkv
  revision already registered by S10.
- Initial state: zero; batch 1; max 384 tokens; generated RWKV text and sampling
  count must both be zero.
- Candidate features: final-layer last-real-token and real-token mean.
- Each head: normalized 2,560 input, Linear(2560,256), GELU, LayerNorm,
  dropout 0.2, Linear(256,2).
- Seed 841; AdamW 1e-3, weight decay 1e-3, batch 64, cosine schedule, at most
  60 epochs, patience 10, inverse-frequency loss.
- Candidate selection uses dev only: maximize the arithmetic mean of Gate and
  Tool macro-F1, then minimize their summed dev loss, then prefer last over
  mean. Deployment is unmodified raw argmax; there is no confidence threshold,
  keyword fallback or output rewriting.

Feature reuse is allowed only for byte-identical S10 rendered inputs under the
same model, zero state and feature protocol. Reuse must be tensor-exact,
recorded by sample ID and SHA-256, and cannot synthesize or alter model output.

## Fixed gates

Internal S11 test:

- Gate accuracy and macro-F1 >= 0.95; `DEFER` recall >= 0.97;
- Tool accuracy and macro-F1 >= 0.95; both tool recalls >= 0.90;
- end-to-end three-way accuracy and macro-F1 >= 0.93.

Natural/deterministic dev clusters:

- connector, ordinary web, mixed-local-first and privacy-local-first each
  >= 0.90 exact;
- deterministic retention = 6/6.

The already-seen ECRA120 is a fixed regression, not a new blind holdout:

- public web >= 23/25 and connector >= 18/20;
- required-online non-takeover <= 0.10;
- web/connector macro-F1 >= 0.90;
- zero takeovers in all 75 local, deterministic, mixed and privacy rows.

Only a complete pass permits runtime integration. Integration must then pass
live Tavily retrieval, connector execution, raw-output integrity, state-lane
isolation and the complete Harness regression. A network gain cannot remove or
replace the existing 13.3B local/project/repair path.

