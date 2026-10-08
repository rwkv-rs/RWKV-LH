"""Freeze reviewed Project boundaries and one immutable regression per role.

The publisher re-extracts every source. Training re-extracts train rows only;
evaluation content is hash-checked, with hashed 5-gram counts for leakage checks.
"""
from collections import Counter
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from . import statetune_core as core
from .goal_state_protocols.role_trace_dataset_v1 import _source_path
from .model_io import JSON_CALL_STOP_SUFFIXES
from .project_contracts import digest
from .project_training_labels import load_reviewed_candidates
from .project_training_sources import read_reference, SOURCE_SCHEMA
from .role_trace_artifacts import _canonical_bytes, _grams, _cosine_parts, _publish_no_replace
from .token_budget import VOCAB_PATH
from .workspace_snapshot import tree_identity

SPLITS = ('train', 'dev', 'confirmation')
REGRESSION_SCHEMA = 'rwkv-lh.project-fixed-regression.v1'
INDEX_SCHEMA = 'rwkv-lh.project-fixed-regression-index.v1'
PROOF_SCHEMA = 'rwkv-lh.project-freeze-proof.v1'
REGRESSION_ROOT = Path(__file__).resolve().parents[1] / 'data/statetune_regressions'
SIMILARITY = {'name': 'count_vector_cosine', 'encoding': 'utf-8', 'ngram_bytes': 5,
              'threshold': 0.95, 'comparison': 'cross_split_same_role', 'index_keys': 'sha256_of_gram_bytes'}


def _reference(path):
    return {'path': str(path), 'sha256': core.sha256_file(path)}


def _write(path, value):
    path.write_bytes(_canonical_bytes(value) + b'\n')


def _function(row):
    return json.loads(row['target_text'][:-len(JSON_CALL_STOP_SUFFIXES[0])])['function']


def _member(row):
    payload = row['input']
    boundary = [payload['assignment']['id'], payload['current_step'], payload['step_reports'],
                payload['selected_evidence'], payload['observations']]
    # The verified ledger genesis survives copied/resealed manifests and later
    # source completion. Retries at one semantic boundary still count once.
    lineage = row['source_lineage_digest']
    core.require(isinstance(lineage, str) and len(lineage) == 64
                 and all(c in '0123456789abcdef' for c in lineage), 'Project source lineage is invalid')
    return {k: row[k] for k in ('sample_id', 'split', 'repository_family', 'source_group',
        'source_manifest', 'source_lineage_digest', 'source_operation_id', 'source_event_digest', 'review_reference')} | {
        'boundary_id': digest([lineage, row['role'], boundary]),
        'input_sha256': hashlib.sha256(row['input_text'].encode()).hexdigest()}


def _metadata_audit(members, minimum):
    core.require(bool(members) and len({m['sample_id'] for m in members}) == len(members),
                 'empty or duplicate Project sample identity')
    families, groups = {}, {}
    for member in members:
        core.require(member['split'] in SPLITS, 'unknown Project split')
        for field, seen in (('repository_family', families), ('source_group', groups)):
            key = member[field]
            core.require(isinstance(key, str) and key.strip(), 'Project source family/group required')
            seen.setdefault(key.strip().casefold(), set()).add(member['split'])
    core.require(all(len(splits) == 1 for seen in (families, groups) for splits in seen.values()),
                 'Project source family/group crosses registered splits')
    counts = {s: sum(m['split'] == s for m in members) for s in SPLITS}
    boundaries = {s: len({m['boundary_id'] for m in members if m['split'] == s}) for s in SPLITS}
    core.require(set(minimum) == set(SPLITS) and all(type(minimum[s]) is int and minimum[s] > 0
                 and boundaries[s] >= minimum[s] for s in SPLITS),
                 'registered distinct Project boundary coverage is not met')
    return counts, boundaries


