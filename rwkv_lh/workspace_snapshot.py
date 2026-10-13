"""Auditable workspace copies; no model input or business decisions.

Before/after identity checks detect observed concurrent changes. They do not
claim filesystem-level atomic snapshots against arbitrary external writers.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
from collections import deque


def resolve_identity_path(identity, path, *, allow_missing=False, traversed_links=None):
    """Resolve a POSIX path from recorded entries, without reading a live tree.

    Links must be relative and resolve inside this identity. Missing leaf paths
    may be used for write authority, but an existing link's target must exist.
    Expansion markers detect link-resolution cycles without recursing through
    directory aliases or imposing a limit on the number of project entries.
    """
    if not isinstance(path, str) or path.startswith('/') or '\0' in path:
        raise ValueError('workspace path must be relative')
    if identity.get('.', {}).get('kind') != 'directory':
        raise ValueError('workspace identity must contain its root directory')
    pending, resolved, active = deque(path.split('/')), [], set()
    while pending:
        part = pending.popleft()
        if isinstance(part, tuple):
            active.remove(part[0])
            continue
        parent = '/'.join(resolved) or '.'
        directory = identity.get(parent)
        if directory is not None and directory.get('kind') != 'directory':
            raise ValueError('workspace path parent is not a directory: ' + parent)
        if part in ('', '.'):
            continue
        if part == '..':
            if not resolved:
                raise ValueError('symlink escapes workspace: ' + path)
            resolved.pop()
            continue
        candidate = '/'.join([*resolved, part])
        entry = identity.get(candidate)
        if entry is None:
            if not allow_missing or active:
                raise ValueError('missing workspace link target or path: ' + candidate)
            resolved.append(part)
        elif entry.get('kind') == 'symlink':
            target = entry.get('target')
            if not isinstance(target, str) or not target or target.startswith('/') or '\0' in target:
                raise ValueError('symlink target must be relative: ' + candidate)
            if candidate in active:
                raise ValueError('cyclic workspace symlink: ' + candidate)
            if traversed_links is not None:
                traversed_links.add(candidate)
            active.add(candidate)
            pending.extendleft(reversed([*target.split('/'), (candidate,)]))
        elif entry.get('kind') in ('file', 'directory'):
            resolved.append(part)
        else:
            raise ValueError('source special file not supported: ' + candidate)
    return '/'.join(resolved) or '.'


def invalid_entries(identity):
    """Report unsafe entries in an untrusted staged inventory before publication."""
    errors = {}
    for path, record in identity.items():
        if record['kind'] == 'symlink':
            try:
                resolve_identity_path(identity, path)
            except ValueError as exc:
                errors[path] = str(exc)
        elif record['kind'] not in ('file', 'directory'):
            errors[path] = 'source special file not supported: ' + path
    return errors


def tree_identity(root, *, exclude_git=False, allow_links=False):
    """Record exact entries and validate portable links by default.

    allow_links=True also permits unsafe links and special nodes in the raw
    inventory, for callers that must record and reject staged changes together.
    It must not be used to authorize a workspace copy or publication.
    """
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('workspace must be a directory')
    entries = {}
    for path in [root, *sorted(root.rglob('*'))]:
        relative = path.relative_to(root)
        if exclude_git and '.git' in relative.parts:
            continue
        info = path.lstat()
        record = {'mode': stat.S_IMODE(info.st_mode)}
        if stat.S_ISLNK(info.st_mode):
            record.update(kind='symlink', target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            record['kind'] = 'directory'
        elif stat.S_ISREG(info.st_mode):
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            record.update(kind='file', sha256=digest.hexdigest())
            after = path.lstat()
            if (info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                    after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('source changed while hashing: ' + str(relative))
        else:
            if not allow_links:
                raise ValueError('source special file not supported: ' + str(relative))
            record.update(kind='special', file_type=stat.S_IFMT(info.st_mode))
        entries[str(relative)] = record
    if not allow_links:
        errors = invalid_entries(entries)
        if errors:
            raise ValueError('; '.join(errors.values()))
    return entries


def file_inventory(identity):
    return {path: (record['sha256'] if record['kind'] == 'file' else 'symlink:' + record['target'])
            for path, record in identity.items() if record['kind'] in ('file', 'symlink')}


def copy_verified_workspace(source, destination, *, audit_path=None, exclude_git=True):
    source, destination = Path(source).resolve(strict=True), Path(destination).resolve()
    if source == destination or source in destination.parents or destination in source.parents:
        raise ValueError('source and copy must not overlap')
    if destination.exists():
        raise FileExistsError(destination)
    before = tree_identity(source, exclude_git=exclude_git)
    record = {'source': str(source), 'destination': str(destination), 'before': before, 'verified': False}
    def save():
        if audit_path is not None:
            path = Path(audit_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    save()
    try:
        shutil.copytree(source, destination, symlinks=True,
                        ignore=shutil.ignore_patterns('.git') if exclude_git else None)
        record['after'] = tree_identity(source, exclude_git=exclude_git)
        record['copied'] = tree_identity(destination)
        if before != record['after'] or before != record['copied']:
            raise ValueError('source changed or workspace copy differs')
        record['verified'] = True
    except BaseException as exc:
        record['error_type'] = type(exc).__name__
        save()
        raise
    save()
    return before
