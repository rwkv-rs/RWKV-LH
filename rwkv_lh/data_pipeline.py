"""Resume a registered production-trace correction batch through dataset admission.

Inputs are sealed reviewer-selected production boundaries, never invented tasks.
Uncertain API attempts block the batch; completed stages are content-bound.
"""
import json
from pathlib import Path

from . import trace_correction_pipeline as corrections
from .offline_teacher_api import exclusive, write_json
from .statetune_data import sealed


SCHEMA = 'rwkv-lh.data-pipeline.v1'
TERMINAL = {'quarantined', 'execution_validated_pending_dataset_gate'}


def prior_rows(registration):
    """Reuse sealed prior labels with their original provenance, never relabel them."""
    from .direct_trace_data import normalize_direct_row, replay_run
    sources = {s['source_id']: s for s in registration['sources']}
    rows, seen = [], set()
    for reference in registration.get('prior_exports', []):
        for row in sealed(reference)['rows']:
            source = sources[row['source_id']]
            manifest = sealed(source['manifest'])
            root = corrections.sealed_files(source['run_root'], manifest['files'])
            if (source['family'] in registration['held_out_families'] or source['split'] != 'train'
                    or row['family'] != source['family']
                    or row['source_manifest_sha256'] != source['manifest']['sha256']
                    or row['source_content_sha256'] != source['source_content_sha256']):
                raise ValueError('prior label source binding differs')
            normalize_direct_row(row, model_sha256=manifest['model_sha256'],
                context_tokens=registration['context_tokens'], vocab_size=registration['vocab_size'],
                bos_token_id=registration['bos_token_id'])
            actual = replay_run(root, manifest['model_sha256'])[row['candidate_checkpoint_id']]
            if any(row[k] != actual[k] for k in ('input_text', 'input_token_ids', 'input_checkpoint_id', 'request_id')):
                raise ValueError('prior label differs from production boundary')
            key = (manifest['files']['model_trace.jsonl'], row['candidate_checkpoint_id'])
            if key in seen:
                raise ValueError('duplicate prior production boundary')
            seen.add(key)
            rows.append(row)
    return rows, seen


def identity():
    root = Path(__file__).resolve().parents[1]
    return {**corrections.pipeline_identity(), **{name: corrections.file_sha(root / name)
        for name in ('rwkv_lh/data_pipeline.py', 'scripts/run_data_pipeline.py')}}


def preflight(registration):
    if registration.get('schema_version') != SCHEMA:
        raise ValueError('unsupported pipeline registration')
    plans = [sealed(ref) for ref in registration['plans']]
    if type(registration['max_jobs']) is not int or (registration['max_jobs'] < 1 or len(plans) > registration['max_jobs']
            or (not plans and not registration.get('prior_exports'))):
        raise ValueError('registered job budget exceeded or empty')
    sources = registration['sources']
    lookup = {source['source_id']: source for source in sources}
    if len(lookup) != len(sources):
        raise ValueError('duplicate source identity')
    _, boundaries = prior_rows(registration)
    for plan in plans:
        source = lookup[plan['source_id']]
        manifest = sealed(source['manifest'])
        if (source['split'] != 'train' or source['family'] in registration['held_out_families']
                or plan['family'] != source['family']
                or Path(plan['run_root']).resolve() != Path(source['run_root']).resolve()
                or manifest['files'] != plan['source_files']
                or manifest.get('source_type') != 'native_production_trace'
                or manifest.get('model_sha256') != plan['model_sha256']
                or not manifest.get('server_identity_sha256')
                or not manifest.get('collector_source_manifest_sha256')):
            raise ValueError('source attestation or training scope differs')
        if (corrections.file_sha(source['content_reference']['path']) != source['source_content_sha256']
                or source['content_reference']['sha256'] != source['source_content_sha256']):
            raise ValueError('source content changed')
        for name in ('collector_source_manifest', 'server_identity'):
            reference = manifest.get(name)
            if not reference or reference['sha256'] != manifest[name + '_sha256']:
                raise ValueError('source attestation requires sealed evidence references')
            sealed(reference)
        corrections.sealed_files(plan['run_root'], manifest['files'])
        boundary = (manifest['files']['model_trace.jsonl'], plan['checkpoint_id'])
        if boundary in boundaries:
            raise ValueError('duplicate production boundary')
        boundaries.add(boundary)
    if registration.get('freeze_template'):
        template = sealed(registration['freeze_template'])
        if template['sources'] != sources:
            raise ValueError('freeze sources differ from registered sources')
        from .statetune_core import verify_file
        verify_file(template['authorization']['path'], template['authorization']['sha256'])
        regression = sealed(template['regression_registration'])
        from .direct_trace_data import validate_split_isolation
        validate_split_isolation([*sources, *regression['cases']])
        if not {case['family'] for case in regression['cases']} <= set(registration['held_out_families']):
            raise ValueError('regression families must be excluded from training')
    return plans