def _vector(text):
    # Hashing gram keys preserves the same count-vector cosine without storing
    # evaluation text fragments in the index used by training admission.
    grams = _grams(text)
    result = {hashlib.sha256(gram).hexdigest(): count for gram, count in grams.items()}
    core.require(len(result) == len(grams), '5-gram index hash collision')
    return result


def _similarity_audit(members, vectors):
    comparisons = 0
    for i, left in enumerate(members):
        for right in members[i + 1:]:
            if left['split'] == right['split']:
                continue
            comparisons += 1
            a, b = vectors[left['sample_id']], vectors[right['sample_id']]
            dot, a_sq, b_sq = _cosine_parts(a, b)
            too_close = (dot * dot * 10000 >= 9025 * a_sq * b_sq if a_sq and b_sq
                         else left['input_sha256'] == right['input_sha256'])
            core.require(not too_close, 'Project cross-split 5-gram similarity reaches 0.95')
    return comparisons


def audit_rows(rows, minimum_boundaries, required_functions):
    core.require(len({r['role'] for r in rows}) == 1, 'Project audit must contain exactly one role')
    members = [_member(row) for row in rows]
    counts, boundaries = _metadata_audit(members, minimum_boundaries)
    core.require(set(required_functions) == set(SPLITS), 'registered function coverage must cover all splits')
    coverage = {s: dict(Counter(_function(r) for r in rows if r['split'] == s)) for s in SPLITS}
    for split, required in required_functions.items():
        core.require(isinstance(required, list) and bool(required)
                     and len(set(required)) == len(required)
                     and all(isinstance(f, str) and f in coverage[split] for f in required),
                     'registered Project function coverage is not met')
    comparisons = _similarity_audit(members, {r['sample_id']: _vector(r['input_text']) for r in rows})
    return {'status': 'valid', 'quality_gates': {'verified_labels': True, 'family_isolation': True,
        'distinct_boundaries': True, 'function_coverage': True, 'cross_split_similarity': True},
        'counts': counts, 'distinct_boundaries': boundaries, 'function_counts': coverage,
        'compared_pairs': comparisons, 'similarity_parameters': SIMILARITY,
        'split_algorithm': 'immutable_source_registration_by_repository_family'}


def _registration(registration, reference):
    from .statetune_data import FREEZE_SCHEMA, _protocol
    core.require(read_reference(reference) == registration, 'Project freeze registration differs from sealed record')
    expected = {'schema_version', 'role', 'authorization', 'candidates', 'model_sha256', 'context_tokens',
        'vocab_size', 'bos_token_id', 'minimum_boundaries', 'required_functions', 'regression_fingerprint'}
    core.require(set(registration) == expected and registration['schema_version'] == FREEZE_SCHEMA
                 and registration['role'] == 'project_executor',
                 'Project freeze/re-extraction requires a complete current registration')
    auth = registration['authorization']
    core.require(set(auth) == {'path', 'sha256'}, 'sealed Project owner authorization required')
    core.verify_file(_source_path(Path(auth['path'])), auth['sha256'])
    core.require(isinstance(registration['candidates'], list) and bool(registration['candidates'])
                 and len({digest(r) for r in registration['candidates']}) == len(registration['candidates']),
                 'unique original Project review references required')
    core.require(type(registration['context_tokens']) is int and registration['context_tokens'] > 0
                 and registration['vocab_size'] == 65536 and registration['bos_token_id'] == 0,
                 'registered complete RWKV context/vocabulary/BOS required')
    return _protocol(registration['role'])


def _check_rows(rows, registration):
    from .statetune_data import normalize_row
    for row in rows:
        core.require(row['role'] == registration['role'] and row['context_tokens'] == registration['context_tokens'],
                     'Project candidate role/context differs from registration')
        normalize_row(row, role=registration['role'], model_sha256=registration['model_sha256'],
            context_tokens=registration['context_tokens'], vocab_size=registration['vocab_size'],
            bos_token_id=registration['bos_token_id'], expected_split=row['split'])


