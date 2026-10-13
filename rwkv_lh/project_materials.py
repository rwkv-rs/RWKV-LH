"""Exact cited workspace material, captured once at project creation.

The request names existing relative paths. This layer copies those bytes into
the original context; it does not interpret requirements or choose write scopes.
"""
import hashlib
from pathlib import Path, PurePosixPath
import re

from .project_contracts import digest, fields, relative_path
from .workspace_snapshot import tree_identity, resolve_identity_path


def referenced_files(request, workspace):
    """Match actual literal paths, including ./, without filename heuristics.

    A sentence-final period is punctuation; a following filename component is
    not. Slash boundaries prevent a nested reference from selecting a root file
    with the same basename. No extension, task or preferred filename is special.
    """
    if not isinstance(workspace, dict):
        raise ValueError('workspace inventory required for referenced material')
    def mentioned(path, *, directory=False):
        suffix = '/' if directory else r'(?![A-Za-z0-9_/\\+-]|\.[A-Za-z0-9_./\\+-])'
        return re.search(r'(?<![A-Za-z0-9_./\\+-])(?:\./)?' + re.escape(path) + suffix, request)
    found = {path: record for path, record in sorted(workspace.items())
            if isinstance(record, dict) and record.get('kind') == 'file'
            and mentioned(path)}
    links = [path for path, record in workspace.items()
             if isinstance(record, dict) and record.get('kind') == 'symlink']
    if not links:
        return found
    children = {}
    for path in workspace:
        if path != '.':
            children.setdefault(str(PurePosixPath(path).parent), []).append(path)
    pending, visited = [(path, path) for path in links], set()
    while pending:
        visible, physical = pending.pop()
        if visible in visited:
            continue
        visited.add(visible)
        if not (mentioned(visible) or mentioned(visible, directory=True)):
            continue
        target = resolve_identity_path(workspace, physical)
        record = workspace[target]
        if record['kind'] == 'file' and mentioned(visible):
            found[visible] = record
        elif record['kind'] == 'directory' and mentioned(visible, directory=True):
            # Traverse only prefixes actually present in the request. Even a
            # directory link to an ancestor has finite cited paths; expanding
            # the whole alias tree could otherwise be infinite.
            pending.extend((visible + '/' + PurePosixPath(child).name, child)
                           for child in children.get(target, ()))
    return dict(sorted(found.items()))


def referenced_paths(request, workspace):
    return list(referenced_files(request, workspace))


def validate_materials(request, workspace, materials):
    files = referenced_files(request, workspace)
    if not isinstance(materials, dict) or set(materials) != set(files):
        raise ValueError('referenced material set differs from the request and workspace')
    for path, record in materials.items():
        relative_path(path)
        fields(record, ('sha256', 'bytes', 'status', 'text'))
        checksum = record['sha256']
        if (not isinstance(checksum, str) or len(checksum) != 64
                or any(c not in '0123456789abcdef' for c in checksum)
                or checksum != files[path].get('sha256')
                or type(record['bytes']) is not int or record['bytes'] < 0):
            raise ValueError('referenced material identity differs from workspace')
        if record['status'] == 'text' and isinstance(record['text'], str):
            raw = record['text'].encode('utf-8')
            if len(raw) != record['bytes'] or hashlib.sha256(raw).hexdigest() != checksum:
                raise ValueError('referenced material bytes or digest mismatch')
        elif record['status'] == 'non_utf8' and record['text'] is None and record['bytes'] > 0:
            # No replacement characters or guessed encoding. Its file identity
            # remains visible, but no textual understanding is claimed.
            pass
        else:
            raise ValueError('invalid referenced material content status')
    return materials


def capture_materials(root, request, *, expected_digest):
    """Capture complete cited bytes and detect observed concurrent changes.

    This shares the workspace snapshot identity policy; it is not a filesystem
    atomic snapshot against arbitrary external writers. Each text is bound to
    the expected file digest before being returned to the Planner builder.
    """
    root = Path(root).resolve(strict=True)
    before = tree_identity(root)
    if digest(before) != expected_digest:
        raise ValueError('workspace changed before initial planning material capture')
    materials = {}
    for path, entry in referenced_files(request, before).items():
        relative_path(path)
        raw = (root / path).read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        if checksum != entry['sha256']:
            raise ValueError('workspace changed while reading referenced material: ' + path)
        try:
            content, status = raw.decode('utf-8'), 'text'
        except UnicodeDecodeError:
            content, status = None, 'non_utf8'
        materials[path] = {'sha256': checksum, 'bytes': len(raw), 'status': status, 'text': content}
    if tree_identity(root) != before:
        raise ValueError('workspace changed during initial planning material capture')
    validate_materials(request, before, materials)
    return before, materials


def validate_initial_context(request, context):
    """The host retains the full initial inventory for completeness checks."""
    fields(context, ('workspace', 'materials'))
    validate_materials(request, context['workspace'], context['materials'])
    return context


def validate_bound_materials(request, materials, expected_digest):
    """Validate the compact role view against its stable assignment binding.

    The production builder checks completeness against the original inventory;
    the role payload carries cited files, not the entire repository inventory.
    Trace reconstruction verifies this view against the captured ledger context.
    """
    if not isinstance(materials, dict) or digest(materials) != expected_digest:
        raise ValueError('initial material digest differs from project assignment')
    if any(not isinstance(record, dict) for record in materials.values()):
        raise ValueError('invalid initial material record')
    inventory = {path: {'kind': 'file', 'sha256': record.get('sha256')}
                 for path, record in materials.items()}
    validate_materials(request, inventory, materials)
    return materials
