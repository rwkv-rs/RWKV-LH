"""Versioned, content-addressed contracts for external evidence.

Titles, URLs and provider labels route evidence; only exact spans or literal
structured fields are factual material.  These value objects intentionally do
not own task completion, planning or persistence semantics.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import canonical_digest


EXTERNAL_EVIDENCE_SCHEMA_VERSION = "rwkv-lh.external-evidence.v1"
EVIDENCE_RECORD_SCHEMA_VERSION = "rwkv-lh.evidence-record.v1"
EVIDENCE_SPAN_SCHEMA_VERSION = "rwkv-lh.evidence-span.v1"
SOURCE_OBJECT_SCHEMA_VERSION = "rwkv-lh.source-object.v1"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ExternalEvidenceRequestMismatch(ValueError):
    """An internally valid envelope belongs to a different tool request."""


def _text(name: str, value: Any, *, max_chars: int) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{name} must be non-empty")
    if len(result) > max_chars:
        raise ValueError(f"{name} exceeds {max_chars} characters")
    return result


def _literal_text(name: str, value: Any, *, max_chars: int) -> str:
    """Validate exact evidence text without normalizing its bytes."""

    result = "" if value is None else str(value)
    if not result.strip():
        raise ValueError(f"{name} must be non-empty")
    if len(result) > max_chars:
        raise ValueError(f"{name} exceeds {max_chars} characters")
    return result


def _mapping_items(name: str, value: Any) -> tuple[Mapping[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be an array of objects")
    if any(not isinstance(item, Mapping) for item in value):
        raise ValueError(f"{name} must contain only objects")
    return tuple(value)


def _sha256(name: str, value: Any) -> str:
    result = str(value or "").strip().casefold()
    if not _SHA256_RE.fullmatch(result):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return result


def external_evidence_request_digest(
    tool: str,
    arguments: Mapping[str, Any],
) -> str:
    operation = _text("evidence tool", tool, max_chars=128)
    return canonical_digest({"tool": operation, "arguments": dict(arguments)})


def validate_external_evidence_request(
    envelope: "ExternalEvidenceEnvelope",
    *,
    tool: str,
    arguments: Mapping[str, Any],
) -> "ExternalEvidenceEnvelope":
    """Bind one envelope to the exact currently selected tool invocation."""

    operation = _text("evidence tool", tool, max_chars=128)
    expected_digest = external_evidence_request_digest(operation, arguments)
    if envelope.tool != operation:
        raise ExternalEvidenceRequestMismatch(
            "external evidence tool does not match the selected operation"
        )
    if envelope.request_digest != expected_digest:
        raise ExternalEvidenceRequestMismatch(
            "external evidence request digest does not match current arguments"
        )
    return envelope


@dataclass(frozen=True)
class SourceObject:
    source_object_id: str
    source_object_type: str
    source_record_id: str = ""
    schema_version: str = SOURCE_OBJECT_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        source_object_id: str,
        source_object_type: str,
        source_record_id: str = "",
    ) -> "SourceObject":
        return cls(
            source_object_id=_text(
                "source_object_id", source_object_id, max_chars=4096
            ),
            source_object_type=_text(
                "source_object_type", source_object_type, max_chars=128
            ),
            source_record_id=str(source_record_id or "").strip()[:1024],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_object_id": self.source_object_id,
            "source_object_type": self.source_object_type,
            "source_record_id": self.source_record_id,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceObject":
        if str(value.get("schema_version") or SOURCE_OBJECT_SCHEMA_VERSION) != (
            SOURCE_OBJECT_SCHEMA_VERSION
        ):
            raise ValueError("unsupported source object schema")
        return cls.create(
            source_object_id=str(value.get("source_object_id") or ""),
            source_object_type=str(value.get("source_object_type") or ""),
            source_record_id=str(value.get("source_record_id") or ""),
        )


@dataclass(frozen=True)
class EvidenceSpan:
    span_id: str
    text: str
    locator: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = EVIDENCE_SPAN_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        text: str,
        locator: Mapping[str, Any] | None = None,
    ) -> "EvidenceSpan":
        literal = _literal_text("evidence span text", text, max_chars=16_000)
        locator_value = dict(locator or {})
        identity = {"text": literal, "locator": locator_value}
        return cls(
            span_id=f"SPAN-{canonical_digest(identity)[:20]}",
            text=literal,
            locator=locator_value,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "span_id": self.span_id,
            "text": self.text,
            "locator": dict(self.locator),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceSpan":
        if str(value.get("schema_version") or EVIDENCE_SPAN_SCHEMA_VERSION) != (
            EVIDENCE_SPAN_SCHEMA_VERSION
        ):
            raise ValueError("unsupported evidence span schema")
        locator_value = value.get("locator", {})
        if not isinstance(locator_value, Mapping):
            raise ValueError("evidence span locator must be an object")
        span = cls.create(
            text=value.get("text"),
            locator=locator_value,
        )
        supplied = str(value.get("span_id") or "")
        if supplied and supplied != span.span_id:
            raise ValueError("evidence span id does not match its content")
        return span


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_record_id: str
    source_object: SourceObject
    snapshot_digest: str
    exact_spans: tuple[EvidenceSpan, ...]
    url: str = ""
    title: str = ""
    published: str = ""
    retrieved_at: str = ""
    structured_fields: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = EVIDENCE_RECORD_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        source_object: SourceObject,
        snapshot_digest: str,
        exact_spans: Sequence[EvidenceSpan],
        url: str = "",
        title: str = "",
        published: str = "",
        retrieved_at: str = "",
        structured_fields: Mapping[str, Any] | None = None,
    ) -> "EvidenceRecord":
        spans = tuple(exact_spans)
        structured = dict(structured_fields or {})
        if not spans and not structured:
            raise ValueError(
                "evidence record requires exact spans or literal structured fields"
            )
        digest = _sha256("snapshot_digest", snapshot_digest)
        url_value = str(url or "").strip()[:4096]
        title_value = str(title or "").strip()[:1000]
        published_value = str(published or "").strip()[:128]
        retrieved_value = str(retrieved_at or "").strip()[:128]
        payload = {
            "source_object": source_object.to_dict(),
            "snapshot_digest": digest,
            "exact_spans": [item.to_dict() for item in spans],
            "structured_fields": structured,
            "url": url_value,
            "title": title_value,
            "published": published_value,
            "retrieved_at": retrieved_value,
        }
        return cls(
            evidence_record_id=f"E-{canonical_digest(payload)[:20]}",
            source_object=source_object,
            snapshot_digest=digest,
            exact_spans=spans,
            url=url_value,
            title=title_value,
            published=published_value,
            retrieved_at=retrieved_value,
            structured_fields=structured,
        )

    def verify_snapshot(self, snapshot_text: str) -> bool:
        snapshot = str(snapshot_text)
        return (
            hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
            == self.snapshot_digest
            and all(span.text in snapshot for span in self.exact_spans)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_record_id": self.evidence_record_id,
            "source_object": self.source_object.to_dict(),
            "snapshot_digest": self.snapshot_digest,
            "exact_spans": [item.to_dict() for item in self.exact_spans],
            "url": self.url,
            "title": self.title,
            "published": self.published,
            "retrieved_at": self.retrieved_at,
            "structured_fields": dict(self.structured_fields),
            "fact_authority": "exact_spans_or_structured_fields_only",
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRecord":
        if str(value.get("schema_version") or EVIDENCE_RECORD_SCHEMA_VERSION) != (
            EVIDENCE_RECORD_SCHEMA_VERSION
        ):
            raise ValueError("unsupported evidence record schema")
        source_value = value.get("source_object")
        if not isinstance(source_value, Mapping):
            raise ValueError("evidence record requires a source_object")
        span_values = _mapping_items("exact_spans", value.get("exact_spans"))
        structured_fields = value.get("structured_fields", {})
        if not isinstance(structured_fields, Mapping):
            raise ValueError("structured_fields must be an object")
        record = cls.create(
            source_object=SourceObject.from_dict(source_value),
            snapshot_digest=str(value.get("snapshot_digest") or ""),
            exact_spans=tuple(
                EvidenceSpan.from_dict(item)
                for item in span_values
            ),
            url=str(value.get("url") or ""),
            title=str(value.get("title") or ""),
            published=str(value.get("published") or ""),
            retrieved_at=str(value.get("retrieved_at") or ""),
            structured_fields=structured_fields,
        )
        supplied = str(value.get("evidence_record_id") or "")
        if supplied and supplied != record.evidence_record_id:
            raise ValueError("evidence record id does not match its content")
        return record


@dataclass(frozen=True)
class ExternalEvidenceEnvelope:
    route_id: str
    tool: str
    request_digest: str
    status: str
    records: tuple[EvidenceRecord, ...]
    as_of: str
    provider_attempts: tuple[Mapping[str, Any], ...] = ()
    truncated: bool = False
    action_id: str = ""
    schema_version: str = EXTERNAL_EVIDENCE_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        tool: str,
        request: Mapping[str, Any],
        status: str,
        records: Sequence[EvidenceRecord],
        as_of: str,
        provider_attempts: Sequence[Mapping[str, Any]] = (),
        truncated: bool = False,
        action_id: str = "",
    ) -> "ExternalEvidenceEnvelope":
        operation = _text("evidence tool", tool, max_chars=128)
        request_value = dict(request)
        request_digest = external_evidence_request_digest(operation, request_value)
        status_value = str(status or "").strip()
        if status_value not in {
            "evidence_committed",
            "no_evidence",
            "provider_unavailable",
        }:
            raise ValueError(f"unsupported external evidence status: {status_value}")
        record_values = tuple(records)
        if status_value == "evidence_committed" and not record_values:
            raise ValueError("evidence_committed requires at least one record")
        if status_value != "evidence_committed" and record_values:
            raise ValueError(f"{status_value} must not contain evidence records")
        route_payload = {
            "tool": operation,
            "request_digest": request_digest,
            "as_of": str(as_of or "").strip(),
        }
        return cls(
            route_id=f"ROUTE-{canonical_digest(route_payload)[:20]}",
            tool=operation,
            request_digest=request_digest,
            status=status_value,
            records=record_values,
            as_of=_text("as_of", as_of, max_chars=128),
            provider_attempts=tuple(dict(item) for item in provider_attempts),
            truncated=bool(truncated),
            action_id=str(action_id or "").strip(),
        )

    def bind_action(self, action_id: str) -> "ExternalEvidenceEnvelope":
        identifier = _text("action_id", action_id, max_chars=128)
        if self.action_id and self.action_id != identifier:
            raise ValueError("external evidence is already bound to another action")
        return ExternalEvidenceEnvelope(
            route_id=self.route_id,
            tool=self.tool,
            request_digest=self.request_digest,
            status=self.status,
            records=self.records,
            as_of=self.as_of,
            provider_attempts=self.provider_attempts,
            truncated=self.truncated,
            action_id=identifier,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "action_id": self.action_id,
            "route_id": self.route_id,
            "tool": self.tool,
            "request_digest": self.request_digest,
            "as_of": self.as_of,
            "status": self.status,
            "records": [item.to_dict() for item in self.records],
            "provider_attempts": [dict(item) for item in self.provider_attempts],
            "truncated": self.truncated,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExternalEvidenceEnvelope":
        if str(value.get("schema_version") or "") != EXTERNAL_EVIDENCE_SCHEMA_VERSION:
            raise ValueError("unsupported external evidence schema")
        record_values = _mapping_items("records", value.get("records"))
        attempt_values = _mapping_items(
            "provider_attempts", value.get("provider_attempts")
        )
        envelope = cls(
            route_id=_text("route_id", value.get("route_id"), max_chars=128),
            tool=_text("tool", value.get("tool"), max_chars=128),
            request_digest=_sha256(
                "request_digest", value.get("request_digest")
            ),
            status=str(value.get("status") or ""),
            records=tuple(
                EvidenceRecord.from_dict(item)
                for item in record_values
            ),
            as_of=_text("as_of", value.get("as_of"), max_chars=128),
            provider_attempts=tuple(
                dict(item)
                for item in attempt_values
            ),
            truncated=bool(value.get("truncated", False)),
            action_id=str(value.get("action_id") or "").strip(),
        )
        if envelope.status not in {
            "evidence_committed",
            "no_evidence",
            "provider_unavailable",
        }:
            raise ValueError("external evidence status is invalid")
        if envelope.status == "evidence_committed" and not envelope.records:
            raise ValueError("evidence_committed requires records")
        if envelope.status != "evidence_committed" and envelope.records:
            raise ValueError(
                f"{envelope.status} must not contain evidence records"
            )
        expected_route_id = (
            "ROUTE-"
            + canonical_digest(
                {
                    "tool": envelope.tool,
                    "request_digest": envelope.request_digest,
                    "as_of": envelope.as_of,
                }
            )[:20]
        )
        if envelope.route_id != expected_route_id:
            raise ValueError("route id does not match its content")
        if len(envelope.action_id) > 128:
            raise ValueError("action_id exceeds 128 characters")
        return envelope


__all__ = [
    "EVIDENCE_RECORD_SCHEMA_VERSION",
    "EVIDENCE_SPAN_SCHEMA_VERSION",
    "EXTERNAL_EVIDENCE_SCHEMA_VERSION",
    "SOURCE_OBJECT_SCHEMA_VERSION",
    "EvidenceRecord",
    "EvidenceSpan",
    "ExternalEvidenceEnvelope",
    "ExternalEvidenceRequestMismatch",
    "SourceObject",
    "external_evidence_request_digest",
    "validate_external_evidence_request",
]