def execute(registration_path, output, *, teacher=None):
    """Prepare everything before spending; teacher=None is an offline preflight.

    Passing a teacher completes validation/export/freeze, when registered. This
    never launches training or promotes a State. A frozen dataset is its output.
    """
    registration_path = Path(registration_path).resolve(strict=True)
    registration = json.loads(registration_path.read_text())
    plans = preflight(registration)
    root = Path(output).resolve()
    for plan in plans:
        source = Path(plan['run_root']).resolve()
        if root == source or root in source.parents or source in root.parents:
            raise ValueError('pipeline output overlaps source')
    root.mkdir(parents=True, exist_ok=True)
    binding = {'registration_sha256': corrections.file_sha(registration_path), 'code': identity()}
    with exclusive(root / '.pipeline.lock'):
        identity_path = root / 'IDENTITY.json'
        if identity_path.exists():
            if json.loads(identity_path.read_text()) != binding:
                raise ValueError('pipeline registration or code changed')
        else:
            write_json(identity_path, binding)
        jobs = []
        for index, plan in enumerate(plans):
            directory = root / 'jobs' / f'{index:04d}'
            packet = directory / 'PACKET.json'
            if packet.exists():
                value = json.loads(packet.read_text())
                if value['plan'] != plan or value['pipeline_identity'] != corrections.pipeline_identity():
                    raise ValueError('prepared job differs from registration')
            else:
                corrections.prepare(plan, directory)
            jobs.append({'directory': str(directory), 'packet_sha256': corrections.file_sha(packet)})
        batch = {'jobs': jobs, 'sources': registration['sources'],
                 'vocab_size': registration['vocab_size'], 'bos_token_id': registration['bos_token_id'],
                 'selection_policy': registration.get('selection_policy', {})}
        write_json(root / 'BATCH.json', batch)
        def status(phase, **fields):
            value = {'phase': phase, 'training_started': False, **fields}
            write_json(root / 'STATUS.json', value)
            return value
        if teacher is None:
            return status('prepared_no_api_calls', jobs=len(jobs))
        report = corrections.run_batch(batch, teacher=teacher) if jobs else corrections.summarize([])
        write_json(root / 'CANDIDATE_REPORT.json', report)
        if any(name not in TERMINAL for name in report['statuses']):
            return status('stopped_review_required', candidates=report['statuses'])
        export_path = root / 'REVIEWED_ROWS.json'
        export_receipt = root / 'EXPORT.json'
        if export_path.exists():
            if not export_receipt.exists() or json.loads(export_receipt.read_text())['sha256'] != corrections.file_sha(export_path):
                raise ValueError('export incomplete or changed; explicit reconciliation required')
            exported = json.loads(export_receipt.read_text())
        else:
            exported = corrections.export_candidates(batch, export_path)
            previous, _ = prior_rows(registration)
            if previous:
                value = json.loads(export_path.read_text())
                value['rows'] = previous + value['rows']
                value['prior_exports'] = registration['prior_exports']
                # Combined coverage is enforced again by the freeze gate.
                from collections import Counter
                policy = registration.get('selection_policy', {})
                counts = Counter(row['source_id'] for row in value['rows'])
                if policy.get('max_per_source') and max(counts.values()) > policy['max_per_source']:
                    raise ValueError('combined rows exceed registered per-source limit')
                if policy.get('deduplicate_targets_per_source'):
                    targets = [(row['source_id'], row['target_text']) for row in value['rows']]
                    if len(targets) != len(set(targets)):
                        raise ValueError('combined rows contain duplicate targets')
                write_json(export_path, value)
                exported.update(rows=len(value['rows']), sha256=corrections.file_sha(export_path))
            write_json(export_receipt, exported)
        if not registration.get('freeze_template'):
            return status('exported_pending_freeze_registration', export=exported)
        freeze = sealed(registration['freeze_template'])
        freeze['reviewed_rows'] = {'path': str(export_path), 'sha256': corrections.file_sha(export_path)}
        frozen_registration = root / 'FREEZE_REGISTRATION.json'
        if frozen_registration.exists() and json.loads(frozen_registration.read_text()) != freeze:
            raise ValueError('freeze registration changed')
        write_json(frozen_registration, freeze)
        dataset = Path(registration['dataset_output']).resolve()
        receipt = root / 'DATASET.json'
        if receipt.exists():
            published = json.loads(receipt.read_text())
            if corrections.file_sha(dataset / 'manifest.json') != published['manifest_sha256']:
                raise ValueError('published dataset changed')
        elif dataset.exists():
            raise ValueError('unreceipted dataset exists; explicit reconciliation required')
        else:
            from .direct_trace_data import freeze_direct_dataset
            try:
                freeze_direct_dataset(freeze, registration_reference={
                    'path': str(frozen_registration), 'sha256': corrections.file_sha(frozen_registration)}, output=dataset)
            except ValueError as exc:
                return status('dataset_gate_rejected', export=exported, reason=str(exc))
            published = {'path': str(dataset), 'manifest_sha256': corrections.file_sha(dataset / 'manifest.json')}
            write_json(receipt, published)
        from .statetune_data import admit_dataset
        # Recheck every published file and source before reporting readiness.
        admit_dataset({'path': str(dataset / 'manifest.json'), 'sha256': published['manifest_sha256']},
                      role=freeze['role'], model_sha256=freeze['model_sha256'],
                      expected_regression=freeze['regression_fingerprint'],
                      context_tokens=freeze['context_tokens'], vocab_size=freeze['vocab_size'],
                      bos_token_id=freeze['bos_token_id'])
        return status('dataset_admitted', export=exported, dataset=published)


