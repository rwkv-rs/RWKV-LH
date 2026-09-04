# Tavily primary discovery — run r4 remediation record

## Trigger and root cause

- `run_r3/RESULT.json` SHA-256: `a72cce32d8ab1298882526f7a2e9ccbb3a63528f7b9b03303ec34f0376a8da1a`.
- r3 reached Tavily with HTTP 200 and discovered three results, but committed zero Tavily pages and mechanically fell back to Bing. The frozen `no_fallback_used` gate therefore failed.
- `run_r3/FETCH_DIAGNOSTIC.json` SHA-256: `dcfbb275491ef8e8c87a657ca210ec65ad18bf99e2fec7bc0c24c6033912e13d`.
- All three exact Tavily URLs failed with `FetchPolicyError: retrieval peer address is unavailable`. The returned URLs were extensionless directory paths without a trailing slash. Those origins returned an empty 302; urllib3 released the connection before connected-peer inspection.

## Systemic fix

- `rwkv_lh/retrieval/providers.py` SHA-256: `f6006be80423c0c84fba60dfa453517b6ae3fae6263ca3f3bced139c0666ca36`.
- The connected-peer requirement was not removed or weakened. After this exact failure, Tavily may make one fresh request to a trailing-slash variant only when the discovered URL is HTTP(S), extensionless, has no query/fragment, and is not already slash-terminated.
- The retry is a new request through `PublicHttpFetcher`, so URL DNS validation and connected-peer validation both execute again. The original discovery URL and retry count remain in structured provenance.
- Other fetch failures and URL forms still fail normally and can trigger the existing Bing/DDG fallback.

## Verification

- Retrieval regression source SHA-256: `679f74386392d170c7f412b0b98dc49c8850cf6aa700e95e6156e7fe126b49f0`.
- Focused and related retrieval regression: `58 passed`.
- r4 runner SHA-256: `881e2a598d449499c721d32e5115331e5e1b7441b4e74d0a24d6c68cb6bf2368`.
- `RESULT.json` SHA-256: `128774d7ea46f9e846bfba03967eae8ff98b128f977983a773affe85eaf2afe0`.
- r4 passed every frozen gate: Tavily was the only provider attempt, 11 original-page evidence records were committed, snapshots and request binding verified, no search endpoint became evidence, and no credential entered the artifacts.