def _prior(registration):
    folder = _source_path(REGRESSION_ROOT / registration['role'])
    if not folder.exists():
        core.require(registration['regression_fingerprint'] is None, 'registered immutable regression is absent')
        return folder, None, None
    index = json.loads((folder / 'index.json').read_text())
    core.require(index.get('schema_version') == INDEX_SCHEMA and registration['regression_fingerprint']
                 == index.get('fingerprint'), 'immutable regression cannot be reset or replaced')
    path = core.verify_file(folder / 'regression.json', index['regression_sha256'])
    regression = json.loads(path.read_text())
    actual = {k: v for k, v in regression.items() if k != 'fingerprint'}
    core.require(digest(actual) == regression['fingerprint'] == index['fingerprint'],
                 'immutable regression fingerprint differs')
    for name in ('role', 'model_sha256', 'context_tokens'):
        core.require(regression[name] == registration[name], 'immutable regression identity differs')
    for name in ('minimum_boundaries', 'required_functions'):
        core.require(regression[name] == {s: registration[name][s] for s in SPLITS[1:]},
                     'immutable regression coverage requirements differ')
    return folder, index, regression


def _manifest(registration, registration_reference, proof, proof_member):
    from .statetune_data import DATASET_SCHEMA, _protocol
    protocol, protocol_sha = _protocol(registration['role'])
    return {'schema_version': DATASET_SCHEMA, 'purpose': 'frozen_role_training',
        'role': registration['role'], 'input_protocol': protocol, 'protocol_sha256': protocol_sha,
        'model_sha256': registration['model_sha256'], 'tokenizer_sha256': core.sha256_file(VOCAB_PATH),
        'freeze_registration': dict(registration_reference), 'authorization': registration['authorization'],
        'counts': proof['audit']['counts'], 'candidate_audit': proof['audit'],
        'train': proof['train'], 'regression': proof['regression'], 'project_freeze': proof_member}


def _provenance_files(rows):
    """Keep hash references in the fixed index, never evaluation text or labels."""
    references = {}
    for row in rows:
        review = read_reference(row['review_reference'])
        registration = read_reference(review['review_registration'])
        source = read_reference(row['source_manifest'])
        collection = read_reference(source['collection_registration'])
        items = [row['review_reference'], review['review_registration'], review['trace'], registration['packet'],
            row['source_manifest'], source['collection_registration'], source['source_registration'],
            {'path': collection['authorization'], 'sha256': collection['authorization_sha256']}]
        for reference in items: references[digest(reference)] = reference
    return [references[key] for key in sorted(references)]


