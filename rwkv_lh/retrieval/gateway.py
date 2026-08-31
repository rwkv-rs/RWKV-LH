"""Live ECRA-derived retrieval transaction for already-selected RWKV actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from rwkv_lh.retrieval.chunk import chunk_text
from rwkv_lh.retrieval.clean import clean_document
from rwkv_lh.retrieval.contracts import (
    EvidenceRecord,
    EvidenceSpan,
    ExternalEvidenceEnvelope,
    SourceObject,
    external_evidence_request_digest,
    validate_external_evidence_request,
)
from rwkv_lh.retrieval.providers import (
    ConnectorProvider,
    LocalWebProvider,
    PublicConnectorProvider,
    RetrievedSource,
    WebProvider,
    WebSearchResult,
)
from rwkv_lh.retrieval.snapshot import SnapshotStore


class LiveRetrievalBackend:
    """Fetch, freeze, clean, chunk and expose candidates; never plan or finish."""

    provider_name = "rwkv-lh-ecra-kernel.v1"

    def __init__(
        self,
        snapshot_store: SnapshotStore,
        *,
        web_provider: WebProvider | None = None,
        connector_provider: ConnectorProvider | None = None,
        clock: Callable[[], datetime] | None = None,
        max_records: int = 12,
    ) -> None:
        self.snapshot_store = snapshot_store
        self.web_provider = web_provider or LocalWebProvider()
        self.connector_provider = connector_provider or PublicConnectorProvider()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.max_records = max(1, min(int(max_records), 32))

    @property
    def connector_operations(self) -> tuple[str, ...]:
        return tuple(self.connector_provider.supported_operations)

    @property
    def _route_root(self) -> Path:
        return self.snapshot_store.root / "routes"

    def _cached(self, tool: str, arguments: Mapping[str, Any]) -> ExternalEvidenceEnvelope | None:
        request_digest = external_evidence_request_digest(tool, arguments)
        path = self._route_root / request_digest[:2] / f"{request_digest}.json"
        if not path.exists():
            return None
        envelope = ExternalEvidenceEnvelope.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        return validate_external_evidence_request(
            envelope,
            tool=tool,
            arguments=arguments,
        )

    def recover(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope | None:
        """Return only an already committed route; never call a provider."""
        return self._cached(str(tool or "").strip(), dict(arguments))

    def _commit_route(self, envelope: ExternalEvidenceEnvelope) -> None:
        path = self._route_root / envelope.request_digest[:2] / f"{envelope.request_digest}.json"
        payload = json.dumps(
            envelope.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.snapshot_store.write_immutable(path, payload)

    def _records(
        self,
        sources: Sequence[RetrievedSource],
        *,
        retrieved_at: str,
    ) -> tuple[EvidenceRecord, ...]:
        records: list[EvidenceRecord] = []
        committed_span_count = 0
        for source in sources:
            clean, extracted_title = clean_document(source.raw, source.media_type)
            if not clean:
                continue
            snapshot = self.snapshot_store.commit(
                url=source.url,
                media_type=source.media_type,
                raw=source.raw,
                clean_text=clean,
                retrieved_at=retrieved_at,
                title=source.title or extracted_title,
                published=source.published,
            )
            remaining = self.max_records - committed_span_count
            if remaining <= 0:
                break
            chunks = chunk_text(clean, max_chunks=min(4, remaining))
            spans = tuple(
                EvidenceSpan.create(
                    text=chunk.text,
                    locator={
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "chunk_index": chunk.index,
                        "snapshot_digest": snapshot.snapshot_digest,
                    },
                )
                for chunk in chunks
            )
            if not spans and not source.structured_fields:
                continue
            # One record is one immutable source object. Chunking produces
            # multiple exact spans inside that record; emitting one record per
            # chunk duplicated URLs, source IDs and structured fields in every
            # Executor input without adding evidence.
            records.append(
                EvidenceRecord.create(
                    source_object=SourceObject.create(
                        source_object_id=(
                            f"{source.source_type}:{snapshot.snapshot_digest[:24]}"
                        ),
                        source_object_type=source.source_type,
                        source_record_id=snapshot.raw_digest,
                    ),
                    snapshot_digest=snapshot.snapshot_digest,
                    exact_spans=spans,
                    url=snapshot.url,
                    title=snapshot.title,
                    published=snapshot.published,
                    retrieved_at=snapshot.retrieved_at,
                    structured_fields=dict(source.structured_fields),
                )
            )
            committed_span_count += len(spans)
            if committed_span_count >= self.max_records:
                break
        return tuple(records)

    def execute(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope:
        selected_tool = str(tool or "").strip()
        request = dict(arguments)
        cached = self._cached(selected_tool, request)
        if cached is not None:
            return cached
        observed = self.clock()
        if observed.tzinfo is None:
            raise ValueError("retrieval clock must return an aware datetime")
        as_of = observed.astimezone(timezone.utc).isoformat(timespec="seconds")
        attempts: list[dict[str, Any]] = []
        try:
            if selected_tool == "web_search":
                provider = str(self.web_provider.provider_name)
                search_result = self.web_provider.search(
                    str(request.get("query") or ""),
                    int(request.get("max_results", 5) or 5),
                )
                if isinstance(search_result, WebSearchResult):
                    sources = search_result.sources
                    attempts.extend(
                        dict(item) for item in search_result.provider_attempts
                    )
                else:
                    sources = search_result
            elif selected_tool == "connector_lookup":
                provider = str(self.connector_provider.provider_name)
                sources = self.connector_provider.lookup(
                    str(request.get("operation") or ""),
                    str(request.get("query") or ""),
                )
            else:
                raise ValueError(f"unsupported retrieval tool: {selected_tool}")
            if not attempts:
                attempts.append({"provider": provider, "status": "ok"})
        except Exception as exc:
            captured = getattr(exc, "provider_attempts", ())
            attempts.extend(dict(item) for item in captured)
            if not captured:
                attempts.append(
                    {
                        "provider": locals().get("provider", self.provider_name),
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
            envelope = ExternalEvidenceEnvelope.create(
                tool=selected_tool,
                request=request,
                status="provider_unavailable",
                records=(),
                as_of=as_of,
                provider_attempts=attempts,
            )
            self._commit_route(envelope)
            return envelope
        records = self._records(tuple(sources), retrieved_at=as_of)
        envelope = ExternalEvidenceEnvelope.create(
            tool=selected_tool,
            request=request,
            status=("evidence_committed" if records else "no_evidence"),
            records=records,
            as_of=as_of,
            provider_attempts=attempts,
            truncated=(
                sum(len(record.exact_spans) for record in records)
                >= self.max_records
            ),
        )
        self._commit_route(envelope)
        return envelope


def build_live_retrieval_backend(snapshot_root: Path) -> LiveRetrievalBackend:
    from rwkv_lh.runtime.settings import load_local_env

    load_local_env()
    return LiveRetrievalBackend(SnapshotStore(snapshot_root))


__all__ = ["LiveRetrievalBackend", "build_live_retrieval_backend"]
