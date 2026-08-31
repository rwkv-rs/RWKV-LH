"""Content-addressed immutable raw and clean retrieval snapshots."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Mapping


SNAPSHOT_SCHEMA_VERSION = "rwkv-lh.source-snapshot.v1"


@dataclass(frozen=True)
class SourceSnapshot:
    snapshot_digest: str
    raw_digest: str
    url: str
    media_type: str
    retrieved_at: str
    title: str
    published: str
    clean_chars: int
    raw_bytes: int
    schema_version: str = SNAPSHOT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "snapshot_digest": self.snapshot_digest,
            "raw_digest": self.raw_digest,
            "url": self.url,
            "media_type": self.media_type,
            "retrieved_at": self.retrieved_at,
            "title": self.title,
            "published": self.published,
            "clean_chars": self.clean_chars,
            "raw_bytes": self.raw_bytes,
        }


class SnapshotStore:
    """Persist blobs once; manifests are projections of immutable content."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()

    @staticmethod
    def write_immutable(path: Path, payload: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise ValueError("content-addressed snapshot collision")
            return
        with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def commit(
        self,
        *,
        url: str,
        media_type: str,
        raw: bytes,
        clean_text: str,
        retrieved_at: str,
        title: str = "",
        published: str = "",
    ) -> SourceSnapshot:
        clean = str(clean_text)
        clean_bytes = clean.encode("utf-8")
        digest = hashlib.sha256(clean_bytes).hexdigest()
        raw_digest = hashlib.sha256(raw).hexdigest()
        snapshot = SourceSnapshot(
            snapshot_digest=digest,
            raw_digest=raw_digest,
            url=str(url),
            media_type=str(media_type),
            retrieved_at=str(retrieved_at),
            title=str(title)[:1000],
            published=str(published)[:128],
            clean_chars=len(clean),
            raw_bytes=len(raw),
        )
        directory = self.root / digest[:2] / digest
        self.write_immutable(directory / "clean.txt", clean_bytes)
        self.write_immutable(directory / "raw" / f"{raw_digest}.bin", bytes(raw))
        manifest = json.dumps(
            snapshot.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        manifest_digest = hashlib.sha256(manifest).hexdigest()
        self.write_immutable(
            directory / "manifests" / f"{manifest_digest}.json", manifest
        )
        return snapshot

    def read_clean(self, digest: str) -> str:
        selected = str(digest or "").strip().casefold()
        if len(selected) != 64 or any(char not in "0123456789abcdef" for char in selected):
            raise ValueError("invalid snapshot digest")
        return (self.root / selected[:2] / selected / "clean.txt").read_text(
            encoding="utf-8"
        )


__all__ = ["SNAPSHOT_SCHEMA_VERSION", "SnapshotStore", "SourceSnapshot"]
