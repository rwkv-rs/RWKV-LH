"""Immutable, testable Project workspace sources for genuine production trace collection.

This does not grant training eligibility. It only prevents the collector from
silently omitting the repo's Python entrypoint package or copying private data.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import tempfile

_SOURCE_PACKAGES = ('rwkv_lh', 'scripts')
_OPTIONAL_SOURCE_PACKAGES = ('tests',)
_REQUIRED_FILES = ('pyproject.toml', 'uv.lock', 'docs/ARCHITECTURE.zh-CN.md',
                   'rwkv_lh/__init__.py', 'scripts/__init__.py')
_OPTIONAL_FILES = ('AGENTS.md', 'docs/HANDOFF.zh-CN.md',
                   'docs/PROJECT_ROLE_DATA_PIPELINE.zh-CN.md')
_EXCLUDED_DIRS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_files(root: Path) -> list[Path]:
    for name in _REQUIRED_FILES:
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Project source requires regular {name}')
    if (root / 'docs').is_symlink() or not (root / 'docs').is_dir():
        raise ValueError('Project source requires regular directory docs')
    files = [root / name for name in _REQUIRED_FILES if not name.startswith(_SOURCE_PACKAGES)]
    for name in _OPTIONAL_FILES:
        path = root / name
        if path.is_symlink() or path.exists():
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'Project source requires regular {name}')
            files.append(path)
    optional = []
    for dirname in _OPTIONAL_SOURCE_PACKAGES:
        parent = root / dirname
        if parent.is_symlink() or parent.exists():
            if parent.is_symlink() or not parent.is_dir():
                raise ValueError(f'Project source requires regular directory {dirname}')
            configuration = parent / 'conftest.py'
            if configuration.is_symlink() or not configuration.is_file():
                raise ValueError(f'Project source requires regular {dirname}/conftest.py')
            optional.append(dirname)
    for dirname in (*_SOURCE_PACKAGES, *optional):
        parent = root / dirname
        if parent.is_symlink() or not parent.is_dir():
            raise ValueError(f'Project source requires regular directory {dirname}')
        for path in sorted(parent.rglob('*')):
            if any(part in _EXCLUDED_DIRS for part in path.relative_to(parent).parts):
                continue
            if path.is_symlink():
                raise ValueError(f'Project source contains symbolic link: {path.relative_to(root)}')
            if path.name.startswith('.env') or path.name.endswith('.key'):
                raise ValueError(f'Project source includes private file: {path.relative_to(root)}')
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f'Project source contains non-file entry: {path.relative_to(root)}')
            if path.suffix in {'.pyc', '.so'}:
                continue
            files.append(path)
    return sorted(set(files))


def snapshot_project_source(root: str | Path, output: str | Path) -> dict[str, str]:
    """Publish an exact source snapshot or nothing; never traverse data/ or benchmarks/.

    Public checkouts contain runtime sources. Include local regression sources
    and maintenance instructions when installed, without requiring them publicly.

    Caller separately seals the returned mapping, origin request and model
    identity. The copied workspace is still *unreviewed* training provenance.
    """
    root = Path(root).resolve(strict=True)
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if output == root or any(output == root / name or root / name in output.parents
                             for name in (*_SOURCE_PACKAGES, *_OPTIONAL_SOURCE_PACKAGES)):
        raise ValueError('snapshot must not be inside a copied source package')
    files = _source_files(root)
    before = {str(path.relative_to(root)): _hash(path) for path in files}
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f'.{output.name}.source-', dir=output.parent))
    try:
        for name, expected in before.items():
            source = root / name
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target, follow_symlinks=False)
            if _hash(source) != expected or _hash(target) != expected:
                raise ValueError(f'Project source changed during snapshot: {name}')
        os.rename(stage, output)
        return before
    finally:
        if stage.exists():
            shutil.rmtree(stage)