def freeze_project_dataset(registration, *, registration_reference, output):
    protocol, protocol_sha = _registration(registration, registration_reference)
    output = _source_path(Path(output).absolute())
    core.require(not output.exists(), 'Project dataset output already exists')
    registry, prior_index, prior = _prior(registration)
    rows = load_reviewed_candidates(registration['candidates'])
    if prior:
        core.require(all(r['split'] == 'train' for r in rows), 'later Project freezes accept new train rows only')
        rows += [r for split in SPLITS[1:] for r in prior['samples_by_split'][split]]
    _check_rows(rows, registration)
    rows.sort(key=lambda r: r['sample_id'])
    audit = audit_rows(rows, registration['minimum_boundaries'], registration['required_functions'])
    members = [_member(row) for row in rows]
    for member in members:
        source = read_reference(member['source_manifest'])
        root = Path(source['source_root']).resolve()
        core.require(root != output and root not in output.parents, 'Project dataset overlaps original source')
    regression = prior or {'schema_version': REGRESSION_SCHEMA, 'role': registration['role'],
        'model_sha256': registration['model_sha256'], 'input_protocol': protocol, 'protocol_sha256': protocol_sha,
        'context_tokens': registration['context_tokens'],
        'minimum_boundaries': {s: registration['minimum_boundaries'][s] for s in SPLITS[1:]},
        'required_functions': {s: registration['required_functions'][s] for s in SPLITS[1:]},
        'samples_by_split': {s: [r for r in rows if r['split'] == s] for s in SPLITS[1:]}}
    if not prior:
        regression['fingerprint'] = digest(regression)
    regression_bytes = _canonical_bytes(regression) + b'\n'
    regression_sha = hashlib.sha256(regression_bytes).hexdigest()
    index = prior_index or {'schema_version': INDEX_SCHEMA, 'role': registration['role'],
        'fingerprint': regression['fingerprint'], 'regression_sha256': regression_sha,
        'members': [m for m in members if m['split'] != 'train'],
        'function_counts': {s: audit['function_counts'][s] for s in SPLITS[1:]},
        'provenance_files': _provenance_files([r for r in rows if r['split'] != 'train']),
        'similarity_parameters': SIMILARITY,
        'similarity_vectors': {r['sample_id']: _vector(r['input_text']) for r in rows if r['split'] != 'train'}}
    core.require(index['regression_sha256'] == regression_sha, 'immutable regression bytes changed')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.' + output.name + '.freeze-', dir=output.parent))
    try:
        (staging / 'train.jsonl').write_bytes(b''.join(_canonical_bytes(r) + b'\n' for r in rows if r['split'] == 'train'))
        (staging / 'regression.json').write_bytes(regression_bytes)
        REGRESSION_ROOT.mkdir(parents=True, exist_ok=True)
        with (REGRESSION_ROOT / (registration['role'] + '.lock')).open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if prior:
                core.require(_reference(registry / 'index.json')['sha256'] == hashlib.sha256(
                    _canonical_bytes(index) + b'\n').hexdigest(), 'immutable registry changed during freeze')
                core.verify_file(registry / 'regression.json', regression_sha)
            else:
                core.require(not registry.exists(), 'immutable regression was concurrently published')
                temporary = Path(tempfile.mkdtemp(prefix='.regression-', dir=REGRESSION_ROOT))
                try:
                    (temporary / 'regression.json').write_bytes(regression_bytes)
                    _write(temporary / 'index.json', index)
                    _publish_no_replace(temporary, registry)
                finally:
                    if temporary.exists(): shutil.rmtree(temporary)
            proof = {'schema_version': PROOF_SCHEMA, 'generator_sha256': core.sha256_file(__file__),
                'registration': dict(registration_reference), 'registry_index': _reference(registry / 'index.json'),
                'members': members, 'audit': audit,
                'train': {'file': 'train.jsonl', 'sha256': core.sha256_file(staging / 'train.jsonl')},
                'regression': {'file': 'regression.json', 'sha256': regression_sha,
                               'fingerprint': regression['fingerprint']}}
            _write(staging / 'freeze_proof.json', proof)
            manifest = _manifest(registration, registration_reference, proof,
                {'file': 'freeze_proof.json', 'sha256': core.sha256_file(staging / 'freeze_proof.json')})
            _write(staging / 'manifest.json', manifest)
            _publish_no_replace(staging, output)
        return manifest
    finally:
        if staging.exists(): shutil.rmtree(staging)


