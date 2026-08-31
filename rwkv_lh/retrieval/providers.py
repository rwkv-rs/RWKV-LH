"""Provider adapters extracted as a retrieval kernel, without agent semantics."""

from __future__ import annotations

import json
import hashlib
import os
import re
import threading
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse
from xml.etree import ElementTree

import requests

from rwkv_lh.retrieval.fetch import (
    FetchPolicyError,
    FetchResponse,
    PublicHttpFetcher,
    validate_public_url,
)


@dataclass(frozen=True)
class RetrievedSource:
    url: str
    raw: bytes
    media_type: str
    source_type: str
    title: str = ""
    published: str = ""
    structured_fields: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WebSearchResult(Sequence[RetrievedSource]):
    sources: tuple[RetrievedSource, ...]
    provider_attempts: tuple[Mapping[str, Any], ...] = ()

    def __getitem__(self, index: int | slice) -> RetrievedSource | tuple[RetrievedSource, ...]:
        return self.sources[index]

    def __len__(self) -> int:
        return len(self.sources)


class ProviderSearchError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        provider_attempts: Sequence[Mapping[str, Any]] = (),
    ) -> None:
        super().__init__(message)
        self.provider_attempts = tuple(dict(item) for item in provider_attempts)


class WebProvider(Protocol):
    provider_name: str

    def search(self, query: str, max_results: int) -> WebSearchResult: ...


class ConnectorProvider(Protocol):
    provider_name: str
    supported_operations: Sequence[str]

    def lookup(self, operation: str, query: str) -> Sequence[RetrievedSource]: ...


class _SearchLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href = ""
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        attributes = dict(attrs)
        classes = str(attributes.get("class") or "")
        if "result__a" in classes or "result-link" in classes:
            self._href = str(attributes.get("href") or "")
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(str(data or ""))

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "a" and self._href:
            self.links.append((self._href, " ".join("".join(self._parts).split())))
            self._href = ""
            self._parts = []


