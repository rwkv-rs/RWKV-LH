# Local Retrieval Quality V1 preregistration

Registered before the first live call on 2026-08-29 (Asia/Shanghai).

## Question

Is the local retrieval kernel merely network-reachable, or does it return
content-addressed evidence from relevant authoritative source families with
usable exact spans quickly enough for the RWKV Executor?

## Frozen data and execution

- Dataset: `data/datasets/rwkv_lh_retrieval_quality_v1/cases.jsonl`, 9 rows,
  SHA-256 `eee343aa311811a349476f4f632b0a4a5e97cc1e6657e4c8c68255124297fd2e`.
- Every case uses a fresh snapshot/route directory and exactly one Harness backend
  call; no cache is shared across cases.
- General discovery uses the configured order Tavily → Bing RSS → DuckDuckGo.
  The four `tavily_required` cases must succeed through Tavily without discovery
  fallback. Bing and DDG remain available product fallbacks but cannot satisfy
  this specific Tavily gate.
- No RWKV or strong model is called. Queries, expected domains, terms, fields,
  metrics, and thresholds are not changed after observing results.
- API credentials are read only from ignored local environment files. Values may
  not enter reports, snapshots, route files, logs, or source control.

## Fixed metrics

For every case report status, record count, unique URL count, latency, provider
path, expected-host precision over unique URLs, and whether the first record is
relevant. A relevant record must itself match an expected host and contain every
required literal term in its title, exact spans, or structured fields. Applicable
structured field names must exist in the same evidence set.

Hard gates:

1. 9/9 exact status and minimum record/unique-URL recall.
2. 9/9 at least one relevant record; all applicable literal terms and structured
   fields present.
3. 9/9 request digest binding and complete snapshot/span integrity.
4. 4/4 Tavily-required cases have a successful Tavily attempt and no Bing/DDG
   discovery fallback.
5. Every action is at most 60 seconds; p50 and p95 are reported without changing
   the threshold.
6. Zero credential occurrence in in-memory sanitized reports or any persisted
   snapshot/route artifact.

Top-1 relevance, source precision, source diversity, record duplication, and
latency are diagnostic quality metrics and must be reported even when all hard
gates pass. A failure is retained as evidence and expanded to its whole family;
it is never repaired by rewriting provider output or weakening expectations.
