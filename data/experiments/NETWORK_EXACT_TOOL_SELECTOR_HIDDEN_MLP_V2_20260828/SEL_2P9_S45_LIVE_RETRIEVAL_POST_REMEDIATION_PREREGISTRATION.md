# SEL-2P9 S45 live retrieval post-remediation preregistration

## Purpose

Run one final live product-Harness smoke after the S44 bounded page-fetch remediation. This is a new immutable run; S42 and S43 remain unchanged.

## Frozen inputs and implementation

- Query: `RWKV official GitHub repository`
- Action: `web_search`
- Arguments: `{"query": "RWKV official GitHub repository", "max_results": 3}`
- Network policy: `AUTO_PUBLIC`
- Product menu: exact fixed 23 executable operations used by the activated 2.9B Selector architecture
- GPU environment: `CUDA_VISIBLE_DEVICES=0`
- Provider implementation SHA-256: `8c78dd73afe55f8d956beba171335e6a441e9224b9bea5aeb97c3a743f9e3f82`
- Fetch implementation SHA-256: `6b9617e4fa26bd4341284a9578de1ddae1507ffaef3227e287e1ee131f18e562`
- S44 protocol SHA-256: `be695e4eda28db5d82403b17804a688a06256dcc64cda0cb0414f9823a17003b`
- S43 diagnostic SHA-256: `2f735fd1af0d353ce160179ff20bc6138fa07805a4b2023b6ddabfd722a8c965`
- Credential selection: current ordered `.env.local` Tavily pool; no raw credential may be emitted.

## One-shot procedure

1. Verify all frozen hashes before making a network request.
2. Construct the real product Harness with its fixed operation menu and immutable snapshot store.
3. Execute exactly one `web_search` action with the frozen arguments.
4. Require Tavily discovery and at least one independently fetched Tavily page; Bing/DDG fallback is not accepted for this specific gate.
5. Record sanitized provider counters, committed evidence identities, immutable file hashes, and network-policy decision.
6. Scan the in-memory result and every immutable artifact for all configured Tavily credentials.

## Acceptance gates

- at least one Tavily credential is configured;
- the menu is exactly the fixed 23 executable operations;
- policy allows the literal public query without controller rewrite;
- Tavily API authentication succeeds and at least one independently fetched Tavily page is committed;
- no fallback discovery provider is used;
- Harness reports evidence committed with at least one exact span;
- immutable route and evidence files exist;
- no configured credential occurs in result or immutable files;
- agent retry, alternative tool fallback, Selector postprocessing, Executor call, RWKV generation, and RWKV-output modification counts are all zero.

No threshold or gate may be changed after the live run.

