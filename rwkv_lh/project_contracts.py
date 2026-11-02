"""Structural contract helpers shared by the ledger, runtime and agent protocol."""
import hashlib
import json
from pathlib import PurePosixPath


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
