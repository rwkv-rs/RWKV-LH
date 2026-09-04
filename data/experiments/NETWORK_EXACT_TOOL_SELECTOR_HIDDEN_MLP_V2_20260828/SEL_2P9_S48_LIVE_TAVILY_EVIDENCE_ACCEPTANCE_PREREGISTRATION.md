# SEL-2P9 S48 live Tavily evidence acceptance preregistration

## Purpose

One immutable deployment acceptance run for the S47 product path. It validates that Tavily remains the primary provider and commits evidence through either independently fetched pages or the explicitly typed Tavily-extracted transport when a public source host is transiently unreachable.

## Frozen inputs

- action: `web_search`
- query: `RWKV official GitHub repository`
- `max_results`: `3`
- policy: `AUTO_PUBLIC`
- product menu: exact fixed 23 executable operations
- GPU environment: `CUDA_VISIBLE_DEVICES=0`
- Provider implementation SHA-256: `5f09ea303e11aef4a863af3c16e7d38065f7da9f1da25d633c6914ca005c2181`
- Fetch implementation SHA-256: `6b9617e4fa26bd4341284a9578de1ddae1507ffaef3227e287e1ee131f18e562`
- S47 protocol SHA-256: `4f8dd5ad2c595ddd750b0a27775aec2384e57d1bc1fba005bddddf6a6fc1dda6`
- S47 offline regression SHA-256: `18370eca6f6a7fb4648b4a5023b3874d9a944b2b9418f23a7aaf92f25c6c3392`
- Credential selection: existing ordered local Tavily pool; raw credentials must never be emitted.

## Acceptance gates

- at least one Tavily credential is configured;
- the Harness exposes exactly the fixed 23 executable operations;
- policy allows the literal public query without controller rewrite;
- Tavily API authentication succeeds and Tavily commits at least one page;
- Bing/DDG discovery fallback is not used;
- every record is either:
  - `public_web_page` with `evidence_transport=direct_public_http`, or
  - `tavily_extracted_public_web_page` with `evidence_transport=tavily_extracted_markdown`;
- for every Tavily-extracted record, `extracted_content_sha256` equals the immutable raw snapshot digest/source record ID;
- record-level Tavily response hash and request ID equal the outer provider attempt;
- Harness status is `evidence_committed`, every record has an exact span, and immutable route/raw/clean/manifest files exist;
- no configured credential occurs in the result or immutable files;
- one Harness action only; agent retry, alternative tool fallback, Selector call/postprocessing, Executor call, RWKV generation, and RWKV-output modification counts are zero.

The run accepts either direct or eligible provider-extracted Tavily transport because direct-host reachability is external and variable. Offline S47 tests separately force and verify both branches. The criteria may not be revised after execution.

