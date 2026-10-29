"""Validated project contracts. Models own semantics; this module owns structure."""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath

ASSIGNMENT_PROTOCOL = 'rwkv-lh.coder.assignment.v2'
GOAL_PROTOCOL = 'rwkv-lh.coder.user-goal.v1'
GOAL_ID = 'original-goal'
WORKSPACE_PATH_SCHEMA = {
    'type': 'string', 'minLength': 1,
    'description': (
        "Literal workspace-relative file or directory path. 'path' and './path' denote "
        "the same path; '.' and './' denote the workspace root. Absolute paths, '..' "
        "components, backslashes and NUL are forbidden. No globs or inferred targets."),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError(f'contract fields must be {sorted(required)}')


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('nonempty text required')
    return value


def strings(value, *, empty=True):
    if not isinstance(value, list) or (not empty and not value):
        raise ValueError('text array required')
    for item in value:
        text(item)
    if len(set(value)) != len(value):
        raise ValueError('duplicate identifiers')
    return value


def resource_budget(value=None):
    """A shared resource fact; absent standalone-fixture budgets remain unknown."""
    import math
    if value is None:
        return {'calls': None, 'seconds': None}
    fields(value, ('calls', 'seconds'))
    calls, seconds = value['calls'], value['seconds']
    if calls is not None and (type(calls) is not int or calls < 0):
        raise ValueError('remaining calls must be nonnegative or unknown')
    if seconds is not None and (type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0):
        raise ValueError('remaining seconds must be finite nonnegative or unknown')
    return deepcopy(value)


def relative_path(value):
    text(value)
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value or '\x00' in value:
        raise ValueError('workspace-relative path required')
    return value


def scope_path(value, *, field=None):
    """Validate literal write authority with the workspace's relative-path rules.

    Preserve the model/owner spelling in the contract. Permission checks compare
    POSIX paths, so equivalent safe spellings cannot change or broaden authority.
    """
    try:
        relative_path(value)
    except ValueError as exc:
        if field is not None:
            raise ValueError(f'{field}: invalid path {value!r}: {exc}') from exc
        raise
    return value


def make_goal(request, protected_paths=()):
    return {'protocol': GOAL_PROTOCOL, 'id': GOAL_ID, 'request': text(request),
            'scope': ['.'], 'protected_paths': list(protected_paths)}


def validate_goal(goal):
    fields(goal, ('protocol', 'id', 'request', 'scope', 'protected_paths'))
    if goal['protocol'] != GOAL_PROTOCOL or goal['id'] != GOAL_ID:
        raise ValueError('unsupported user goal contract')
    text(goal['request'])
    for key in ('scope', 'protected_paths'):
        strings(goal[key], empty=key == 'protected_paths')
        for path in goal[key]:
            scope_path(path)
    return goal


def protected_paths(state):
    return list(state['goal']['protected_paths'])


def make_assignment(goal, *, assignment_id, workspace_digest, materials_digest):
    """One stable project identity, unchanged across work orders."""
    validate_goal(goal)
    return {'protocol': ASSIGNMENT_PROTOCOL, 'id': text(assignment_id),
            'goal_digest': digest(goal), 'workspace_digest': workspace_digest,
            'materials_digest': materials_digest, 'protected_paths': list(goal['protected_paths'])}
