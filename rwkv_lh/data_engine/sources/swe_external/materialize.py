"""Prepare pinned repository tasks for the existing production admission loop.

Downloads and runtime package selection are separate, recorded input steps.
This module executes patches only in ActionHarness, keeps oracle/test material
outside model workspaces, and does not grant eligibility before real admission.
"""
import hashlib
from pathlib import Path

from rwkv_lh.data_engine.records import write_immutable
from rwkv_lh.data_engine.tasks import checksum, dump
from rwkv_lh.evaluation_policy import assert_training_source_allowed
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState, TaskAction
from rwkv_lh.workspace_snapshot import copy_verified_workspace, tree_identity
from . import SCHEMA, sha
from .pytest_verifier import pytest_acceptance


def prepare_pytest_task(candidate, *, seed, hidden_root, output, runtime):
    """Turn a source candidate into a frozen task, still awaiting admit().

    A declared local runtime reproduction is allowed; it is never represented
    as equivalence to an upstream container. The frozen original assertions
    must be reproduced and the reference must pass three times before rollout.
    """
    if candidate['schema_version'] != SCHEMA or candidate['language'] != 'python':
        raise ValueError('Python external task candidate required')
    if not candidate['decontamination']['passed']:
        raise ValueError('source exclusion checks must pass')
    if candidate.get('evaluation_only') or candidate.get('usage_policy') == 'evaluation_only_never_train':
        raise ValueError('evaluation-only candidate cannot be materialized for training')
    if runtime.get('kind') != 'local-reproduction' or not runtime.get('files'):
        raise ValueError('explicit frozen local runtime inventory required')
    seed, hidden_root, output = (Path(v).resolve() for v in (seed, hidden_root, output))
    for path in (seed, hidden_root, output):
        assert_training_source_allowed(path)
    for private in (hidden_root, output):
        if private == seed or private.is_relative_to(seed) or seed.is_relative_to(private):
            raise ValueError('private material must be outside the model seed tree')
    # Runtime inventory includes the Python executable and every vendored file.
    for name, digest in runtime['files'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('runtime inventory changed')
    patches = {}
    for field in ('gold_patch_sha256', 'test_patch_sha256'):
        path = hidden_root/candidate['hidden'][field]
        if path.is_symlink():
            raise ValueError('private patch must be a regular immutable object')
        patches[field] = path.read_text()
        if sha(patches[field]) != candidate['hidden'][field]:
            raise ValueError('private patch identity differs')
    output.mkdir(parents=True, exist_ok=False)
    before = tree_identity(seed, exclude_git=True)
    harness = ActionHarness()
    for name, field in [('reference', 'gold_patch_sha256'), ('hidden-tests', 'test_patch_sha256')]:
        workspace = output/name
        copy_verified_workspace(seed, workspace, audit_path=output/(name+'-copy.json'))
        goal = GoalState.create(request='Materialize a frozen upstream patch', constraints=[], workspace_root=workspace)
        receipt = harness.execute(TaskAction('run_shell', {'command': 'git apply --whitespace=nowarn -',
            'stdin': patches[field], 'timeout': 60}), goal)
        write_immutable(output/(name+'-patch.json'), dump(receipt.to_dict()).encode())
        if not receipt.success:
            raise ValueError('frozen patch does not apply: '+name)
    tested = output/'hidden-tests'
    after = tree_identity(tested)
    test_files, deleted = {}, []
    for name, entry in after.items():
        if entry != before.get(name) and entry['kind'] != 'directory':
            if entry['kind'] != 'file':
                raise ValueError('hidden test overlay requires regular files')
            test_files[name] = (tested/name).read_bytes()
    for name, entry in before.items():
        if name not in after and entry['kind'] != 'directory':
            deleted.append(name)
    if not test_files and not deleted:
        raise ValueError('hidden patch made no observable test change')
    args = {'test_files': test_files, 'deleted_files': deleted,
            'fail_to_pass': candidate['hidden']['fail_to_pass'],
            'pass_to_pass': candidate['hidden']['pass_to_pass']}
    def snapshot(path):
        return {'path': str(path), 'tree_sha256': checksum(tree_identity(path, exclude_git=True))}
    task = {'id': candidate['task_id'], 'family': candidate['repository'],
        'request': candidate['requests'][0]['text'], 'workflow': 'upstream_project_bugfix',
        'source': {'candidate': candidate, 'candidate_sha256': checksum(candidate),
                   'runtime': runtime, 'runtime_sha256': checksum(runtime),
                   'materialization': 'local-reproduction', 'upstream_container_parity': False},
        'workspace_snapshots': {'seed': snapshot(seed), 'reference': snapshot(output/'reference'),
                                'mutants': [snapshot(seed)]},
        'reference_repetitions': 3, 'seed_must_fail': True,
        'verification_timeout_seconds': 330,
        'acceptance': pytest_acceptance(**args), 'base_acceptance': pytest_acceptance(**args, base=True),
        'protected_paths': ['.project-deps'], 'max_calls': None, 'max_seconds': None}
    task['digest'] = checksum(task)
    write_immutable(output/'task.json', dump(task).encode())
    return task
