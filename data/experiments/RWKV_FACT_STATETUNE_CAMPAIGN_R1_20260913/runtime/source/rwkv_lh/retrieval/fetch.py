"""Bounded HTTP fetch with redirect-by-redirect SSRF validation."""

from __future__ import annotations

import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import urljoin, urlparse

import requests


class FetchPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class FetchResponse:
    url: str
    status_code: int
    media_type: str
    body: bytes
    headers: Mapping[str, str]


Resolver = Callable[[str], Iterable[str]]


def _system_resolver(host: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            item[4][0]
            for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        )
    )


def validate_public_url(url: str, *, resolver: Resolver = _system_resolver) -> str:
    selected = str(url or "").strip()
    parsed = urlparse(selected)
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise FetchPolicyError("retrieval URL must use http or https")
    if parsed.username or parsed.password or not parsed.hostname:
        raise FetchPolicyError("retrieval URL authority is invalid")
    if parsed.port not in {None, 80, 443}:
        raise FetchPolicyError("retrieval URL uses a disallowed port")
    try:
        addresses = tuple(resolver(parsed.hostname))
    except OSError as exc:
        raise FetchPolicyError(f"retrieval hostname resolution failed: {exc}") from exc
    if not addresses:
        raise FetchPolicyError("retrieval hostname has no addresses")
    for raw in addresses:
        address = ipaddress.ip_address(raw)
        if not address.is_global:
            raise FetchPolicyError("retrieval URL resolves to a non-public address")
    return selected


def validate_public_peer(response: Any) -> str:
    """Validate the connected peer, closing the DNS-check/connect TOCTOU gap."""
    raw = getattr(response, "raw", None)
    candidates = (
        getattr(getattr(raw, "_connection", None), "sock", None),
        getattr(getattr(raw, "connection", None), "sock", None),
        getattr(
            getattr(getattr(getattr(raw, "_fp", None), "fp", None), "raw", None),
            "_sock",
            None,
        ),
    )
    peer_socket = next((item for item in candidates if item is not None), None)
    if peer_socket is None:
        raise FetchPolicyError("retrieval peer address is unavailable")
    try:
        raw_address = str(peer_socket.getpeername()[0])
        address = ipaddress.ip_address(raw_address)
    except (AttributeError, IndexError, TypeError, ValueError, OSError) as exc:
        raise FetchPolicyError("retrieval peer address is invalid") from exc
    if not address.is_global:
        raise FetchPolicyError("retrieval connection reached a non-public address")
    return address.compressed


class PublicHttpFetcher:
    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        connect_timeout_seconds: float = 5.0,
        max_bytes: int = 4_000_000,
        max_redirects: int = 4,
        resolver: Resolver = _system_resolver,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout_seconds = max(1.0, min(float(timeout_seconds), 60.0))
        self.connect_timeout_seconds = max(
            1.0, min(float(connect_timeout_seconds), 60.0)
        )
        self.max_bytes = max(1024, min(int(max_bytes), 16_000_000))
        self.max_redirects = max(0, min(int(max_redirects), 8))
        self.resolver = resolver
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "User-Agent": "RWKV-LH-Retrieval/0.1 (+local evidence runtime)",
                "Accept": "text/html,application/json,text/plain,application/xml;q=0.8,*/*;q=0.2",
            }
        )

    def _consume(self, response: Any, *, current: str) -> FetchResponse:
        validate_public_peer(response)
        response.raise_for_status()
        media_type = str(
            response.headers.get("Content-Type") or "application/octet-stream"
        )
        chunks: list[bytes] = []
        observed = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            observed += len(chunk)
            if observed > self.max_bytes:
                raise FetchPolicyError("retrieved response exceeds the byte bound")
            chunks.append(bytes(chunk))
        return FetchResponse(
            url=str(response.url or current),
            status_code=int(response.status_code),
            media_type=media_type,
            body=b"".join(chunks),
            headers={str(key): str(value) for key, value in response.headers.items()},
        )

    def fetch(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> FetchResponse:
        current = validate_public_url(url, resolver=self.resolver)
        for redirect in range(self.max_redirects + 1):
            response = self.session.get(
                current,
                headers=dict(headers or {}),
                timeout=(self.connect_timeout_seconds, self.timeout_seconds),
                stream=True,
                allow_redirects=False,
            )
            try:
                validate_public_peer(response)
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = str(response.headers.get("Location") or "").strip()
                    if not location or redirect >= self.max_redirects:
                        raise FetchPolicyError("retrieval redirect bound exceeded")
                    current = validate_public_url(
                        urljoin(current, location), resolver=self.resolver
                    )
                    continue
                return self._consume(response, current=current)
            finally:
                response.close()
        raise FetchPolicyError("retrieval redirect loop")

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        *,
        headers: Mapping[str, str] | None = None,
    ) -> FetchResponse:
        """POST bounded JSON to one validated origin without forwarding secrets.

        API credentials must never be replayed across redirects, so provider
        POSTs reject redirects instead of following them.
        """

        current = validate_public_url(url, resolver=self.resolver)
        selected_headers = {
            "Content-Type": "application/json",
            **dict(headers or {}),
        }
        response = self.session.post(
            current,
            data=json.dumps(dict(payload), ensure_ascii=False).encode("utf-8"),
            headers=selected_headers,
            timeout=(self.connect_timeout_seconds, self.timeout_seconds),
            stream=True,
            allow_redirects=False,
        )
        try:
            validate_public_peer(response)
            if response.status_code in {301, 302, 303, 307, 308}:
                raise FetchPolicyError("retrieval API redirects are not allowed")
            return self._consume(response, current=current)
        finally:
            response.close()


__all__ = [
    "FetchPolicyError",
    "FetchResponse",
    "PublicHttpFetcher",
    "validate_public_peer",
    "validate_public_url",
]