def consume_inbox(inbox, output, *, teacher, max_batches, max_jobs, max_seconds,
                  poll_seconds=5):
    """Consume sealed registered batches until a persistent deadline/budget.

    Drop complete JSON registrations into the inbox via atomic rename. Same
    boundary cannot be purchased again under another batch name. New tasks still
    need source registration and public checks; this function synthesizes neither.
    """
    import math
    import time
    if (type(max_batches) is not int or max_batches < 1 or type(max_jobs) is not int or max_jobs < 1
            or not math.isfinite(max_seconds) or not 0 < max_seconds <= 72 * 3600
            or not 0 < poll_seconds <= 30):
        raise ValueError('bounded inbox budgets required')
    inbox, root = Path(inbox).resolve(strict=True), Path(output).resolve()
    if root == inbox or root in inbox.parents or inbox in root.parents:
        raise ValueError('inbox and output must not overlap')
    root.mkdir(parents=True, exist_ok=True)
    binding = {'code': identity(), 'inbox': str(inbox), 'max_batches': max_batches,
               'max_jobs': max_jobs, 'max_seconds': max_seconds,
               'provider': teacher.config}
    with exclusive(root / '.inbox.lock'):
        ledger_path = root / 'INBOX.json'
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text())
            if ledger['identity'] != binding:
                raise ValueError('inbox identity or budget changed')
        else:
            ledger = {'identity': binding, 'deadline': time.time() + max_seconds, 'batches': {}}
            write_json(ledger_path, ledger)
        class DeadlineTeacher:
            def complete(self, system, user):
                if time.time() >= ledger['deadline']:
                    raise TimeoutError('inbox deadline before provider request')
                return teacher.complete(system, user)
        def status(phase, **fields):
            value = {'phase': phase, 'batches': len(ledger['batches']), 'training_started': False, **fields}
            write_json(root / 'STATUS.json', value)
            return value
        while time.time() < ledger['deadline']:
            for path in sorted(inbox.glob('*.json')):
                key, checksum = path.name, corrections.file_sha(path)
                previous = ledger['batches'].get(key)
                if previous:
                    if previous['sha256'] != checksum:
                        raise ValueError('admitted inbox registration changed')
                    continue
                if len(ledger['batches']) >= max_batches:
                    return status('batch_budget_exhausted')
                registration = json.loads(path.read_text())
                plans = preflight(registration)
                boundaries = [[p['source_files']['model_trace.jsonl'], p['checkpoint_id']] for p in plans]
                old = [b for value in ledger['batches'].values() for b in value['boundaries']]
                if any(b in old for b in boundaries):
                    raise ValueError('duplicate production boundary across inbox batches')
                if len(old) + len(boundaries) > max_jobs:
                    return status('job_budget_exhausted')
                ledger['batches'][key] = {'sha256': checksum, 'boundaries': boundaries, 'status': 'pending'}
                write_json(ledger_path, ledger)
            for key, batch in ledger['batches'].items():
                if batch['status'] == 'completed':
                    continue
                if time.time() >= ledger['deadline']:
                    return status('deadline')
                path = inbox / key
                if corrections.file_sha(path) != batch['sha256']:
                    raise ValueError('admitted inbox registration changed')
                result = execute(path, root / 'batches' / Path(key).stem, teacher=DeadlineTeacher())
                batch['result'] = result
                if result['phase'] not in {'dataset_admitted', 'exported_pending_freeze_registration'}:
                    batch['status'] = 'stopped_review_required'
                    write_json(ledger_path, ledger)
                    return status('stopped_review_required', active_batch=key, result=result)
                batch['status'] = 'completed'
                write_json(ledger_path, ledger)
            if len(ledger['batches']) == max_batches:
                return status('registered_batches_completed')
            status('waiting_for_registered_sources')
            time.sleep(min(poll_seconds, max(0, ledger['deadline'] - time.time())))
        return status('deadline')


