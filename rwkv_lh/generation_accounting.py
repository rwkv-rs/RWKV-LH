"""Observed model-generation accounting for owned execution traces.

Counts persisted model-session events, not HTTP attempts or service acceptance.
One JSON record is held at a time; only request identities survive iteration.
This checks event pairing, not model State equality or ledger authenticity.
"""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class GenerationCounts:
    started: int | None
    returned: int | None
    paired: bool
    errors: tuple[str, ...]
    started_ids: frozenset[str]
    returned_ids: frozenset[str]


def execution_trace_files(root, names):
    """Traverse only run containers produced by actual agent entrypoints.

    A direct read-only run writes at its root; Project/coding/assistance use
    execution; Goal uses rwkv/takeover; dependency integration nests execution.
    Everything else is an artifact, including workspace, generation_snapshots,
    tool_snapshots and integrated source. Never infer provenance from filename.
    """
    pending=[Path(root)]
    while pending:
        directory=pending.pop()
        if directory.is_symlink():raise ValueError('execution container must not be a symbolic link')
        if not directory.exists():continue
        if not directory.is_dir():raise ValueError('execution container must be a directory')
        for name in sorted(names):
            trace=directory/name
            if trace.is_symlink():raise ValueError('execution trace must not be a symbolic link')
            if trace.exists():yield trace
        for name in ('execution','rwkv','takeover'):
            child=directory/name
            if child.is_symlink():raise ValueError('execution container must not be a symbolic link')
            if child.exists():pending.append(child)


def execution_model_traces(root):
    return execution_trace_files(root, ("model_trace.jsonl",))


_MALFORMED_JSON = object()


def count_generation_records(records):
    """Return unknown counts on malformed or ambiguous records, never guess zero.

Unpaired but well-formed events retain their observed counts. Repeated identities
are ambiguous and invalidate counts; missing traces are an empty supplied set.
Callers must also check reserved calls and unresolved ledger operations.
"""
    starts, returns, errors = set(), set(), set()
    readable = True
    try:
        for event in records:
            if event is _MALFORMED_JSON:
                readable = False
                errors.add('malformed_json')
                continue
            if not isinstance(event, dict) or not isinstance(event.get('type'), str):
                readable = False
                errors.add('malformed_event')
                continue
            kind = event['type']
            if kind not in ('model_session_generation_started', 'model_session_generation_returned'):
                continue
            identity = event.get('request_id')
            if not isinstance(identity, str) or not identity.strip():
                readable = False
                errors.add('missing_generation_identity')
                continue
            selected = starts if kind.endswith('_started') else returns
            if identity in selected:
                readable = False
                errors.add('duplicate_generation_identity')
            selected.add(identity)
            if selected is returns and identity not in starts:
                errors.add('return_without_prior_start')
    except (OSError, ValueError, UnicodeError):
        readable = False
        errors.add('trace_read_failed')
    if starts != returns:
        errors.add('unpaired_generation')
    return GenerationCounts(len(starts) if readable else None,
                            len(returns) if readable else None,
                            readable and not errors,
                            tuple(sorted(errors)), frozenset(starts), frozenset(returns))


def count_generation_traces(paths):
    """Stream owned JSONL files through the same in-memory event validator."""
    def records():
        for path in paths:
            with Path(path).open(encoding='utf-8') as stream:
                for line in stream:
                    try:
                        yield json.loads(line)
                    except (ValueError, UnicodeError):
                        yield _MALFORMED_JSON
    return count_generation_records(records())


def project_generation_accounting(counts, *, budget_reserved, pending_operation, evidence):
    """Join actual trace identities to published model evidence without replay.

    Call budgets remain reservations. A well-formed trace may have observed
    counts yet lack a published result or retain an unresolved operation.
    """
    errors = set(counts.errors)
    if not counts.paired:
        errors.add('trace_not_paired')
    published_ids = set()
    model_receipts = 0
    for receipt in evidence:
        if receipt.get('kind') != 'model':
            continue
        model_receipts += 1
        result = receipt.get('result')
        proof = result.get('evidence') if isinstance(result, dict) else None
        raw = proof.get('raw_generation') if isinstance(proof, dict) else None
        identity = raw.get('request_id') if isinstance(raw, dict) else None
        if not isinstance(identity, str) or not identity.strip():
            errors.add('published_generation_identity_missing')
            continue
        if identity in published_ids:
            errors.add('published_generation_identity_duplicate')
        published_ids.add(identity)
    if published_ids != counts.returned_ids:
        errors.add('published_generation_identity_mismatch')
    if type(budget_reserved) is not int or budget_reserved != counts.started:
        errors.add('reserved_and_started_counts_differ')
    if model_receipts != counts.returned:
        errors.add('published_and_returned_counts_differ')
    if pending_operation is not None:
        errors.add('pending_operation')
    return dict(generation_started=counts.started, generation_returned=counts.returned,
                trace_complete=not errors, generation_accounting_errors=sorted(errors))
