"""Re-extract original Project production boundaries before any label admission.

This source seal is evidence, not a training dataset or authority to invent labels.
No tools or models are called while sealing or loading an existing source.
"""
import json
from pathlib import Path

from . import statetune_core as core
from .goal_state_protocols.role_trace_dataset_v1 import _source_path
from .project_contracts import digest
from .project_generation_snapshots import validate_snapshots
from .project_ledger import ProjectLedger
from .project_trace import role_boundaries
from .project_token_data import replay_native_rows
from .workspace_snapshot import tree_identity

SOURCE_SCHEMA = 'rwkv-lh.project-production-source.v1'
_REQUIRED_MODULES = (
    'project_runtime.py', 'project_agent.py', 'project_ledger.py', 'project_trace.py', 'project_token_data.py',
    'project_generation_snapshots.py', 'project_protocols/decision.py', 'project_protocols/executor.py')


def read_reference(reference):
    core.require(isinstance(reference, dict) and set(reference) == {'path', 'sha256'},
                 'exact sealed Project source reference required')
    path = _source_path(Path(reference['path']))
    return core.read_sealed_json(path, reference['sha256'])


def _source(root, collection_reference, source_reference):
    collection = read_reference(collection_reference)
    registered = read_reference(source_reference)
    core.require(collection.get('source_purpose') == registered.get('source_purpose')
                 == 'production_training_source', 'Project source is not registered production training provenance')
    core.verify_file(_source_path(Path(collection['authorization'])), collection['authorization_sha256'])
    matches = [item for item in collection['items'] if item.get('id') == registered.get('id')]
    core.require(len(matches) == 1, 'Project source is not unique in collection registration')
    item = matches[0]
    core.require(item.get('source_registration_sha256') == source_reference['sha256']
                 and {k: v for k, v in item.items() if k != 'source_registration_sha256'} == registered,
                 'Project source registration differs from preregistered collection')
    core.require(registered.get('split') in ('train', 'dev', 'confirmation')
                 and bool(registered.get('source_group')) and bool(registered.get('repository_family')),
                 'Project source group and preregistered split required')
    package = Path(__file__).resolve().parent
    # Current role protocols must be byte-identical. Source runtime identity and
    # the present read-only re-extractor are separately recorded; every input
    # and token is still rebuilt by the single current production builder.
    for name in ('project_protocols/decision.py', 'project_protocols/executor.py'):
        core.require(collection['runtime_files'].get('rwkv_lh/' + name) == core.sha256_file(package / name),
                     'Project source renderer or runtime differs from registered production')
    root = _source_path(Path(root))
    with ProjectLedger.read_snapshot(root) as ledger:
        before = tree_identity(root, exclude_git=False)
        return _read_locked_source(ledger, before, collection, registered)


def _read_locked_source(ledger, before, collection, registered):
    root = ledger.root
    events = ledger.verified_events()
    state = events[-1]['state']
    core.require(state['pending'] is None, 'Project source has an unknown pending operation')
    result = json.loads((root / 'RESULT.json').read_text())
    core.require(result.get('status') in ('completed', 'blocked', 'interrupted')
                 and result.get('model_calls') == state['calls']
                 and result.get('diagnostics', {}).get('pending_operation') is None
                 and state.get('record_generation_snapshots') is True,
                 'Project source must have ended with production snapshots enabled')
    core.require(state.get('request') == registered['request'] and state.get('task_id') == registered['id'],
                 'Project source request/task differs from collection registration')
    rows = list(role_boundaries(root, read_only=True))
    core.require(bool(rows), 'Project source contains no returned model boundaries')
    snapshots = validate_snapshots(ledger, [row['operation_id'] for row in rows])
    replayed = replay_native_rows(rows)
    core.require(bool(replayed), 'Project source contains no original Native generation')
    for replay in replayed.values():
        identity = collection['roles']['project_' + replay['row']['role']]
        core.require((replay['model_sha256'], replay['state_profile_id'], replay['state_profile_sha256'])
                     == (identity['model_sha256'], identity['state_profile_id'], identity['state_profile_sha256']),
                     'Project source model/State differs from registered collection')
    core.require(before == tree_identity(root, exclude_git=False)
                 and events[-1]['digest'] == ledger.verified_events()[-1]['digest'],
                 'Project production source changed during re-extraction')
    return {'ledger': ledger, 'rows': rows, 'replayed': replayed, 'snapshots': snapshots,
            'tree': before, 'event_root': events[0]['digest'], 'event_tip': events[-1]['digest'], 'registered': registered,
            'collection': collection, 'ledger_sha256': core.sha256_file(ledger.path)}


def _manifest(source, collection_reference, source_reference):
    registered = source['registered']
    return {'schema_version': SOURCE_SCHEMA, 'purpose': 'verified_project_source_only',
        'source_purpose': registered['source_purpose'], 'source_group': registered['source_group'],
        'repository_family': registered['repository_family'], 'split': registered['split'],
        'source_root': str(source['ledger'].root), 'collection_registration': dict(collection_reference),
        'source_registration': dict(source_reference), 'source_event_chain_root': source['event_root'],
        'source_event_chain_tip': source['event_tip'],
        'source_ledger_sha256': source['ledger_sha256'], 'artifact_tree': source['tree'],
        'extractor_sha256': core.sha256_file(__file__),
        'extractor_modules': {name: core.sha256_file(Path(__file__).resolve().parent / name)
                              for name in _REQUIRED_MODULES},
        'original_runtime_files': source['collection']['runtime_files'],
        'returned_models': len(source['rows']), 'native_replayed': len(source['replayed']),
        'snapshots_verified': len(source['snapshots']), 'training_eligible': False}


def seal_source(root, *, collection_reference, source_reference, output):
    output = _source_path(Path(output))
    root = _source_path(Path(root))
    core.require(root not in output.parents and root != output,
                 'Project source seal must be outside original source records')
    core.require(not output.exists(), 'Project source seal already exists')
    source = _source(root, collection_reference, source_reference)
    manifest = _manifest(source, collection_reference, source_reference)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, sort_keys=True) + '\n')
    return {'path': str(output), 'sha256': core.sha256_file(output)}


def load_source(reference):
    manifest = read_reference(reference)
    core.require(manifest.get('schema_version') == SOURCE_SCHEMA
                 and manifest.get('purpose') == 'verified_project_source_only'
                 and manifest.get('extractor_sha256') == core.sha256_file(__file__),
                 'Project source requires the current verified source re-extractor')
    root = _source_path(Path(manifest['source_root']))
    core.require(manifest['artifact_tree'] == tree_identity(root, exclude_git=False),
                 'Project source file inventory or checksum differs from seal')
    source = _source(root, manifest['collection_registration'], manifest['source_registration'])
    core.require(manifest == _manifest(source, manifest['collection_registration'], manifest['source_registration']),
                 'Project source manifest differs from independent re-extraction')
    return {**source, 'manifest': manifest, 'reference': dict(reference)}
