# SEL-2P9 S49 same-request host circuit and timeout split preregistration

## Evidence selecting the change

- S45: three Tavily results on `github.com` each performed an initial and one retry GET; all six ended in `ConnectTimeout`/`ReadTimeout`, then Bing fallback supplied evidence.
- S46: Tavily returned three extracted content values in 1.9 seconds.
- S47: safely typed provider-extracted evidence is implemented and 529/529 full tests pass.
- Therefore repeatedly paying the full direct-connection timeout for later results on a host already proven unavailable in the same request adds latency without new information.

S48 was preregistered but never executed and is explicitly recorded as superseded. No acceptance result or threshold is being replaced.

## Minimal changes

1. `PublicHttpFetcher` keeps a 20-second read bound and adds a separate default 5-second connect bound; both GET and API POST use the Requests `(connect, read)` timeout tuple.
2. `TavilyWebProvider` keeps the initial direct GET plus its single retry for the first result on a host.
3. Only when both attempts end in eligible transient errors, mark that hostname unavailable for the remainder of this one `search()` call.
4. For later results on that hostname, perform fresh `validate_public_url` DNS/public-address validation but skip the socket GET; only then may the already implemented, explicitly typed Tavily-extracted content path run.
5. Any validation failure remains a `FetchPolicyError`, is recorded safely, and blocks extracted evidence.
6. Circuit state is local to one `search()` invocation: no global, persistent, cross-user, or cross-query state is introduced.
7. Results on other hostnames still attempt direct fetch normally.

No change to Selector, Executor, state, menu, query, RWKV prompt/generation/output, cleanup, chunking, snapshot integrity, provider order, or evidence source typing.

## Frozen offline gates

- Requests GET and POST receive connect/read timeout tuples with defaults `(5.0, 20.0)`.
- Two same-host results with persistent transient failures perform exactly two GETs for the first result and zero GETs for the second; both eligible provider-extracted pages are committed, and circuit skip count is one.
- A result on a different host still performs its own direct GET.
- A same-host circuit skip whose fresh public-URL validation fails commits no extracted content and records the policy rejection.
- The circuit is empty on the next `search()` call.
- Existing transient retry, extracted-content, oversized-content, fetch-policy, SSRF, credential, fallback, fixed-menu, Harness and release tests pass.
- Full project suite passes without changing gates after execution.

After offline acceptance, a new separately preregistered live Harness run will replace the unexecuted S48 procedure.

