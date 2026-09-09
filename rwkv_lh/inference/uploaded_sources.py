"""One complete uploaded-source verification rule for CLI and Native processes."""
from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path, PurePosixPath
from typing import Any

ENGINE_SCHEMA = "rwkv-lh.uploaded-engine-source-manifest.v1"
PROJECT_SCHEMA = "rwkv-lh.uploaded-project-source-manifest.v1"
EXCLUDED_DIRECTORIES = frozenset({".git", ".venv", "__pycache__"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION = re.compile(r"^[0-9a-f]{40}$")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def source_inventory(root: Path) -> dict[str, tuple[str, int]]:
    files, pending = {}, [root]
    while pending:
        for child in pending.pop().iterdir():
            info = child.lstat()
            if stat.S_ISDIR(info.st_mode):
                if child.name not in EXCLUDED_DIRECTORIES:
                    pending.append(child)
            elif stat.S_ISREG(info.st_mode):
                files[child.relative_to(root).as_posix()] = (digest(child), info.st_size)
            else:
                raise RuntimeError("uploaded engine source tree contains a symlink or special file")
    return files


def verify_manifest(
    path: Path,
    expected_sha256: str,
    *,
    expected_schema: str | None = None,
    expected_root: Path | None = None,
    expected_revision: str | None = None,
    required_files: tuple[Path, ...] = (),
) -> dict[str, Any]:
    path = Path(path).resolve()
    label = "local engine source" if expected_schema == ENGINE_SCHEMA else "uploaded source"
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        raise RuntimeError(f"{label} manifest checksum is invalid")
    if not path.is_file() or digest(path) != expected_sha256:
        raise RuntimeError(f"{label} manifest checksum mismatch")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} manifest fields mismatch")  # noqa: TRY004
    schema = value.get("schema_version")
    root_key = {ENGINE_SCHEMA: "engine_root", PROJECT_SCHEMA: "project_root"}.get(schema)
    fields = {"schema_version", "source_root", "files", root_key}
    if schema == ENGINE_SCHEMA:
        fields.add("engine_revision")
    if root_key is None or set(value) != fields:
        raise RuntimeError(f"{label} manifest fields mismatch")
    if not isinstance(value[root_key], str):
        raise RuntimeError(f"{label} manifest root is invalid")  # noqa: TRY004
    root = Path(value[root_key])
    if (
        (expected_schema is not None and schema != expected_schema)
        or value["source_root"] != "."
        or not root.is_absolute() or not root.is_dir() or root.is_symlink()
        or (expected_root is not None and root != expected_root)
        or (schema == ENGINE_SCHEMA and (
            not isinstance(value["engine_revision"], str)
            or not _REVISION.fullmatch(value["engine_revision"])
            or (expected_revision is not None and value["engine_revision"] != expected_revision)
        ))
        or not isinstance(value["files"], list) or not value["files"]
    ):
        raise RuntimeError(f"{label} manifest identity mismatch")
    if path.is_relative_to(root.resolve()):
        raise RuntimeError(f"{label} manifest must be outside its absolute source root")
    expected = {}
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "bytes"}:
            raise RuntimeError(f"{label} manifest file fields mismatch")
        name, checksum, size = item["path"], item["sha256"], item["bytes"]
        if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
            raise RuntimeError(f"{label} manifest file path is invalid")
        relative = PurePosixPath(name)
        if (
            relative.is_absolute() or relative.as_posix() != name or name == "."
            or ".." in relative.parts or name in expected
            or any(part in EXCLUDED_DIRECTORIES for part in relative.parts[:-1])
            or not isinstance(checksum, str) or not _SHA256.fullmatch(checksum)
            or type(size) is not int or size < 0
        ):
            raise RuntimeError(f"{label} manifest file identity is invalid")
        expected[name] = (checksum, size)
    actual = source_inventory(root)
    if actual.keys() != expected.keys():
        raise RuntimeError(f"{label} file set differs from uploaded manifest")
    if actual != expected:
        raise RuntimeError(f"{label} file checksum or size mismatch")
    for loaded in required_files:
        resolved = Path(loaded).resolve()
        if not resolved.is_relative_to(root.resolve()) or resolved.relative_to(root.resolve()).as_posix() not in actual:
            raise RuntimeError(f"{label} loaded module is outside verified source files")
    return {"manifest_sha256": expected_sha256, "file_count": len(actual), "root": str(root)}
