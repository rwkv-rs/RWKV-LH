"""Pinned, re-extracted correction queues. No labels or training admission."""
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile

from .project_contracts import digest
from .project_ledger import ProjectLedger
from .project_protocols import planner, decision, executor
from .project_role_data import file_sha
from .project_trace import role_boundaries


def prepare_queue(manifest_path, expected_manifest_sha256, output):
    manifest_path, output = Path(manifest_path), Path(output)
    if output.exists():
        raise FileExistsError(output)
    if file_sha(manifest_path) != expected_manifest_sha256:
        raise ValueError('manifest identity mismatch')
    manifest = json.loads(manifest_path.read_text())
    registration = Path(manifest['source_registration'])
    if file_sha(registration) != manifest['source_registration_sha256']:
        raise ValueError('registration identity mismatch')
    provenance = json.loads(registration.read_text())
    if manifest['source_purpose'] != 'production_training_source' or provenance.get('source_purpose') != manifest['source_purpose']:
        raise ValueError('evaluation sources cannot enter production correction queue')
    group = provenance.get('source_group')
    if not isinstance(group, str) or not group.strip():
        raise ValueError('registered source group required')
    for name, module in (('planner', planner), ('decision', decision), ('executor', executor)):
        if manifest['protocol_modules'][name] != {'protocol':module.PROTOCOL,'sha256':file_sha(module.__file__)}:
            raise ValueError('current protocol identity mismatch')
    source = Path(manifest['source_ledger']).resolve()
    resolved_output = output.resolve()
    if resolved_output == source or source in resolved_output.parents or resolved_output in source.parents:
        raise ValueError('queue must not overlap source ledger')
    with ProjectLedger.read_snapshot(source) as ledger:
        return _prepare_locked(ledger, manifest, manifest_path, expected_manifest_sha256,
                               registration, output, group)


def _prepare_locked(ledger, manifest, manifest_path, expected_manifest_sha256, registration, output, group):
    source = ledger.root
    tip = manifest['source_event_chain_tip']
    if ledger.verified_events()[-1]['digest'] != tip:
        raise ValueError('source chain differs from pinned extraction')
    rows = list(role_boundaries(source))
    if dict(Counter(row['role'] for row in rows)) != manifest['counts']:
        raise ValueError('reconstructed source counts differ')
    rows = [row for row in rows if row['role'] in ('decision','executor')]
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.review-queue-', dir=output.parent))
    try:
        (staging/'author').mkdir()
        (staging/'audit').mkdir()
        identities = {}
        for row in rows:
            key = digest([row['source_event_digest'], row['result_event_digest'], row['operation_id']])
            # Future results/checkpoints are audit-only; never add them to author input.
            author = {name:row[name] for name in ('operation_id','role','input')}
            author['input_digest'] = digest(row['input'])
            for folder, value in (('author',author),('audit',row)):
                path = staging/folder/(key+'.json')
                path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
                identities[str(path.relative_to(staging))] = file_sha(path)
        if (ledger.verified_events()[-1]['digest'] != tip or
                file_sha(registration) != manifest['source_registration_sha256'] or
                file_sha(manifest_path) != expected_manifest_sha256):
            raise ValueError('source changed during queue construction')
        summary = {'source_manifest_sha256':expected_manifest_sha256,
                   'source_group':group,'counts':dict(Counter(row['role'] for row in rows)),
                   'files':identities,'training_eligible':False,'labels_created':0,
                   'generator_sha256':file_sha(__file__),
                   'reconstructor_sha256':file_sha(Path(__file__).with_name('project_trace.py')),
                   'warning':'File separation is not access isolation. Only mount author/ for correction authors. Source authenticity, Native replay, reviewer identity and semantic evidence remain separate gates.'}
        (staging/'manifest.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        staging.rename(output)
        return summary
    finally:
        if staging.exists():
            shutil.rmtree(staging)