def admit_project_dataset(reference, *, role, expected_regression, model_sha256,
                          context_tokens, vocab_size, bos_token_id):
    from .statetune_data import _member as member_file, normalize_row
    manifest = read_reference(reference)
    core.require(isinstance(manifest.get('project_freeze'), dict),
                 'Project freeze/re-extraction proof is required; declared flags are not authority')
    root = Path(reference['path']).parent
    proof = read_reference(_reference(member_file(root, manifest['project_freeze'])))
    core.require(proof.get('schema_version') == PROOF_SCHEMA
                 and proof.get('generator_sha256') == core.sha256_file(__file__),
                 'current Project freeze/re-extraction publisher proof required')
    reg_ref = proof['registration']; registration = read_reference(reg_ref)
    _registration(registration, reg_ref)
    core.require(manifest == _manifest(registration, reg_ref, proof, manifest['project_freeze']),
                 'Project dataset differs from frozen publisher proof')
    core.require((role, model_sha256, context_tokens, vocab_size, bos_token_id) == tuple(
        registration[k] for k in ('role', 'model_sha256', 'context_tokens', 'vocab_size', 'bos_token_id')),
        'Project training identity differs from frozen registration')
    registry = _source_path(REGRESSION_ROOT / role)
    core.require(proof['registry_index']['path'] == str(registry / 'index.json'),
                 'Project freeze must use the single immutable role regression')
    index = read_reference(proof['registry_index'])
    core.require(index['schema_version'] == INDEX_SCHEMA and index['role'] == role
                 and index['fingerprint'] == expected_regression == manifest['regression']['fingerprint']
                 and registration['regression_fingerprint'] in (None, index['fingerprint'])
                 and index['similarity_parameters'] == SIMILARITY,
                 'Project immutable regression identity differs')
    # No evaluation input strings or target labels are parsed here.
    core.verify_file(registry / 'regression.json', index['regression_sha256'])
    member_file(root, manifest['regression'])
    core.require(manifest['regression']['sha256'] == index['regression_sha256'], 'Project regression bytes differ')
    for ref in index['provenance_files']:
        core.verify_file(_source_path(Path(ref['path'])), ref['sha256'])
    members = proof['members']; evaluation = [m for m in members if m['split'] != 'train']
    core.require(evaluation == index['members'], 'Project regression membership changed')
    train_members = [m for m in members if m['split'] == 'train']
    expected = members if registration['regression_fingerprint'] is None else train_members
    core.require(sorted(digest(m['review_reference']) for m in expected)
                 == sorted(digest(r) for r in registration['candidates']), 'Project registered review membership differs')
    actual = load_reviewed_candidates([m['review_reference'] for m in train_members])
    _check_rows(actual, registration)
    core.require([_member(r) for r in actual] == train_members and all(r['split'] == 'train' for r in actual),
                 'Project train members differ from original re-extraction')
    train_path = member_file(root, manifest['train'])
    core.require(train_path.read_bytes() == b''.join(_canonical_bytes(r) + b'\n' for r in actual),
                 'Project training bytes differ from independently re-extracted labels')
    counts, boundaries = _metadata_audit(members, registration['minimum_boundaries'])
    core.require(counts == manifest['counts'] and boundaries == proof['audit']['distinct_boundaries'],
                 'Project frozen coverage differs from source membership')
    functions = {'train': dict(Counter(_function(r) for r in actual)), **index['function_counts']}
    core.require(functions == proof['audit']['function_counts'] and all(
        f in functions[s] for s in SPLITS for f in registration['required_functions'][s]),
        'Project frozen function coverage differs from reviewed labels')
    core.require(proof['audit']['status'] == 'valid' and proof['audit']['quality_gates'] == {
        'verified_labels': True, 'family_isolation': True, 'distinct_boundaries': True,
        'function_coverage': True, 'cross_split_similarity': True}, 'Project frozen quality proof differs')
    vectors = dict(index['similarity_vectors'])
    vectors.update({r['sample_id']: _vector(r['input_text']) for r in actual})
    core.require(_similarity_audit(members, vectors) == proof['audit']['compared_pairs'],
                 'Project similarity proof differs')
    for ref in {digest(m['source_manifest']): m['source_manifest'] for m in members}.values():
        source = read_reference(ref)
        core.require(source.get('schema_version') == SOURCE_SCHEMA
                     and source['artifact_tree'] == tree_identity(_source_path(Path(source['source_root'])), exclude_git=False),
                     'Project frozen original source inventory changed')
        for name in ('collection_registration', 'source_registration'):
            original = source[name]
            core.verify_file(_source_path(Path(original['path'])), original['sha256'])
    normalized = [normalize_row(r, role=role, model_sha256=model_sha256, context_tokens=context_tokens,
        vocab_size=vocab_size, bos_token_id=bos_token_id) for r in actual]
    return manifest, normalized
