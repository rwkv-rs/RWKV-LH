# SEL-2P9 S50 live Tavily evidence and performance acceptance preregistration

## Purpose

One immutable live product-Harness acceptance run after S49. It replaces only the never-executed S48 procedure and validates both evidence integrity and bounded local latency.

## Frozen inputs

- action: `web_search`
- arguments: `{"query": "RWKV official GitHub repository", "max_results": 3}`
- policy: `AUTO_PUBLIC`
- menu: exact fixed 23 executable operations used by the activated 2.9B Selector architecture
- GPU environment: `CUDA_VISIBLE_DEVICES=0`
- Fetch implementation SHA-256: `06fa0059a77da5cce7c85c48be8c37cef74542ab8534a2c55419fabf263831d7`
- Provider implementation SHA-256: `cb8255aa2a170779150e545de9d2a807686e0c590ee7c3898ad1a6037ace427f`
- S49 protocol SHA-256: `026ad56cb5b7e1d151b4e315c6879f40571e7e6d5358abdd6cabcb4caea4bd0e`
- S49 offline regression SHA-256: `a3943f5e1718d9b4e1ce0556a3565bdd76e0cdaf60fe0ab60defd7ecdec3fe09`
- Credential selection: existing ordered local Tavily pool; no raw credential may be emitted.

## One-shot acceptance gates

- at least one Tavily credential is configured;
- the Harness menu is exactly the fixed 23 operations;
- policy allows the literal public query without controller rewrite;
- Tavily authentication succeeds and commits at least one evidence page;
- Bing/DDG discovery fallback is not used;
- Harness execution wall time measured around the one action is at most 60 seconds;
- every evidence record is either:
  - `public_web_page` with `evidence_transport=direct_public_http`, or
  - `tavily_extracted_public_web_page` with `evidence_transport=tavily_extracted_markdown`;
- every Tavily-extracted record has `extracted_content_sha256` exactly equal to its immutable raw snapshot/source-record digest;
- every record's provider response SHA and request ID equal the outer Tavily attempt;
- Harness status is `evidence_committed`, every record contains an exact span, and immutable raw/clean/manifest/route files exist;
- no configured credential occurs in the in-memory result or immutable files;
- exactly one Harness action; agent retry, alternative tool fallback, Selector call/postprocessing, Executor call, RWKV generation, and RWKV-output modification counts are zero.

Direct-host reachability may vary, so either valid Tavily transport is accepted. S49 offline tests deterministically force direct success, extracted fallback, host circuit, different-host, policy rejection, and circuit reset branches. No gate may be revised after execution.

