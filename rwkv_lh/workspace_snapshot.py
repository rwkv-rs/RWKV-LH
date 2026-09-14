"""Auditable workspace copies; no model input or business decisions.

Before/after identity checks detect observed concurrent changes. They do not
claim filesystem-level atomic snapshots against arbitrary external writers.
"""
import hashlib
import json
from pathlib import Path
import shutil
import stat


def tree_identity(root, *, exclude_git=False, allow_links=False):
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
            if not allow_links:
                raise ValueError('source symlink not supported: ' + str(relative))
            record.update(kind='symlink', target=str(path.readlink()))
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
