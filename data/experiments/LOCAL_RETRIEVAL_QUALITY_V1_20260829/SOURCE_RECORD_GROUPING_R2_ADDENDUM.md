# Retrieval source-record grouping R2 addendum

Registered on 2026-08-29 before the R2 live calls.

## Frozen R1 observation

The original preregistered R1 result is retained unchanged at `run_r1/RESULT.json`,
SHA-256 `0cac98f37fd45c55445876d30ed89105424a8cb14be2ba52037d68d737292bb4`.
It passed all 9/9 hard gates, but its diagnostic mean duplicate-record ratio was
`0.5496031746031745` and scholarly top-1 relevance was false.

The root cause is structural, not a provider or model failure: the gateway emitted
one `EvidenceRecord` for each text chunk while reusing the same immutable source
object, URL, snapshot digest, title and structured fields. `EvidenceRecord` already
supports multiple exact spans, so those rows were duplicate record envelopes rather
than distinct evidence sources. Crossref and PyPI were affected most because the
same structured payload was copied into up to four chunk records.

## R2 correction

- Emit exactly one `EvidenceRecord` per immutable `RetrievedSource`.
- Put up to four exact chunks into that record's `exact_spans` in original offset
  order.
- Preserve the previous global span budget: the sum of spans remains at most
  `max_records`; this is not an unbounded evidence expansion.
- Preserve provider order, raw source bytes, snapshots, exact span text and
  locators. No search result, RWKV output or evidence text is ranked, rewritten,
  dropped based on expected answers, or synthesized.
- Corrected gateway SHA-256:
  `067501eb5024ebf6d79e68de0be050ef0015f9c6bdb86ce866c1ad21027f6f6e`.
- Fixed regression before live calls: retrieval kernel/harness/search-text suite
  `69 passed`.

## Frozen R2 evaluation

R2 reuses the original 9-row dataset unchanged, SHA-256
`eee343aa311811a349476f4f632b0a4a5e97cc1e6657e4c8c68255124297fd2e`, the original
hard gates, provider order, 60-second per-action bound and metric definitions. It
must still report top-1 relevance, host precision, duplicate-record ratio, latency,
provider attempts, snapshot integrity and span locator integrity. Results are
accepted whether the diagnostic metrics improve or regress; the implementation and
evaluation thresholds will not be changed after R2 starts.