def _public_result_url(value: str) -> str:
    selected = str(value or "").strip()
    parsed = urlparse(selected)
    if parsed.netloc.casefold().endswith("duckduckgo.com"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            selected = unquote(target)
    return selected


class KeylessWebProvider:
    """Exact URL fetch plus bounded keyless discovery; it never plans queries.

    The discovery path is deliberately multi-source.  The original deployment
    depended only on DuckDuckGo HTML, which is unreachable in the target local
    network.  Bing RSS is the local primary and the original DuckDuckGo HTML
    parser remains a bounded fallback.  Both receive the exact model query.
    """

    provider_name = "keyless-public-web-multi-source-v1"

    def __init__(self, fetcher: PublicHttpFetcher | None = None) -> None:
        self.fetcher = fetcher or PublicHttpFetcher()

    @staticmethod
    def _explicit_url(query: str) -> str:
        match = re.search(r"https?://[^\s<>\]\[()]+", str(query or ""))
        return match.group(0).rstrip(".,;:!?，。；：！？") if match else ""

    @staticmethod
    def _source(
        response: FetchResponse,
        *,
        title: str = "",
        structured_fields: Mapping[str, Any] | None = None,
    ) -> RetrievedSource:
        return RetrievedSource(
            url=response.url,
            raw=response.body,
            media_type=response.media_type,
            source_type="public_web_page",
            title=title,
            structured_fields=dict(structured_fields or {}),
        )

    @staticmethod
    def _bing_rss_links(payload: bytes) -> list[tuple[str, str]]:
        root = ElementTree.fromstring(payload)
        links: list[tuple[str, str]] = []
        for item in root.findall(".//item"):
            url = str(item.findtext("link") or "").strip()
            title = " ".join(str(item.findtext("title") or "").split())
            if url:
                links.append((url, title))
        return links

    def _discover(
        self, query: str
    ) -> tuple[str, list[tuple[str, str]], tuple[Mapping[str, Any], ...]]:
        attempts = (
            (
                "bing-rss",
                "https://cn.bing.com/search?"
                + urlencode({"q": query, "format": "rss"}),
                lambda response: self._bing_rss_links(response.body),
            ),
            (
                "duckduckgo-html",
                "https://html.duckduckgo.com/html/?" + urlencode({"q": query}),
                self._duckduckgo_links,
            ),
        )
        failures: list[str] = []
        provider_attempts: list[dict[str, Any]] = []
        for provider, url, parse_links in attempts:
            try:
                response = self.fetcher.fetch(url)
                links = list(parse_links(response))
            except Exception as exc:
                failures.append(f"{provider}:{type(exc).__name__}:{str(exc)[:200]}")
                provider_attempts.append(
                    {
                        "provider": provider,
                        "status": "error",
                        "error_type": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
                continue
            if links:
                provider_attempts.append({"provider": provider, "status": "ok"})
                return provider, links, tuple(provider_attempts)
            failures.append(f"{provider}:no_results")
            provider_attempts.append({"provider": provider, "status": "no_results"})
        raise ProviderSearchError(
            "public web discovery failed: " + "; ".join(failures),
            provider_attempts=provider_attempts,
        )

    @staticmethod
    def _duckduckgo_links(response: FetchResponse) -> list[tuple[str, str]]:
        parser = _SearchLinks()
        parser.feed(response.body.decode("utf-8", errors="replace"))
        return parser.links

    def search(self, query: str, max_results: int) -> WebSearchResult:
        selected_query = str(query or "").strip()
        if not selected_query:
            raise ValueError("web search query must be non-empty")
        limit = max(1, min(int(max_results), 10))
        direct = self._explicit_url(selected_query)
        if direct:
            return WebSearchResult(
                sources=(
                    self._source(
                        self.fetcher.fetch(direct),
                        structured_fields={"discovery_provider": "direct_url"},
                    ),
                ),
                provider_attempts=({"provider": "direct_url", "status": "ok"},),
            )
        discovery_provider, links, provider_attempts = self._discover(selected_query)
        sources: list[RetrievedSource] = []
        seen: set[str] = set()
        for rank, (href, title) in enumerate(links, start=1):
            url = _public_result_url(href)
            if not url or url in seen:
                continue
            seen.add(url)
            try:
                sources.append(
                    self._source(
                        self.fetcher.fetch(url),
                        title=title,
                        structured_fields={
                            "discovery_provider": discovery_provider,
                            "discovery_rank": rank,
                        },
                    )
                )
            except Exception:
                continue
            if len(sources) >= limit:
                break
        return WebSearchResult(
            sources=tuple(sources),
            provider_attempts=provider_attempts,
        )


def _configured_tavily_keys() -> tuple[str, ...]:
    values = [os.environ.get("TAVILY_API_KEY", "")]
    values.extend(re.split(r"[,;\s]+", os.environ.get("TAVILY_API_KEYS", "")))
    return tuple(
        dict.fromkeys(value.strip() for value in values if value.strip())
    )


def _credential_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class TavilyWebProvider:
    """Prefer direct pages, with explicitly marked Tavily extraction on timeout."""

    provider_name = "tavily-search-api"
    _TRANSIENT_PAGE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
    _MAX_EXTRACTED_PAGE_BYTES = 1_000_000

    def __init__(
        self,
        fetcher: PublicHttpFetcher | None = None,
        *,
        api_keys: Sequence[str] | None = None,
        url_validator: Callable[[str], str] = validate_public_url,
    ) -> None:
        self.fetcher = fetcher or PublicHttpFetcher()
        self._api_keys = tuple(api_keys) if api_keys is not None else None
        self._url_validator = url_validator
        self._disabled_credentials: set[str] = set()
        self._health_lock = threading.Lock()

    def _keys(self) -> tuple[str, ...]:
        values = self._api_keys if self._api_keys is not None else _configured_tavily_keys()
        with self._health_lock:
            return tuple(
                value
                for value in values
                if _credential_id(value) not in self._disabled_credentials
            )

    @staticmethod
    def _status_code(exc: Exception) -> int | None:
        response = getattr(exc, "response", None)
        try:
            return int(getattr(response, "status_code", 0)) or None
        except (TypeError, ValueError):
            return None

    def _disable(self, key: str) -> None:
        with self._health_lock:
            self._disabled_credentials.add(_credential_id(key))

    @staticmethod
    def _canonical_directory_retry(url: str) -> str:
        """Return one narrow slash variant for extensionless discovered pages.

        Some HTTP servers emit an empty 301/302 response and urllib3 releases
        its socket before the connected-peer check can inspect it.  We never
        weaken that SSRF check.  For a Tavily-discovered, extensionless path we
        may instead request the conventional trailing-slash URL as a fresh,
        independently DNS- and peer-validated request.
        """

        parsed = urlparse(url)
        segment = parsed.path.rsplit("/", 1)[-1]
        if (
            parsed.scheme in {"http", "https"}
            and parsed.path
            and not parsed.path.endswith("/")
            and segment
            and "." not in segment
            and not parsed.query
            and not parsed.fragment
        ):
            return url + "/"
        return ""

    @classmethod
    def _is_transient_page_error(cls, exc: Exception) -> bool:
        """Select only transport failures that are safe to repeat once.

        Fetch policy failures are security or resource-bound decisions, not
        availability failures, and must never enter the generic retry path.
        """

        if isinstance(exc, FetchPolicyError):
            return False
        status_code = cls._status_code(exc)
        if status_code is not None:
            return status_code in cls._TRANSIENT_PAGE_STATUS_CODES
        return isinstance(
            exc,
            (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
                TimeoutError,
                ConnectionError,
            ),
        )

    @classmethod
    def _safe_page_failure(
        cls,
        *,
        url: str,
        rank: int,
        attempt: str,
        exc: Exception,
    ) -> dict[str, Any]:
        """Create a correlatable failure record without retaining URL secrets."""

        parsed = urlparse(url)
        status_code = cls._status_code(exc)
        value: dict[str, Any] = {
            "discovery_rank": rank,
            "attempt": attempt,
            "scheme": parsed.scheme.casefold()[:16],
            "host": str(parsed.hostname or "")[:253],
            "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "error_type": type(exc).__name__,
            "status_code": status_code,
        }
        if isinstance(exc, FetchPolicyError):
            value["category"] = "fetch_policy"
            value["policy_reason"] = str(exc)[:240]
        elif status_code is not None:
            value["category"] = (
                "transient_http"
                if status_code in cls._TRANSIENT_PAGE_STATUS_CODES
                else "http"
            )
        elif isinstance(
            exc, (requests.exceptions.Timeout, TimeoutError)
        ):
            value["category"] = "transport_timeout"
        elif isinstance(
            exc, (requests.exceptions.ConnectionError, ConnectionError)
        ):
            value["category"] = "transport_connection"
        else:
            value["category"] = "page_fetch"
        return value

    def search(self, query: str, max_results: int) -> WebSearchResult:
        selected_query = str(query or "").strip()
        if not selected_query:
            raise ValueError("web search query must be non-empty")
        keys = self._keys()
        if not keys:
            return WebSearchResult(
                sources=(),
                provider_attempts=(
                    {
                        "provider": self.provider_name,
                        "status": "disabled",
                        "error_type": "provider_not_configured",
                    },
                ),
            )
        limit = max(1, min(int(max_results), 10))
        credential_attempts: list[dict[str, Any]] = []
        payload: Mapping[str, Any] | None = None
        response_body = b""
        successful_credential_id = ""
        for key in keys:
            identity = _credential_id(key)
            try:
                response = self.fetcher.post_json(
                    "https://api.tavily.com/search",
                    {
                        "query": selected_query,
                        "search_depth": "basic",
                        "max_results": limit,
                        "include_answer": False,
                        "include_raw_content": "markdown",
                        "include_images": False,
                        "topic": "general",
                    },
                    headers={"Authorization": f"Bearer {key}"},
                )
                response_body = response.body
                value = json.loads(response_body.decode("utf-8"))
                if not isinstance(value, Mapping):
                    raise ValueError("Tavily response must be a JSON object")
                payload = value
                successful_credential_id = identity
                credential_attempts.append(
                    {
                        "status": "ok",
                        "credential_id": identity,
                    }
                )
                break
            except Exception as exc:
                status_code = self._status_code(exc)
                credential_attempts.append(
                    {
                        "status": "error",
                        "credential_id": identity,
                        "status_code": status_code,
                        "error_type": type(exc).__name__,
                        "message": str(exc)[:500],
                    }
                )
                if status_code in {401, 402, 403, 432}:
                    self._disable(key)
                    continue
                if status_code == 429:
                    continue
                break
        if payload is None:
            return WebSearchResult(
                sources=(),
                provider_attempts=(
                    {
                        "provider": self.provider_name,
                        "status": "error",
                        "credential_attempt_count": len(credential_attempts),
                        "credential_attempts": credential_attempts,
                    },
                ),
            )

        sources: list[RetrievedSource] = []
        fetch_failures = 0
        canonical_directory_retries = 0
        page_transport_retries = 0
        direct_page_commits = 0
        provider_extracted_page_commits = 0
        provider_extracted_page_rejections = 0
        host_circuit_open_skips = 0
        host_circuit_validation_failures = 0
        transient_unavailable_hosts: set[str] = set()
        page_fetch_attempt_failures: list[dict[str, Any]] = []
        response_sha256 = hashlib.sha256(response_body).hexdigest()
        request_id = str(payload.get("request_id") or "")[:128]
        for rank, item in enumerate(payload.get("results") or [], start=1):
            if not isinstance(item, Mapping):
                continue
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            page: FetchResponse | None = None
            extracted_content_eligible = False
            direct_page_attempted = True
            host = str(urlparse(url).hostname or "").casefold()
            if host and host in transient_unavailable_hosts:
                direct_page_attempted = False
                try:
                    self._url_validator(url)
                except Exception as exc:
                    host_circuit_validation_failures += 1
                    page_fetch_attempt_failures.append(
                        self._safe_page_failure(
                            url=url,
                            rank=rank,
                            attempt="host_circuit_public_url_validation",
                            exc=exc,
                        )
                    )
                else:
                    host_circuit_open_skips += 1
                    extracted_content_eligible = True
            else:
                try:
                    page = self.fetcher.fetch(url)
                except FetchPolicyError as exc:
                    page_fetch_attempt_failures.append(
                        self._safe_page_failure(
                            url=url,
                            rank=rank,
                            attempt="initial",
                            exc=exc,
                        )
                    )
                    retry_url = (
                        self._canonical_directory_retry(url)
                        if str(exc) == "retrieval peer address is unavailable"
                        else ""
                    )
                    try:
                        if retry_url:
                            page = self.fetcher.fetch(retry_url)
                            canonical_directory_retries += 1
                    except Exception as retry_exc:
                        page_fetch_attempt_failures.append(
                            self._safe_page_failure(
                                url=retry_url,
                                rank=rank,
                                attempt="canonical_directory_retry",
                                exc=retry_exc,
                            )
                        )
                except Exception as exc:
                    page_fetch_attempt_failures.append(
                        self._safe_page_failure(
                            url=url,
                            rank=rank,
                            attempt="initial",
                            exc=exc,
                        )
                    )
                    if self._is_transient_page_error(exc):
                        page_transport_retries += 1
                        try:
                            page = self.fetcher.fetch(url)
                        except Exception as retry_exc:
                            page_fetch_attempt_failures.append(
                                self._safe_page_failure(
                                    url=url,
                                    rank=rank,
                                    attempt="transport_retry",
                                    exc=retry_exc,
                                )
                            )
                            extracted_content_eligible = self._is_transient_page_error(
                                retry_exc
                            )
                            if extracted_content_eligible and host:
                                transient_unavailable_hosts.add(host)
            if page is not None:
                direct_page_commits += 1
                sources.append(
                    KeylessWebProvider._source(
                        page,
                        title=str(item.get("title") or ""),
                        structured_fields={
                            "discovery_provider": self.provider_name,
                            "discovery_rank": rank,
                            "discovery_score": item.get("score"),
                            "discovery_url": url,
                            "evidence_transport": "direct_public_http",
                            "provider_response_sha256": response_sha256,
                            "provider_request_id": request_id,
                        },
                    )
                )
            else:
                if direct_page_attempted:
                    fetch_failures += 1
                raw_content = item.get("raw_content")
                encoded = (
                    raw_content.encode("utf-8")
                    if isinstance(raw_content, str) and raw_content.strip()
                    else b""
                )
                if extracted_content_eligible and (
                    0 < len(encoded) <= self._MAX_EXTRACTED_PAGE_BYTES
                ):
                    provider_extracted_page_commits += 1
                    sources.append(
                        RetrievedSource(
                            url=url,
                            raw=encoded,
                            media_type="text/markdown; charset=utf-8",
                            source_type="tavily_extracted_public_web_page",
                            title=str(item.get("title") or ""),
                            published=str(item.get("published_date") or ""),
                            structured_fields={
                                "discovery_provider": self.provider_name,
                                "discovery_rank": rank,
                                "discovery_score": item.get("score"),
                                "discovery_url": url,
                                "evidence_transport": "tavily_extracted_markdown",
                                "extracted_content_sha256": hashlib.sha256(
                                    encoded
                                ).hexdigest(),
                                "provider_response_sha256": response_sha256,
                                "provider_request_id": request_id,
                            },
                        )
                    )
                elif extracted_content_eligible:
                    provider_extracted_page_rejections += 1
            if len(sources) >= limit:
                break
        provider_attempt = {
            "provider": self.provider_name,
            "status": "ok",
            "credential_id": successful_credential_id,
            "credential_attempt_count": len(credential_attempts),
            "credential_attempts": credential_attempts,
            "response_sha256": response_sha256,
            "request_id": request_id,
            "discovered_result_count": len(payload.get("results") or []),
            "committed_page_count": len(sources),
            "direct_page_commit_count": direct_page_commits,
            "provider_extracted_page_commit_count": provider_extracted_page_commits,
            "provider_extracted_page_rejection_count": provider_extracted_page_rejections,
            "host_circuit_open_host_count": len(transient_unavailable_hosts),
            "host_circuit_open_skip_count": host_circuit_open_skips,
            "host_circuit_validation_failure_count": host_circuit_validation_failures,
            "page_fetch_failure_count": fetch_failures,
            "page_fetch_attempt_failure_count": len(page_fetch_attempt_failures),
            "page_fetch_attempt_failures": page_fetch_attempt_failures,
            "page_transport_retry_count": page_transport_retries,
            "canonical_directory_retry_count": canonical_directory_retries,
        }
        return WebSearchResult(
            sources=tuple(sources),
            provider_attempts=(provider_attempt,),
        )


class LocalWebProvider:
    """Project-owned provider order: direct URL, Tavily, Bing RSS, DDG."""

    provider_name = "local-web-tavily-bing-ddg-v1"

    def __init__(
        self,
        fetcher: PublicHttpFetcher | None = None,
        *,
        tavily: TavilyWebProvider | None = None,
        keyless: KeylessWebProvider | None = None,
    ) -> None:
        shared = fetcher or PublicHttpFetcher()
        self.tavily = tavily or TavilyWebProvider(shared)
        self.keyless = keyless or KeylessWebProvider(shared)

    def search(self, query: str, max_results: int) -> WebSearchResult:
        selected_query = str(query or "").strip()
        if KeylessWebProvider._explicit_url(selected_query):
            return self.keyless.search(selected_query, max_results)
        tavily = self.tavily.search(selected_query, max_results)
        if tavily.sources:
            return tavily
        attempts = list(tavily.provider_attempts)
        try:
            keyless = self.keyless.search(selected_query, max_results)
        except ProviderSearchError as exc:
            attempts.extend(exc.provider_attempts)
            raise ProviderSearchError(
                "all local web discovery providers failed",
                provider_attempts=attempts,
            ) from exc
        return WebSearchResult(
            sources=keyless.sources,
            provider_attempts=tuple(attempts) + keyless.provider_attempts,
        )


def _json_source(response: FetchResponse, source_type: str) -> RetrievedSource:
    parsed = json.loads(response.body.decode("utf-8"))
    canonical = json.dumps(parsed, ensure_ascii=False, sort_keys=True).encode("utf-8")

    def bounded(value: Any, *, depth: int = 0) -> Any:
        if depth >= 3:
            return None
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:2000]
        if isinstance(value, Mapping):
            priority = (
                "full_name",
                "default_branch",
                "html_url",
                "tag_name",
                "published_at",
                "sha",
                "name",
                "version",
                "info",
                "message",
                "current",
                "current_units",
                "timezone",
                "latitude",
                "longitude",
                "DOI",
                "title",
                "published",
                "author",
                "url",
            )
            keys = [key for key in priority if key in value]
            keys.extend(key for key in value if key not in keys)
            return {
                str(key)[:200]: projected
                for key in keys[:32]
                if (item := value[key]) is not None
                if (projected := bounded(item, depth=depth + 1)) is not None
            }
        if isinstance(value, list):
            return [
                projected
                for item in value[:8]
                if (projected := bounded(item, depth=depth + 1)) is not None
            ]
        return str(value)[:500]

    structured = bounded(parsed)
    return RetrievedSource(
        url=response.url,
        raw=canonical,
        media_type="application/json",
        source_type=source_type,
        structured_fields=(
            structured if isinstance(structured, Mapping) else {"value": structured}
        ),
    )


class PublicConnectorProvider:
    """Typed public lookups that are actually configured in this local runtime."""

    provider_name = "public-structured-connectors"
    supported_operations = (
        "github_repository",
        "github_release",
        "github_commit",
        "package_release",
        "scholarly_record",
        "weather",
    )

    def __init__(self, fetcher: PublicHttpFetcher | None = None) -> None:
        self.fetcher = fetcher or PublicHttpFetcher()

    @staticmethod
    def _github_repository(query: str) -> str:
        text = str(query or "").strip()
        match = re.search(r"(?:github\.com/)?([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", text)
        if not match:
            raise ValueError("GitHub lookup requires owner/repository")
        return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"

    @staticmethod
    def _package(query: str) -> str:
        text = " ".join(str(query or "").split()).strip()
        parsed = urlparse(text)
        if parsed.netloc.casefold().endswith("pypi.org"):
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2:
                return parts[1]
        match = re.search(r"(?:PyPI\s+)?([A-Za-z0-9_.-]+)$", text, re.IGNORECASE)
        if not match:
            raise ValueError("package lookup requires one exact package identifier")
        return match.group(1)

    def lookup(self, operation: str, query: str) -> Sequence[RetrievedSource]:
        selected = str(operation or "").strip()
        if selected in {"github_repository", "github_release", "github_commit"}:
            repository = self._github_repository(query)
            suffix = ""
            if selected == "github_release":
                suffix = "/releases/latest"
            elif selected == "github_commit":
                suffix = "/commits/HEAD"
            response = self.fetcher.fetch(
                f"https://api.github.com/repos/{repository}{suffix}",
                headers={"Accept": "application/vnd.github+json"},
            )
            return (_json_source(response, selected),)
        if selected == "github_code":
            raise ValueError("github_code requires an authenticated connector not configured")
        if selected == "package_release":
            package = self._package(query)
            response = self.fetcher.fetch(
                f"https://pypi.org/pypi/{quote(package, safe='')}/json"
            )
            return (_json_source(response, "pypi_release"),)
        if selected == "scholarly_record":
            response = self.fetcher.fetch(
                "https://api.crossref.org/works?"
                + urlencode({"query.bibliographic": str(query), "rows": 5})
            )
            return (_json_source(response, "crossref_works"),)
        if selected in {"weather", "weather_alerts"}:
            geocode = self.fetcher.fetch(
                "https://geocoding-api.open-meteo.com/v1/search?"
                + urlencode({"name": str(query), "count": 1, "language": "en"})
            )
            geocode_value = json.loads(geocode.body.decode("utf-8"))
            rows = geocode_value.get("results") if isinstance(geocode_value, Mapping) else []
            row = rows[0] if isinstance(rows, list) and rows else None
            if not isinstance(row, Mapping):
                return ()
            if selected == "weather_alerts":
                raise ValueError("weather_alerts provider is not configured for this region")
            response = self.fetcher.fetch(
                "https://api.open-meteo.com/v1/forecast?"
                + urlencode(
                    {
                        "latitude": row["latitude"],
                        "longitude": row["longitude"],
                        "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
                        "timezone": "auto",
                    }
                )
            )
            return (_json_source(response, "weather_observation"),)
        raise ValueError(f"unsupported connector operation: {selected}")


__all__ = [
    "ConnectorProvider",
    "KeylessWebProvider",
    "LocalWebProvider",
    "ProviderSearchError",
    "PublicConnectorProvider",
    "RetrievedSource",
    "TavilyWebProvider",
    "WebProvider",
    "WebSearchResult",
]
