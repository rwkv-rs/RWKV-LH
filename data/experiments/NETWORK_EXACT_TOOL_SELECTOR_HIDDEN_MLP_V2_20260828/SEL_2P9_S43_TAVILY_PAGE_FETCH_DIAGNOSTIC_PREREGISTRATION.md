# SEL-2P9 S43 Tavily page-fetch diagnostic preregistration

## Scope

- Diagnose the already-recorded S42 failure without changing or rerunning S42.
- Exercise only the project-owned `TavilyWebProvider` and `PublicHttpFetcher` path.
- Keep Tavily as discovery only: each discovered URL must still be fetched and peer-validated independently before it can become evidence.
- Do not invoke the Selector, Executor, RWKV generation, postprocessing, retries at agent level, or fallback providers.
- Do not change, delete, induce, repair, or mask any RWKV output.

## Frozen inputs

- Query: `RWKV official GitHub repository`
- `max_results`: `3`
- GPU environment: `CUDA_VISIBLE_DEVICES=0`
- S42 report SHA-256: `f817b555ee3cf8956e5dce3c51ede21a6a80931e0c8b793b4df3de71083728ca`
- Retrieval fetcher SHA-256: `6b9617e4fa26bd4341284a9578de1ddae1507ffaef3227e287e1ee131f18e562`
- Provider implementation SHA-256: `f6006be80423c0c84fba60dfa453517b6ae3fae6263ca3f3bced139c0666ca36`
- Credential selection: the existing ordered local configuration; raw credentials must never be written or printed.

## Recorded evidence

For the single provider call, record:

1. sanitized Tavily provider attempts and hashed credential identity;
2. Tavily API request success/failure without payload, headers, or raw response body;
3. every independent discovered-page GET URL;
4. per GET success metadata or exact exception type, bounded message, and HTTP status when available;
5. whether a canonical trailing-slash retry occurred;
6. absence of every configured credential from the diagnostic artifacts.

Public result URLs are diagnostic inputs and may be stored. No API key, Authorization header, or Tavily response body may be stored.

## Diagnostic completion gates

The run is diagnostically complete only if all are true:

- at least one Tavily credential is configured;
- the Tavily API credential attempt succeeds;
- Tavily reports at least one discovered result;
- at least one independent page GET is observed;
- every observed GET has either bounded success metadata or a bounded exception record;
- no configured credential occurs in the written artifacts;
- agent retry, fallback provider, Selector, Executor, RWKV generation, and RWKV-output modification counts remain zero.

This diagnostic does not require a page fetch to fail or succeed. Its result will select the next implementation change; the criteria above may not be revised after the run.

