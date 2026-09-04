# SEL-2P9 S44 Tavily page-fetch resilience remediation preregistration

## Evidence selecting this change

- S42 report SHA-256 `f817b555ee3cf8956e5dce3c51ede21a6a80931e0c8b793b4df3de71083728ca`: Tavily API success, 3 results discovered, 0 pages committed, 3 page failures; Bing fallback still committed evidence.
- S43 diagnostic SHA-256 `2f735fd1af0d353ce160179ff20bc6138fa07805a4b2023b6ddabfd722a8c965`: with the same query and frozen implementation, Tavily API success and all 3 pages independently fetched and committed.
- Therefore credentials, fixed query, provider architecture, DNS/public-peer policy, and page parsability are viable. The S42 page failure is transient/non-deterministic. The persistent code defect exposed by S42 is that page exceptions are counted and discarded, so their cause is not retained.

## Frozen architecture

- Tavily remains discovery only. Tavily snippets and generated answers are not evidence.
- Each discovered page remains a new, independently DNS- and connected-peer-validated GET.
- Local provider order remains Tavily, Bing RSS, DuckDuckGo.
- No Selector, Executor, RWKV generation, RWKV output rewriting, query rewriting, or agent retry is added.
- Existing trailing-slash workaround remains restricted to the exact peer-unavailable policy error and eligible extensionless paths.

## Single remediation

Within `TavilyWebProvider` only:

1. add at most one same-URL transport retry for explicit transient transport exceptions or HTTP 408/425/429/500/502/503/504;
2. never transport-retry URL validation, DNS/public-address, connected-peer, redirect-bound, byte-bound, or other `FetchPolicyError` failures;
3. record a bounded safe diagnostic for every failed page-fetch attempt: discovery rank, attempt kind, scheme/host, SHA-256 of the complete URL, exception type, category, and HTTP status or policy reason;
4. never store the raw URL path/query, exception message from non-policy failures, response content, or credentials in those diagnostics;
5. preserve the existing result-level `page_fetch_failure_count`, adding separate attempt-failure and transport-retry counts.

## Frozen tests and gates

Pre-change retrieval-kernel test SHA-256: `e34788a4d227ff34c44978bad994d3fabad057ccea3f420bd987bd6fd4e2abb2`.

The remediation is accepted only if:

- a first transient timeout followed by success performs exactly two page GETs, commits one original page, reports one transport retry and zero failed results;
- a persistent transient failure performs exactly two page GETs, commits no page, reports one failed result and two safe attempt diagnostics;
- a public-policy failure performs one GET, no transport retry, and remains rejected;
- safe diagnostics contain neither a configured API credential nor the raw discovered URL path/query;
- existing trailing-slash, credential rotation, discovery-only, fallback, SSRF, redirect, byte-bound, and Harness tests pass;
- the complete project test suite passes without changing test expectations after execution.

After the code and offline tests pass, a separately preregistered live Harness smoke may be run once. S42 and S43 artifacts are immutable and must not be overwritten.

