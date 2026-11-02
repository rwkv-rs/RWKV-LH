"""Extract SWE task definitions, never foreign trajectories or predicted patches.

This adapter does not introduce another harness. Extraction is not admission:
the base, oracle and repeated verifier runs must still execute in our sandbox.
"""
import hashlib
import json
import re
from pathlib import Path

from rwkv_lh.data_engine.contamination import repository
from rwkv_lh.data_engine.records import write_immutable
from rwkv_lh.data_engine.tasks import checksum

SCHEMA = 'rwkv-lh.external-swe-task.v1'
TASK_POOLS = frozenset({'nebius/SWE-rebench', 'SWE-Gym/SWE-Gym', 'R2E-Gym/R2E-Gym-Subset'})
LICENSES = {'MIT': 'MIT', 'MIT License': 'MIT', 'Apache-2.0': 'Apache-2.0',
            'Apache License 2.0': 'Apache-2.0', 'BSD-2-Clause': 'BSD-2-Clause',
            'BSD 2-Clause "Simplified" License': 'BSD-2-Clause',
            'BSD-3-Clause': 'BSD-3-Clause', 'BSD 3-Clause "New" or "Revised" License': 'BSD-3-Clause'}


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def string_list(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise ValueError('explicit test identifiers required')
    return value


def candidate_fields(row, source):
    """The decontamination view contains upstream task text and hidden hashes only."""
    return {'instance_id': row['instance_id'], 'repository': repository(row['repo']),
            'base_commit': row['base_commit'], 'text': row['problem_statement'],
            'gold_patch_sha256': sha(row.get('patch') or ''),
            'test_file_sha256': [sha(row['test_patch'])] if row.get('test_patch') else [],
            'created_at': row.get('created_at'), 'source_dataset': source['dataset']}


def extract_candidate(row, *, source, registry, hidden_root):
    """Whitelist task fields and store patches in a separate private CAS.

    Pool names are deliberately explicit: a benchmark split cannot enter by
    masquerading as an unrecognized source. The SWE-rebench corpus supports RL
    use despite its historical split names; its leaderboard is a distinct denied
    dataset, and the registry excludes leaderboard tasks and repositories.
    """
    if source['dataset'] not in TASK_POOLS:
        raise ValueError('unknown task pool or benchmark source')
    if not re.fullmatch('[0-9a-f]{40}', source['revision']):
        raise ValueError('pinned dataset revision required')
    if source.get('license') not in ('cc-by-4.0', 'mit', 'apache-2.0'):
        raise ValueError('unreviewed dataset license')
    fields = candidate_fields(row, source)
    if not re.fullmatch(r'[a-z0-9_.-]+/[a-z0-9_.-]+', fields['repository']):
        raise ValueError('invalid upstream repository')
    if not re.fullmatch('[0-9a-f]{40}', fields['base_commit']):
        raise ValueError('pinned repository commit required')
    license_id = LICENSES.get(row.get('license_name') or row.get('license'))
    if not license_id:
        raise ValueError('unreviewed repository license')
    for name in ('instance_id', 'problem_statement', 'patch', 'test_patch'):
        if not isinstance(row.get(name), str) or not row[name].strip():
            raise ValueError('missing upstream task field: ' + name)
    fail_to_pass = string_list(row['FAIL_TO_PASS'])
    pass_to_pass = string_list(row['PASS_TO_PASS'])
    if not fail_to_pass:
        raise ValueError('nonempty fail-to-pass tests required')
    decontamination = registry.check(fields)
    if not decontamination['passed']:
        raise ValueError('decontamination excluded candidate: ' + json.dumps(decontamination['hits']))
    recipe = {key: row[key] for key in ('install_config', 'requirements', 'environment', 'environment_setup_commit') if key in row}
    private = Path(hidden_root)
    if private.is_symlink():
        raise ValueError('private store cannot be a symlink')
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    private.chmod(0o700)
    for name in ('patch', 'test_patch'):
        path = private / sha(row[name])
        if path.is_symlink():
            raise ValueError('private object cannot be a symlink')
        write_immutable(path, row[name].encode())
        path.chmod(0o600)
    identity = checksum({'dataset': source['dataset'], 'revision': source['revision'], 'instance': fields['instance_id']})
    return {'schema_version': SCHEMA, 'task_id': 'swe-' + identity[:24],
            'source': {key: source[key] for key in ('dataset', 'revision', 'license', 'url', 'split') if key in source}
                      | {'instance_id': fields['instance_id'], 'created_at': fields['created_at'], 'repository_license': license_id},
            'repository': fields['repository'], 'base_commit': fields['base_commit'],
            'language': row.get('language', 'unverified'),
            'environment': {'kind': 'unmaterialized', 'image': row.get('docker_image') or row.get('image_name'),
                            'image_digest': None, 'setup_recipe_sha256': checksum(recipe),
                            'workspace_archive_sha256': None},
            'issue_text_sha256': sha(fields['text']),
            'hidden': {'gold_patch_sha256': sha(row['patch']), 'test_patch_sha256': sha(row['test_patch']),
                       'fail_to_pass': fail_to_pass, 'pass_to_pass': pass_to_pass,
                       'verifier_command': None, 'verifier_sha256': None},
            'admission': {'oracle_passed': False, 'base_failed': False, 'materialization_faithful': False, 'runs': []},
            'decontamination': decontamination,
            'labels': {'workflow_category': 'bugfix', 'family': fields['repository'], 'difficulty': 'unmeasured'},
            'requests': [{'text': fields['text'], 'origin': 'upstream_issue'}],
            'training_eligible': False}


def public_request(task):
    """The only task-author/teacher view; private checks and references are absent."""
    return {'repository': task['repository'], 'request': task['requests'][0]['text']}