def review_existing(job, review_reference, output):
    """Reassess an unchanged recorded API candidate, with zero provider requests.

    An explicit attributed human review can disagree with the teacher reviewer.
    Neither the target nor the public execution contract can be edited here.
    All source/token/execution/fresh-freeze gates still apply.
    """
    job = Path(job).resolve(strict=True)
    packet = json.loads((job / 'PACKET.json').read_text())
    original = json.loads((job / 'AUTHOR.json').read_text())
    review = sealed(review_reference)
    expected = {'packet_sha256', 'author_sha256', 'reviewer', 'independent', 'judgment'}
    if (set(review) != expected or review['packet_sha256'] != corrections.file_sha(job / 'PACKET.json')
            or review['author_sha256'] != corrections.file_sha(job / 'AUTHOR.json')
            or not isinstance(review['reviewer'], str) or not review['reviewer'].strip()
            or review['independent'] is not False):
        raise ValueError('explicit bound single-author human review required')
    from .correction_review import build_review_packet, validate_review
    candidate = json.dumps(original['envelope'], ensure_ascii=False, separators=(',', ':'))
    validate_review(build_review_packet(actual_rwkv_input=packet['actual']['input_text'],
                                       candidate=candidate), review['judgment'])
    class RecordedTeacher:
        calls = 0
        def complete(self, system, user):
            self.calls += 1
            if self.calls == 1:
                return original['envelope'], original['identity']
            if self.calls == 2:
                return review['judgment'], {'model': 'human-review', 'reviewer_id': review['reviewer'],
                                           'review_reference': review_reference}
            raise RuntimeError('recorded candidate cannot generate new responses')
    out = Path(output).resolve()
    origin = {'original_packet': {'path': str(job / 'PACKET.json'), 'sha256': corrections.file_sha(job / 'PACKET.json')},
              'original_author': {'path': str(job / 'AUTHOR.json'), 'sha256': corrections.file_sha(job / 'AUTHOR.json')},
              'review_reference': review_reference, 'provider_requests': 0}
    if out.exists():
        if not (out / 'REVIEW_ORIGIN.json').exists() or json.loads((out / 'REVIEW_ORIGIN.json').read_text()) != origin:
            raise ValueError('review output exists without matching origin')
        prepared = {'packet_sha256': corrections.file_sha(out / 'PACKET.json')}
    else:
        prepared = corrections.prepare(packet['plan'], out)
        write_json(out / 'REVIEW_ORIGIN.json', origin)
    return corrections.run(out, expected_packet_sha256=prepared['packet_sha256'], teacher=RecordedTeacher())
