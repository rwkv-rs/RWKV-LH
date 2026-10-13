"""Exact cited workspace material, captured once at project creation.

The request names existing relative paths. This layer copies those bytes into
the original context; it does not interpret requirements or choose write scopes.
"""
import hashlib
from pathlib import Path
import re

from .project_contracts import digest, fields, relative_path
from .workspace_snapshot import tree_identity


def referenced_paths(request, workspace):
    """Match actual literal paths, including ./, without filename heuristics.

    A sentence-final period is punctuation; a following filename component is
    not. Slash boundaries prevent a nested reference from selecting a root file
    with the same basename. No extension, task or preferred filename is special.
    """
    if not isinstance(workspace, dict):
        raise ValueError('workspace inventory required for referenced material')
    return [path for path, record in sorted(workspace.items())
            if isinstance(record, dict) and record.get('kind') == 'file'
            and re.search(r'(?<![A-Za-z0-9_./\\+-])(?:\./)?' + re.escape(path)
                          + r'(?![A-Za-z0-9_/\\+-]|\.[A-Za-z0-9_./\\+-])', request)]


def validate_materials(request, workspace, materials):
    if not isinstance(materials, dict) or set(materials) != set(referenced_paths(request, workspace)):
        raise ValueError('referenced material set differs from the request and workspace')
    for path, record in materials.items():
        relative_path(path)
        fields(record, ('sha256', 'bytes', 'status', 'text'))
        checksum = record['sha256']
        if (not isinstance(checksum, str) or len(checksum) != 64
                or any(c not in '0123456789abcdef' for c in checksum)
                or checksum != workspace[path].get('sha256')
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
    for path in referenced_paths(request, before):
        relative_path(path)
        raw = (root / path).read_bytes()
        checksum = hashlib.sha256(raw).hexdigest()
        if checksum != before[path]['sha256']:
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
