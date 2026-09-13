"""Fail-closed Native identity from actual uploaded engine and project contents."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rwkv_lh.inference.uploaded_sources import (
    ENGINE_SCHEMA,
    PROJECT_SCHEMA,
    verify_manifest,
)
from rwkv_lh.model_io import canonical_digest


def verify_native_source_identity(
    *, engine_file: str | Path | None, project_file: str | Path | None = None,
) -> dict[str, Any]:
    configuration = {}
    for scope in ("ENGINE", "PROJECT"):
        for suffix in ("MANIFEST", "MANIFEST_SHA256"):
            key = f"RWKV_NATIVE_{scope}_SOURCE_{suffix}"
            value = os.environ.get(key)
            if not value:
                raise RuntimeError(f"Native source configuration requires {key}")
            configuration[key] = value
    if engine_file is None:
        raise RuntimeError("Native source verification requires the loaded engine module path")
    identities = {}
    for scope, schema, loaded in (
        ("ENGINE", ENGINE_SCHEMA, Path(engine_file)),
        ("PROJECT", PROJECT_SCHEMA, Path(project_file) if project_file is not None else Path(__file__)),
    ):
        verified = verify_manifest(
            Path(configuration[f"RWKV_NATIVE_{scope}_SOURCE_MANIFEST"]),
            configuration[f"RWKV_NATIVE_{scope}_SOURCE_MANIFEST_SHA256"],
            expected_schema=schema, required_files=(loaded,),
        )
        identities[f"{scope.lower()}_manifest_sha256"] = verified["manifest_sha256"]
    identity = {"schema_version": "rwkv-lh.native-source-identity.v1", **identities}
    return {**identity, "identity_sha256": canonical_digest(identity)}
