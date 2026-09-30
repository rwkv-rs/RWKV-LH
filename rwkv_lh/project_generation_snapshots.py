"""Optional correction evidence at real Project model boundaries, never model input."""
import hashlib
import json
from pathlib import Path

from .project_contracts import digest
from .workspace_snapshot import copy_verified_workspace, tree_identity

SNAPSHOT_SCHEMA = 'rwkv-lh.project-generation-snapshot.v1'


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def capture_snapshot(ledger, identifier):
    events = ledger.verified_events()
    event = events[-1]
    state = event['state']
    pending = state['pending']
    if (event['kind'] != 'operation_started' or not pending
            or pending['id'] != identifier or pending['kind'] != 'model'):
        raise ValueError('snapshot requires the actual newly started model operation')
    directory = ledger.root / 'generation_snapshots' / identifier
    directory.mkdir(parents=True, exist_ok=False)
    tree = copy_verified_workspace(state['workspace'], directory / 'before', exclude_git=False,
                                   audit_path=directory / 'COPY.json')
    if digest(tree) != pending['workspace_digest']:
        raise ValueError('workspace changed after the model input was constructed')
    intent = pending['payload']
    record = {'schema_version': SNAPSHOT_SCHEMA, 'operation_id': identifier,
        'role': intent['role'], 'lane': intent['lane'], 'input_digest': intent['input_digest'],
        'source_event_digest': event['digest'], 'workspace_digest': digest(tree)}
    manifest = directory / 'SNAPSHOT.json'
    manifest.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    reference = {'path': str(manifest.relative_to(ledger.root)), 'sha256': _sha(manifest)}
    def register(current):
        if current['pending'] != pending:
            raise ValueError('model operation changed during snapshot')
        current.setdefault('generation_snapshots', {})[identifier] = reference
    ledger.update('generation_snapshot_saved', register)
    return directory / 'before'


def validate_snapshot(ledger, identifier):
    """Reverify one original generation through the same batch validator."""
    return validate_snapshots(ledger, [identifier])[identifier]


def validate_snapshots(ledger, identifiers):
    """Verify one fresh event chain and every requested snapshot's original bytes.

    Callers cannot supply cached events. Offline callers hold the source read
    lease for this whole operation, including workspace and manifest checks.
    """
    identifiers = tuple(identifiers)
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('snapshot batch requires unique operation identifiers')
    if not identifiers:
        return {}
    events = ledger.verified_events()
    starts = {}
    for index, event in enumerate(events):
        if event['kind'] == 'operation_started':
            identifier = event['state']['pending']['id']
            starts.setdefault(identifier, []).append((index, event))
    return {identifier: _validate_snapshot(ledger, identifier, events, starts.get(identifier, []))
            for identifier in identifiers}


def _validate_snapshot(ledger, identifier, events, starts):
    if len(starts) != 1:
        raise ValueError('snapshot requires a unique original model operation')
    index, started = starts[0]
    pending = started['state']['pending']
    if pending['kind'] != 'model' or index + 1 >= len(events):
        raise ValueError('missing model snapshot event')
    saved = events[index + 1]
    if saved['kind'] != 'generation_snapshot_saved' or saved['state']['pending'] != pending:
        raise ValueError('snapshot was not saved immediately before the actual model call')
    reference = saved['state'].get('generation_snapshots', {}).get(identifier)
    if reference is None or events[-1]['state'].get('generation_snapshots', {}).get(identifier) != reference:
        raise ValueError('snapshot identity changed after generation')
    manifest = ledger.root / 'generation_snapshots' / identifier / 'SNAPSHOT.json'
    if (reference.get('path') != str(manifest.relative_to(ledger.root))
            or manifest.resolve(strict=True) != manifest or reference.get('sha256') != _sha(manifest)):
        raise ValueError('snapshot manifest identity differs')
    intent = pending['payload']
    expected = {'schema_version': SNAPSHOT_SCHEMA, 'operation_id': identifier,
        'role': intent['role'], 'lane': intent['lane'], 'input_digest': intent['input_digest'],
        'source_event_digest': started['digest'], 'workspace_digest': pending['workspace_digest']}
    if json.loads(manifest.read_text()) != expected:
        raise ValueError('snapshot does not bind the original model input')
    before = manifest.parent / 'before'
    if before.resolve(strict=True) != before or digest(tree_identity(before)) != expected['workspace_digest']:
        raise ValueError('snapshot workspace identity differs')
    return before
