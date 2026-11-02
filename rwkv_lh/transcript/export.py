"""Export one ended agent session as the stored transcript a dataset version reads.

This is the only session -> ``native_messages.json`` conversion. It reads the
ledger without writing, proves every recorded model input equals the production
builder's output, and emits ``{"messages", "tools"}`` exactly as
``parse.parse_transcript`` and ``dataset.build_dataset`` read it. It decides
nothing about admission: acceptance, task family and authorization stay with
the caller (the data engine) and the dataset sealer.
"""
import hashlib
import json

from ..project_ledger import ENDED, ProjectLedger
from ..project_protocols import agent
from ..project_trace import agent_boundaries
from .parse import parse_transcript
from .tools import canonical_definitions


def encode(document):
    """Deterministic bytes for a stored transcript envelope."""
    return json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def session_transcript(execution_root, native_tools):
    """Return ``{"bytes", "sha256", "session_id", "status", "requests"}`` for an ended session.

    Refuses a running session, a pending operation, or any recorded model input
    that differs from the builder; never repairs or truncates.
    """
    list(agent_boundaries(execution_root))  # raises if any recorded input differs from the builder
    with ProjectLedger.read_snapshot(execution_root) as ledger:
        state = ledger.state()
    if state['status'] not in ENDED or state['pending'] is not None:
        raise ValueError('only an ended session without pending operations can be exported')
    messages = agent.build_input(state, native_tools=native_tools)['messages']
    agent.validate_conversation(messages, native_tools)
    raw = encode({'messages': messages, 'tools': canonical_definitions(native_tools)})
    parse_transcript(raw)
    return {'bytes': raw, 'sha256': hashlib.sha256(raw).hexdigest(), 'session_id': state['session_id'],
            'status': state['status'],
            'requests': [{'id': item['id'], 'termination_reason': item['termination_reason']}
                         for item in state['requests']]}
