# SEL-2P9 S46 Tavily raw-content capability preregistration

## Motivation

S45 recorded six direct `github.com` failures (five `ConnectTimeout`, one `ReadTimeout`) after Tavily successfully discovered three results. The existing Bing fallback committed evidence, but Tavily could not remain the primary content path when the local machine could not reach the discovered host.

Tavily's official Search API documentation, checked on 2026-08-29, defines `include_raw_content="markdown"` as returning cleaned and parsed page content in each result. It is distinct from the optional LLM-generated `answer`, which remains disabled:

- <https://docs.tavily.com/documentation/api-reference/endpoint/search>
- <https://docs.tavily.com/documentation/best-practices/best-practices-extract>

This experiment only determines whether that provider-extracted content is available for the frozen failing query. It does not yet change product evidence semantics.

## Frozen request

- endpoint: `https://api.tavily.com/search`
- query: `RWKV official GitHub repository`
- `search_depth`: `basic`
- `max_results`: `3`
- `include_answer`: `false`
- `include_raw_content`: `markdown`
- `include_images`: `false`
- topic: `general`
- GPU environment: `CUDA_VISIBLE_DEVICES=0`
- Fetch implementation SHA-256: `6b9617e4fa26bd4341284a9578de1ddae1507ffaef3227e287e1ee131f18e562`
- S45 report SHA-256: `705fa6836aa4995d8f984c8102ebc17c140e179c9581e5a63356234755502c51`

Use the ordered local Tavily credential pool with the existing status-based rotation rules. Raw credentials, Authorization headers, response bodies, snippets, and raw content must never be written or printed.

## Recorded measurements

- safe credential hash and status;
- response byte count and SHA-256;
- result count;
- per result: rank, scheme, host, full-URL SHA-256, and raw-content byte count/SHA-256;
- no page GET, fallback provider, model, Selector, Executor, or Harness call.

## Capability gates

- at least one credential is configured and one API call succeeds;
- at least one result is returned;
- every accepted result has non-empty provider-extracted raw content;
- at least one raw-content value contains 200 or more UTF-8 bytes;
- no configured credential occurs in artifacts;
- direct page GET, fallback provider, Selector, Executor, RWKV generation, and RWKV-output modification counts are zero.

The diagnostic is one-shot and immutable. Its gates may not be changed after execution.

