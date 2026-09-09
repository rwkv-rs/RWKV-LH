# Incremental access-log store

Implement `accesslog.py` with Python standard library and a durable SQLite database:

- `python accesslog.py ingest DB SOURCE_JSONL`
- `python accesslog.py query DB --from ISO --to ISO [--status-min INTEGER] [--prefix PATH_PREFIX]`
- `python accesslog.py rejections DB`

Each JSONL record has exactly `id`, `timestamp`, `path`, `status`, `bytes`. ID is a nonempty string; path starts with `/`; status is a true integer 100..599; bytes is a true nonnegative integer (booleans are not integers for this format). Timestamp is an ISO 8601 string with explicit offset or Z and whole-second precision. Normalize timestamps to UTC. Event IDs are global across source files. An identical normalized event is a duplicate; conflicting content for an existing ID is quarantined without overwriting the original.

Persist each resolved absolute source path's committed byte offset and a cryptographic digest of its consumed prefix. Consume only newline-terminated records. Leave an incomplete final line unconsumed until a later append completes it. On process restart, continue at the saved byte offset. A repeat with no new complete records returns zero work. Reject truncation or rewriting of any consumed prefix as a fatal error with no DB changes; do not silently reset the offset. Different source files have separate offsets but share event deduplication.

Invalid UTF-8/JSON lines are `invalid_json`; invalid event schemas/values are `invalid_event`; conflicting existing IDs are `conflicting_id`. Advance past quarantined complete lines, storing the resolved source path, line-start byte offset and reason once. Apply event inserts, quarantine entries and new offset atomically for an ingest invocation. The successful result is `{"inserted": N, "duplicates": N, "rejected": N, "offset": N}` with byte offset after the last consumed newline.

Query selects timestamps in half-open `[from, to)`, status >= status-min (default 100), and literal path.startswith(prefix) (default `/`). The range must be nonempty; status-min must be 100..599. Return `{"count": N, "bytes": N, "by_status": {"status": N}, "by_path": {"path": {"count": N, "bytes": N}}}`. Empty queries return zero totals and empty maps. JSON object keys must be sorted. `rejections` returns `{"rejected": N, "rows": [{"source": "absolute path", "offset": N, "reason": "code"}]}` ordered by source then offset. Successful stdout is one JSON document; errors exit nonzero with diagnostics. Include tests and document restart, malformed-line and source-rotation behavior; use no external packages or services.
