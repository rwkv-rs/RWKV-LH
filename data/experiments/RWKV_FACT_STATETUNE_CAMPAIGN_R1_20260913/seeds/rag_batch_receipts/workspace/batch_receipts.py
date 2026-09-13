"""Offline accounting for shared HTTP batches, including interrupted runs.

A pre-send receipt proves preparation only. A completed receipt explicitly
recording ``http_attempted=False`` proves no dispatch; an observed True proves
an attempt, not a successful response or provider execution.
"""

from collections import defaultdict
import json
from pathlib import Path


def _summarize_http(directory: Path, prefix: str, identity_key: str, traces=()) -> dict:
    batches = defaultdict(list)
    unreadable = []

    def observe(record, origin, completed=False):
        identity = record.get(identity_key)
        if not isinstance(identity, str) or not identity:
            raise ValueError("HTTP receipt is missing its identity")
        attempted = record.get("http_attempted")
        terminal = completed or bool(record.get("ended_at"))
        evidence = ("attempted" if attempted is True else
                    "not_attempted" if attempted is False and terminal else "unknown")
        batches[identity].append({"origin": origin, "evidence": evidence})

    for path in sorted(directory.glob(f"*.{prefix}_*.json")):
        completed = path.name.endswith(f".{prefix}_completed.json")
        if not completed and not path.name.endswith(f".{prefix}_started.json"):
            continue
        try:
            record = json.loads(path.read_bytes())
            if not isinstance(record, dict):
                raise ValueError("batch receipt is not an object")
            observe(record, path.name, completed)
        except (OSError, ValueError, TypeError):
            # A process can stop halfway through writing a receipt. Its filename
            # identifies an unresolved batch; do not turn corrupt bytes into 0.
            identity = path.name.rsplit(f".{prefix}_", 1)[0]
            batches[identity].append({"origin": path.name, "evidence": "unknown"})
            unreadable.append(path.name)

    for number, trace in enumerate(traces):
        identity = trace.get(identity_key)
        if identity_key == "count_id" and not identity:
            identity = trace.get("token_count_id")
        if isinstance(identity, str) and identity:
            batches[identity]  # Keep a known batch even if its HTTP entry is absent.
        for ordinal, record in enumerate(trace.get("http", [])):
            if isinstance(record, dict) and record.get(identity_key):
                observe(record, f"model_trace[{number}].http[{ordinal}]")

    rows = []
    counts = {"confirmed_attempted": 0, "never_attempted": 0, "unknown": 0}
    for identity, observations in sorted(batches.items()):
        evidence = {item["evidence"] for item in observations}
        conflict = {"attempted", "not_attempted"} <= evidence
        classification = ("unknown" if conflict else
                          "confirmed_attempted" if "attempted" in evidence else
                          "never_attempted" if "not_attempted" in evidence else "unknown")
        counts[classification] += 1
        rows.append({identity_key: identity, "classification": classification,
                     "conflicting_terminal_evidence": conflict, "observations": observations})
    return {"schema": f"{prefix}-http-accounting-v1", "unique_requests": len(rows),
            **counts, "count_exact": counts["unknown"] == 0,
            "http_requests": counts["confirmed_attempted"] if counts["unknown"] == 0 else None,
            "confirmed_attempted_lower_bound": counts["confirmed_attempted"],
            "possible_attempted_upper_bound": counts["confirmed_attempted"] + counts["unknown"],
            "unreadable_receipts": unreadable, "requests": rows,
            "definition": "Attempt means client dispatch attempted; not proof of provider execution. "
                          "Started-only receipts have unknown dispatch state."}


def summarize_batch_http(directory: Path, traces=()) -> dict:
    result = _summarize_http(directory, "batch", "batch_id", traces)
    result["unique_batches"] = result.pop("unique_requests")
    result["batches"] = result.pop("requests")
    return result


def summarize_token_http(directory: Path, traces=()) -> dict:
    """Count tokenizer HTTP separately; one count_id is not a generation batch."""
    result = _summarize_http(directory, "token_count", "count_id", traces)
    result["unique_counts"] = result.pop("unique_requests")
    result["counts"] = result.pop("requests")
    return result
