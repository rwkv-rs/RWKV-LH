# Team timebook

Implement `timebook.py` using only Python's standard library and durable SQLite storage. Commands:

- `python timebook.py add DB --id ID --project PROJECT --start ISO --end ISO`
- `python timebook.py import DB INPUT_JSON`
- `python timebook.py stats DB --from YYYY-MM-DD --to YYYY-MM-DD`

An event has exactly `id`, `project`, `start`, `end`, all nonempty strings. Preserve nonempty IDs/project names exactly; reject whitespace-only ones. Timestamps use ISO 8601 with explicit UTC offset or Z, whole-second precision, and end strictly after start. Import is a JSON array of events. No overlap restriction is imposed: recorded durations are summed independently.

Events are identified globally by ID. Normalize timestamps to UTC for duplicate comparisons. Reimporting an identical ID/project/time interval is a no-op; a conflicting ID is an error. An invalid record or conflicting ID rejects the entire import transaction, including earlier valid records from that batch. Empty imports are valid. Add and import print `{"inserted": N, "duplicates": N}`; add follows the same duplicate rules. A new DB is created as needed.

Stats uses UTC calendar dates and a half-open range `[from, to)`, where `to` is the excluded midnight. Reject invalid or reversed/empty date ranges. Split intervals at UTC midnight and clip to the requested range, including leap days and offset conversions. Return `{"days": [{"date": "YYYY-MM-DD", "projects": {"project": integer_seconds}, "total_seconds": integer_seconds}], "total_seconds": integer_seconds}`. Include only days with recorded duration, ordered chronologically; project keys must be emitted in sorted order. Empty results contain an empty days array and total 0. Each CLI invocation is a new process, so persistence and duplicate detection must survive restarts. Errors exit nonzero with diagnostics; successful stdout is one JSON document. Include your own tests and update this README with usage and verification instructions.
