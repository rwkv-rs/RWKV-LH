"""Current Native request identity contract, independent of model/role schemas.

The deployed journal binds each request ID to an operation and canonical body.
Preparing the same non-generation operation again preserves its identity;
generation must use the durable ID allocated by its ModelSession boundary.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

NATIVE_REQUEST_RECOVERY_VERSION = "rwkv-lh.native-request-recovery.v1"
NATIVE_REQUEST_OPERATIONS = frozenset({
    "create", "append", "fork", "generate", "commit", "rollback", "import", "release",
})
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}\Z")


def native_result_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def native_request_digest(operation: str, payload: Mapping[str, Any]) -> str:
    if operation not in NATIVE_REQUEST_OPERATIONS:
        raise ValueError("unsupported Native request operation")
    return native_result_digest({"operation": operation, "payload": dict(payload)})


def prepare_native_request(operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    if operation not in NATIVE_REQUEST_OPERATIONS:
        raise ValueError("unsupported Native request operation")
    prepared = dict(payload)
    version = prepared.setdefault("recovery_protocol", NATIVE_REQUEST_RECOVERY_VERSION)
    if version != NATIVE_REQUEST_RECOVERY_VERSION:
        raise ValueError("unsupported Native request recovery protocol")
    if "request_id" not in prepared:
        if operation == "generate":
            raise ValueError("Native generation requires its durable request ID")
        prepared["request_id"] = "NR-" + native_request_digest(operation, prepared)
    request_id = prepared["request_id"]
    if not isinstance(request_id, str) or not _REQUEST_ID.fullmatch(request_id):
        raise ValueError("invalid Native request ID")
    native_request_digest(operation, prepared)
    return prepared
