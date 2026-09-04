# SEL-2P9 S47 Tavily-extracted evidence remediation preregistration

## Fixed evidence

- S45 report SHA-256 `705fa6836aa4995d8f984c8102ebc17c140e179c9581e5a63356234755502c51`: Tavily authentication/discovery succeeded, while all three `github.com` pages failed both initial and bounded-retry GETs with transport timeouts; Bing committed six records.
- S46 report SHA-256 `a54f5a092e37abe558b0af46f4228d4bf028b5c09f877b806c2318fedb132daa`: the official `include_raw_content="markdown"` mode returned non-empty extracted content for 3/3 results in 1.9 seconds, with 7.8–21.5 KB per result.
- Tavily official contract: `raw_content` is cleaned and parsed page content. It is not the original response bytes and must never be represented as such.

## Minimal product change

Change only `TavilyWebProvider` and its tests:

1. request `include_raw_content="markdown"`; keep `include_answer=false` and never consume the `content` snippet or generated answer;
2. continue to try the independently DNS-/peer-validated original page first, including the single bounded transient retry from S44;
3. if and only if the final direct-page failure is an explicit transient transport/HTTP failure, accept a non-empty `raw_content` value as a distinct source type `tavily_extracted_public_web_page`;
4. never use provider-extracted content after any `FetchPolicyError`, URL/DNS/public-address/peer/redirect/byte-bound rejection, permanent HTTP failure, malformed URL, or empty content;
5. reject, rather than truncate, provider-extracted content larger than 1,000,000 UTF-8 bytes per result;
6. store exact provider-extracted UTF-8 bytes and mark provenance with `evidence_transport=tavily_extracted_markdown`, full content SHA-256, Tavily response SHA-256, request ID, original URL, discovery rank and score;
7. retain safe direct-fetch failure fingerprints and separately report direct-page and Tavily-extracted commit counts;
8. use Bing/DDG only when neither a direct page nor eligible Tavily-extracted content is available.

No Selector, Executor, state profile, tool label, query, RWKV prompt, RWKV generation, RWKV output, evidence cleanup, chunking, or snapshot semantics changes.

## Frozen acceptance tests

- Direct page succeeds: original bytes are used; provider raw content and snippet are absent from evidence.
- Direct page times out twice: eligible exact `raw_content` bytes are committed under the distinct source type and provenance fields; no key leaks.
- Direct page policy rejection: provider raw content is not accepted and no transport retry occurs.
- Direct page permanent/non-transient failure: provider raw content is not accepted.
- Missing, non-string, empty, or over-1,000,000-byte raw content is not accepted or truncated.
- Existing credential rotation, trailing-slash safety, fallback order, fixed 23-tool menu, SSRF, snapshot, Harness, and release tests pass.
- Full project test suite passes without post-run threshold or expectation changes.

After offline acceptance, one separately preregistered live Harness run may be used for deployment acceptance. Previous runs remain immutable.

