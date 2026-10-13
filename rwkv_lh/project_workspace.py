"""Workspace write authority and isolated, atomic publication on Linux."""
import ctypes
import os
from pathlib import Path, PurePosixPath

from .project_contracts import relative_path
from .workspace_snapshot import resolve_identity_path


def contains(root, path):
    root, path = PurePosixPath(root), PurePosixPath(path)
    return path == root or root in path.parents


def violations(paths, *, scope, protected, before=None, after=None):
    # Protect both the named alias and its recorded target. Write scopes remain
    # literal: creating or retargeting a link never grants new physical paths.
    named_protected = tuple(protected)
    protected, protected_links = set(protected), set()
    for identity in (before, after):
        if identity is not None:
            for path in named_protected:
                try:
                    protected.add(resolve_identity_path(identity, path, allow_missing=True,
                                                        traversed_links=protected_links))
                except ValueError:
                    # Invalid staged links are independently rejected before
                    # publication; their literal protected paths still apply.
                    pass
    rejected = []
    for path in paths:
        relative_path(path)
        protected_overlap = (any(contains(root, path) or contains(path, root) for root in protected)
                             or any(contains(path, link) for link in protected_links))
        allowed = any(contains(root, path) for root in scope)
        # Creating a parent directory is necessary to create an authorized child.
        parent_created = (before is not None and path not in before and after is not None
                          and after.get(path, {}).get('kind') == 'directory'
                          and any(contains(path, root) for root in scope))
        if protected_overlap or not (allowed or parent_created):
            rejected.append(path)
    return sorted(rejected)


def explicit_write_targets(harness, action, *, identity=None):
    """Concrete file APIs are preauthorized; commands are confined to staging."""
    name, args = action.action_type, action.arguments
    if name in ('run_shell', 'check_command') or not harness.definition(name).side_effect:
        return []
    if name == 'copy_file':
        targets = [args['destination']]
    elif name == 'move_file':
        targets = [args['source'], args['destination']]
    elif 'path' in args:
        targets = [args['path']]
    else:
        raise ValueError('write operation has no declared path authority')
    normalized = []
    for target in targets:
        target = harness._normalize_path_literal(target)
        relative_path(target)
        normalized.append(str(PurePosixPath(target)))
        if identity is not None:
            normalized.append(resolve_identity_path(identity, target, allow_missing=True))
    return list(dict.fromkeys(normalized))


def publish_workspace(workspace, staged):
    """Exchange directory names atomically; old contents remain in staged.

    No copy-in-place fallback: a partial publication must never be reported as
    a committed workspace. An interruption after exchange leaves ledger intent
    pending, so recovery cannot silently replay the action.
    """
    workspace, staged = Path(workspace), Path(staged)
    if workspace.stat().st_dev != staged.stat().st_dev:
        raise ValueError('workspace publication requires the same filesystem')
    libc = ctypes.CDLL(None, use_errno=True)
    exchange = libc.renameat2
    exchange.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    exchange.restype = ctypes.c_int
    if exchange(-100, os.fsencode(workspace), -100, os.fsencode(staged), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
