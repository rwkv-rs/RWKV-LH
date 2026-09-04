# Local retrieval quality V1 result

Status on 2026-08-29: retrieval backend hard gates passed; current-architecture
RWKV end-to-end acceptance remains pending the EXE-G2-V3-RL checkpoint ablation.

## Frozen live run R1

- Cases: 9/9 passed; relevant-source recall 100%.
- Tavily-required discovery: 4/4 through Tavily, with no Bing/DDG fallback.
- Top-1 relevance: 8/9 (`88.889%`). The one raw-record miss was the Crossref
  response whose matching paper title occurs in its third exact chunk.
- Mean expected-host precision: `96.296%`.
- Mean duplicate-record ratio: `54.960%`; this reflects multiple exact chunks
  sharing one source URL and is retained as a diagnostic, not hidden.
- Latency p50/p95: `2.280164s` / `34.409386s`. The slowest Chinese discovery
  case was `52.992213s`, below the frozen per-action `60s` gate but with limited
  headroom.
- Snapshot digest, exact-span locator, and request binding: 9/9.
- Credential occurrence in persisted artifacts: zero.
- Raw result SHA-256:
  `0cac98f37fd45c55445876d30ed89105424a8cb14be2ba52037d68d737292bb4`.

## RWKV-visible projection V2

The R1 raw metric was not rewritten. Before changing projection code, the
deterministic V2 protocol was registered. It selects, within each source, the
exact chunk with greatest literal query-token coverage and then exposes a
query-adjacent 512-character exact window. It does not change the full result.

- All nine frozen R1 envelopes: 9/9 relevant projected source present.
- All projected span offsets: 9/9 exact against the immutable clean snapshot.
- Crossref: selected `E-84d46bac8ffbc3212343`, the exact chunk containing
  `RWKV: Reinventing RNNs for the Transformer Era`.
- Full authoritative envelope digest and value unchanged: 9/9.
- Network calls: 0; model calls: 0.
- Validation SHA-256:
  `8f1141dfc3dbda98c1b00823ca2240defe5cee9dc2cf6152423681c8f608febf`.

## Release interpretation

The retrieval kernel itself is suitable for a first local version: discovery,
structured lookup, content-addressed evidence, and the bounded RWKV projection
all meet their registered hard gates. It is not yet the final release verdict
for the full Agent. That verdict also requires the independent Selector + tuned
Executor live E2E to consume this evidence correctly. The main operational
watch item is long-tail discovery latency, especially Chinese queries.
