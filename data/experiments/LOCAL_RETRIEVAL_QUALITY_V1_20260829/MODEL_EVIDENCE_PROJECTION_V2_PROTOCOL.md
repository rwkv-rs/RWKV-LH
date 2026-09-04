# RWKV evidence projection V2 protocol

Registered on 2026-08-29 before changing or re-running the projection.

## Observed defect

The full `ExternalEvidenceEnvelope`, source snapshot, exact spans, and action
result are durable and correct. The bounded Controller-to-RWKV projection groups
records by source object but currently keeps the first chunk. For a structured
response with a long leading author list, the relevant title can occur only in a
later exact chunk. The current 512-character projection can therefore omit the
fact even though it is present in the authoritative result.

## Frozen deterministic change

1. Preserve the provider's source order and group only records with the same
   source-object identity.
2. Tokenize the exact action `query` with
   `[a-z0-9]+|[\u3400-\u9fff]` after Unicode `casefold`; de-duplicate tokens.
3. Within each source, score every record by the total character length and
   count of unique query tokens present in its title, canonical structured
   fields, or exact span text. Keep the highest score; ties keep original order.
4. Within that record, select the highest-scoring exact span. Retain one exact
   512-character window beginning at most 128 characters before the earliest
   occurrence of the longest matched query token. If no token matches, retain
   the existing prefix window.
5. Project at most two source objects, as before. Record source and document
   offsets, projection completeness, and algorithm identity.

This is a read-only projection. It may not change, delete, reorder, repair, or
replace the full evidence envelope, snapshot, action result, RWKV text, or RWKV
token IDs.

## Fixed checks

- Existing bounded-projection regression remains byte-semantic compatible when
  no query is supplied.
- A synthetic three-chunk same-source case must select the later exact chunk and
  expose the registered query literal inside the 512-character window.
- The original input mapping and all full exact span strings remain unchanged.
- The frozen retrieval-quality V1 metrics are not rewritten. Any later live run
  uses a new output directory and the same nine-case dataset and hard gates.
- Full project regression and current-architecture RWKV E2E must pass before the
  projection can be called product-ready.
