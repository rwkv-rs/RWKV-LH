from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from rwkv_lh.retrieval.chunk import chunk_text
from rwkv_lh.retrieval.clean import clean_document
from rwkv_lh.retrieval.fetch import (
    FetchPolicyError,
    PublicHttpFetcher,
    validate_public_peer,
    validate_public_url,
)
from rwkv_lh.retrieval.gateway import LiveRetrievalBackend
from rwkv_lh.retrieval.contracts import (
    ExternalEvidenceRequestMismatch,
    external_evidence_request_digest,
)
from rwkv_lh.retrieval.policy import EgressProvenance, NetworkPolicy, NetworkPolicyMode
from rwkv_lh.retrieval.fetch import FetchResponse
from rwkv_lh.retrieval.providers import (
    KeylessWebProvider,
    LocalWebProvider,
    PublicConnectorProvider,
    RetrievedSource,
    TavilyWebProvider,
    WebSearchResult,
)
from rwkv_lh.retrieval.runtime import (
    RetrievalRuntimeConfig,
    WorkspaceProvenanceResolver,
    build_product_harness,
    network_policy_from_goal,
    operation_allowed_by_retrieval_policy,
    runtime_policy_document,
)
from rwkv_lh.retrieval.snapshot import SnapshotStore
from rwkv_lh.schema import GoalState, TaskAction


class FakeWebProvider:
    provider_name = "fake-web"

    def __init__(self) -> None:
        self.calls = 0

    def search(self, query: str, max_results: int):
        self.calls += 1
        assert query == "current release"
        assert max_results == 3
        return (
            RetrievedSource(
                url="https://example.test/release",
                raw=(
                    b"<html><head><title>Release</title><script>bad()</script></head>"
                    b"<body><h1>Current release</h1><p>Version 4.2 is current.</p></body></html>"
                ),
                media_type="text/html; charset=utf-8",
                source_type="public_web_page",
            ),
        )


class FakeConnectorProvider:
    provider_name = "fake-connector"

    def lookup(self, operation: str, query: str):
        return ()


class RoutedFetcher:
    def __init__(self, routes):
        self.routes = list(routes)
        self.urls: list[str] = []

    def fetch(self, url: str, *, headers=None):
        self.urls.append(url)
        expected, response = self.routes.pop(0)
        assert expected in url
        if isinstance(response, Exception):
            raise response
        return response


def fetch_response(url: str, body: bytes, media_type: str = "text/html"):
    return FetchResponse(
        url=url,
        status_code=200,
        media_type=media_type,
        body=body,
        headers={},
    )


def test_keyless_web_provider_uses_bing_rss_without_rewriting_query() -> None:
    query = "Python Packaging User Guide pyproject.toml"
    rss = b"""<?xml version="1.0"?><rss><channel>
    <item><title>Packaging</title><link>https://packaging.example/guide</link></item>
    </channel></rss>"""
    fetcher = RoutedFetcher(
        [
            ("cn.bing.com/search", fetch_response("https://cn.bing.com/search", rss, "text/xml")),
            (
                "https://packaging.example/guide",
                fetch_response(
                    "https://packaging.example/guide",
                    b"<html><body>pyproject.toml guide</body></html>",
                ),
            ),
        ]
    )

    sources = KeylessWebProvider(fetcher=fetcher).search(query, 3)

    assert len(sources) == 1
    assert "q=Python+Packaging+User+Guide+pyproject.toml" in fetcher.urls[0]
    assert sources[0].structured_fields == {
        "discovery_provider": "bing-rss",
        "discovery_rank": 1,
    }


def test_keyless_web_provider_falls_back_with_the_same_query() -> None:
    query = "RWKV paper"
    duckduckgo = (
        b'<a class="result__a" href="https://papers.example/rwkv">RWKV</a>'
    )
    fetcher = RoutedFetcher(
        [
            ("cn.bing.com/search", TimeoutError("bing unavailable")),
            (
                "html.duckduckgo.com/html/",
                fetch_response("https://html.duckduckgo.com/html/", duckduckgo),
            ),
            (
                "https://papers.example/rwkv",
                fetch_response(
                    "https://papers.example/rwkv",
                    b"<html><body>RWKV paper</body></html>",
                ),
            ),
        ]
    )

    sources = KeylessWebProvider(fetcher=fetcher).search(query, 1)

    assert len(sources) == 1
    assert all("q=RWKV+paper" in url for url in fetcher.urls[:2])
    assert sources[0].structured_fields["discovery_provider"] == "duckduckgo-html"


def test_tavily_prefers_independently_fetched_page_over_extracted_content() -> None:
    api_key = "test-tavily-credential"
    query = "RWKV local agent retrieval"
    search_payload = json.dumps(
        {
            "request_id": "request-1",
            "results": [
                {
                    "title": "RWKV",
                    "url": "https://rwkv.example/project",
                    "content": "provider-generated snippet is not evidence",
                    "raw_content": "provider-extracted content is only a transport fallback",
                    "score": 0.91,
                }
            ],
        }
    ).encode()

    class TavilyFetcher:
        def __init__(self) -> None:
            self.posts = []
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            self.posts.append((url, dict(payload), dict(headers or {})))
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            self.urls.append(url)
            return fetch_response(
                url,
                b"<html><body>Original project page evidence.</body></html>",
            )

    fetcher = TavilyFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=(api_key,)).search(query, 3)

    assert len(result) == 1
    assert fetcher.posts[0][1] == {
        "query": query,
        "search_depth": "basic",
        "max_results": 3,
        "include_answer": False,
        "include_raw_content": "markdown",
        "include_images": False,
        "topic": "general",
    }
    assert fetcher.posts[0][2] == {"Authorization": f"Bearer {api_key}"}
    assert fetcher.urls == ["https://rwkv.example/project"]
    assert result[0].raw == b"<html><body>Original project page evidence.</body></html>"
    assert b"provider-generated snippet" not in result[0].raw
    assert b"provider-extracted content" not in result[0].raw
    assert result[0].structured_fields["discovery_provider"] == "tavily-search-api"
    assert result[0].structured_fields["evidence_transport"] == "direct_public_http"
    assert result[0].source_type == "public_web_page"
    assert api_key not in json.dumps(result.provider_attempts)
    assert result.provider_attempts[0]["response_sha256"] == hashlib.sha256(
        search_payload
    ).hexdigest()


def test_tavily_provider_advances_key_pool_on_provider_432() -> None:
    class ProviderError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("432 provider quota unavailable")
            self.response = SimpleNamespace(status_code=432)

    class RotatingFetcher:
        def __init__(self) -> None:
            self.authorizations = []

        def post_json(self, url, payload, *, headers=None):
            del payload
            self.authorizations.append(dict(headers or {})["Authorization"])
            if len(self.authorizations) == 1:
                raise ProviderError()
            return fetch_response(
                url,
                json.dumps(
                    {
                        "request_id": "request-2",
                        "results": [
                            {"title": "Page", "url": "https://example.test/page"}
                        ],
                    }
                ).encode(),
                "application/json",
            )

        def fetch(self, url, *, headers=None):
            return fetch_response(url, b"original evidence", "text/plain")

    fetcher = RotatingFetcher()
    result = TavilyWebProvider(
        fetcher=fetcher,
        api_keys=("quota-exhausted", "working-key"),
    ).search("same query", 1)

    assert fetcher.authorizations == [
        "Bearer quota-exhausted",
        "Bearer working-key",
    ]
    assert len(result) == 1
    assert result.provider_attempts[0]["status"] == "ok"
    assert result.provider_attempts[0]["credential_attempt_count"] == 2
    assert result.provider_attempts[0]["credential_attempts"][0]["status_code"] == 432
    assert result.provider_attempts[0]["credential_attempts"][1]["status"] == "ok"
    assert all(
        key not in json.dumps(result.provider_attempts)
        for key in ("quota-exhausted", "working-key")
    )


def test_tavily_retries_extensionless_directory_without_weakening_peer_check() -> None:
    search_payload = json.dumps(
        {
            "request_id": "request-directory",
            "results": [
                {
                    "title": "Packaging guide",
                    "url": "https://packaging.example/guides/pyproject-toml",
                }
            ],
        }
    ).encode()

    class DirectoryFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            if not url.endswith("/"):
                raise FetchPolicyError("retrieval peer address is unavailable")
            return fetch_response(url, b"canonical original page", "text/plain")

    fetcher = DirectoryFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=("credential",)).search(
        "pyproject guide", 1
    )

    assert fetcher.urls == [
        "https://packaging.example/guides/pyproject-toml",
        "https://packaging.example/guides/pyproject-toml/",
    ]
    assert result[0].raw == b"canonical original page"
    assert result[0].structured_fields["discovery_url"] == fetcher.urls[0]
    assert result.provider_attempts[0]["canonical_directory_retry_count"] == 1
    assert result.provider_attempts[0]["page_fetch_failure_count"] == 0


def test_tavily_retries_one_transient_page_failure_and_records_safe_fingerprint() -> None:
    api_key = "credential-must-not-leak"
    sensitive_path = "/private/result"
    sensitive_query = "signed=raw-url-value-must-not-leak"
    result_url = f"https://evidence.example{sensitive_path}?{sensitive_query}"
    search_payload = json.dumps(
        {
            "request_id": "request-transient",
            "results": [{"title": "Evidence", "url": result_url}],
        }
    ).encode()

    class TransientFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            if len(self.urls) == 1:
                raise requests.exceptions.Timeout(
                    f"transient failure at {result_url} using {api_key}"
                )
            return fetch_response(url, b"independently fetched evidence", "text/plain")

    fetcher = TransientFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=(api_key,)).search(
        "fixed query", 1
    )

    attempt = result.provider_attempts[0]
    diagnostics = json.dumps(attempt["page_fetch_attempt_failures"])
    assert fetcher.urls == [result_url, result_url]
    assert len(result) == 1
    assert attempt["page_transport_retry_count"] == 1
    assert attempt["page_fetch_failure_count"] == 0
    assert attempt["page_fetch_attempt_failure_count"] == 1
    assert attempt["page_fetch_attempt_failures"][0]["category"] == "transport_timeout"
    assert attempt["page_fetch_attempt_failures"][0]["url_sha256"] == hashlib.sha256(
        result_url.encode()
    ).hexdigest()
    assert api_key not in diagnostics
    assert sensitive_path not in diagnostics
    assert sensitive_query not in diagnostics


def test_tavily_bounds_persistent_transient_page_retry() -> None:
    result_url = "https://evidence.example/unavailable"
    search_payload = json.dumps(
        {
            "request_id": "request-persistent",
            "results": [{"title": "Unavailable", "url": result_url}],
        }
    ).encode()

    class FailingFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            raise requests.exceptions.ConnectionError("temporary route failure")

    fetcher = FailingFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=("credential",)).search(
        "fixed query", 1
    )

    attempt = result.provider_attempts[0]
    assert fetcher.urls == [result_url, result_url]
    assert len(result) == 0
    assert attempt["page_transport_retry_count"] == 1
    assert attempt["page_fetch_failure_count"] == 1
    assert attempt["page_fetch_attempt_failure_count"] == 2
    assert [
        item["attempt"] for item in attempt["page_fetch_attempt_failures"]
    ] == ["initial", "transport_retry"]


def test_tavily_uses_exact_extracted_markdown_after_bounded_transport_failure() -> None:
    api_key = "credential-must-not-leak"
    result_url = "https://evidence.example/unreachable"
    extracted = "# Exact extracted page\n\nRWKV repository evidence."
    search_payload = json.dumps(
        {
            "request_id": "request-extracted",
            "results": [
                {
                    "title": "RWKV evidence",
                    "url": result_url,
                    "content": "generated-style snippet must not be used",
                    "raw_content": extracted,
                    "score": 0.94,
                }
            ],
        }
    ).encode()

    class TimeoutFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            raise requests.exceptions.ConnectTimeout("local direct route timed out")

    fetcher = TimeoutFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=(api_key,)).search(
        "fixed query", 1
    )

    attempt = result.provider_attempts[0]
    assert fetcher.urls == [result_url, result_url]
    assert len(result) == 1
    assert result[0].raw == extracted.encode()
    assert b"generated-style snippet" not in result[0].raw
    assert result[0].source_type == "tavily_extracted_public_web_page"
    assert result[0].structured_fields["evidence_transport"] == (
        "tavily_extracted_markdown"
    )
    assert result[0].structured_fields["extracted_content_sha256"] == hashlib.sha256(
        extracted.encode()
    ).hexdigest()
    assert result[0].structured_fields["provider_request_id"] == "request-extracted"
    assert attempt["direct_page_commit_count"] == 0
    assert attempt["provider_extracted_page_commit_count"] == 1
    assert attempt["provider_extracted_page_rejection_count"] == 0
    assert attempt["page_fetch_failure_count"] == 1
    assert api_key not in json.dumps(result.provider_attempts)


def test_tavily_opens_only_same_request_host_circuit_after_bounded_failure() -> None:
    first_url = "https://same-host.example/first"
    second_url = "https://same-host.example/second"
    search_payload = json.dumps(
        {
            "request_id": "request-circuit",
            "results": [
                {"title": "First", "url": first_url, "raw_content": "first evidence"},
                {
                    "title": "Second",
                    "url": second_url,
                    "raw_content": "second evidence",
                },
            ],
        }
    ).encode()

    class TimeoutFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            raise requests.exceptions.ConnectTimeout("same host unavailable")

    validated_urls = []
    fetcher = TimeoutFetcher()
    provider = TavilyWebProvider(
        fetcher=fetcher,
        api_keys=("credential",),
        url_validator=lambda url: validated_urls.append(url) or url,
    )

    first = provider.search("fixed query", 2)
    second = provider.search("fixed query", 2)

    for result in (first, second):
        attempt = result.provider_attempts[0]
        assert [source.raw for source in result] == [
            b"first evidence",
            b"second evidence",
        ]
        assert attempt["page_transport_retry_count"] == 1
        assert attempt["page_fetch_failure_count"] == 1
        assert attempt["provider_extracted_page_commit_count"] == 2
        assert attempt["host_circuit_open_host_count"] == 1
        assert attempt["host_circuit_open_skip_count"] == 1
        assert attempt["host_circuit_validation_failure_count"] == 0
    assert fetcher.urls == [first_url, first_url, first_url, first_url]
    assert validated_urls == [second_url, second_url]


def test_tavily_host_circuit_does_not_skip_a_different_host() -> None:
    first_url = "https://unavailable.example/first"
    second_url = "https://working.example/second"
    search_payload = json.dumps(
        {
            "request_id": "request-mixed-hosts",
            "results": [
                {"title": "First", "url": first_url, "raw_content": "first evidence"},
                {
                    "title": "Second",
                    "url": second_url,
                    "raw_content": "unused extracted content",
                },
            ],
        }
    ).encode()

    class MixedFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            if url == first_url:
                raise requests.exceptions.ConnectTimeout("first host unavailable")
            return fetch_response(url, b"direct second-host evidence", "text/plain")

    fetcher = MixedFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=("credential",)).search(
        "fixed query", 2
    )

    assert fetcher.urls == [first_url, first_url, second_url]
    assert [source.source_type for source in result] == [
        "tavily_extracted_public_web_page",
        "public_web_page",
    ]
    assert result.provider_attempts[0]["host_circuit_open_skip_count"] == 0


def test_tavily_host_circuit_revalidates_public_url_before_extracted_content() -> None:
    first_url = "https://same-host.example/first"
    blocked_url = "https://same-host.example/blocked"
    search_payload = json.dumps(
        {
            "request_id": "request-circuit-policy",
            "results": [
                {"title": "First", "url": first_url, "raw_content": "first evidence"},
                {
                    "title": "Blocked",
                    "url": blocked_url,
                    "raw_content": "must not bypass validation",
                },
            ],
        }
    ).encode()

    class TimeoutFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            raise requests.exceptions.ConnectTimeout("same host unavailable")

    def reject_url(url):
        assert url == blocked_url
        raise FetchPolicyError("retrieval URL resolves to a non-public address")

    fetcher = TimeoutFetcher()
    result = TavilyWebProvider(
        fetcher=fetcher,
        api_keys=("credential",),
        url_validator=reject_url,
    ).search("fixed query", 2)

    attempt = result.provider_attempts[0]
    assert fetcher.urls == [first_url, first_url]
    assert len(result) == 1
    assert result[0].raw == b"first evidence"
    assert attempt["host_circuit_open_skip_count"] == 0
    assert attempt["host_circuit_validation_failure_count"] == 1
    assert attempt["provider_extracted_page_commit_count"] == 1
    assert attempt["page_fetch_attempt_failures"][-1]["attempt"] == (
        "host_circuit_public_url_validation"
    )
    assert attempt["page_fetch_attempt_failures"][-1]["category"] == "fetch_policy"


@pytest.mark.parametrize(
    "raw_content",
    [None, 7, "   ", "x" * 1_000_001],
)
def test_tavily_rejects_invalid_or_oversized_extracted_content(raw_content) -> None:
    result_url = "https://evidence.example/unreachable"
    search_payload = json.dumps(
        {
            "request_id": "request-invalid-extracted",
            "results": [
                {
                    "title": "Invalid extracted content",
                    "url": result_url,
                    "raw_content": raw_content,
                }
            ],
        }
    ).encode()

    class TimeoutFetcher:
        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del url, headers
            raise requests.exceptions.ReadTimeout("direct route timed out")

    result = TavilyWebProvider(
        fetcher=TimeoutFetcher(), api_keys=("credential",)
    ).search("fixed query", 1)

    attempt = result.provider_attempts[0]
    assert len(result) == 0
    assert attempt["provider_extracted_page_commit_count"] == 0
    assert attempt["provider_extracted_page_rejection_count"] == 1


def test_tavily_rejects_extracted_content_after_permanent_http_failure() -> None:
    result_url = "https://evidence.example/not-found"
    search_payload = json.dumps(
        {
            "request_id": "request-permanent",
            "results": [
                {
                    "title": "Stale result",
                    "url": result_url,
                    "raw_content": "must not be accepted after HTTP 404",
                }
            ],
        }
    ).encode()

    class PermanentHttpError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("permanent HTTP failure")
            self.response = SimpleNamespace(status_code=404)

    class PermanentFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            raise PermanentHttpError()

    fetcher = PermanentFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=("credential",)).search(
        "fixed query", 1
    )

    assert fetcher.urls == [result_url]
    assert len(result) == 0
    assert result.provider_attempts[0]["page_transport_retry_count"] == 0
    assert result.provider_attempts[0]["provider_extracted_page_commit_count"] == 0


def test_tavily_never_transport_retries_public_fetch_policy_failure() -> None:
    sensitive_path = "/must-not-appear"
    result_url = f"https://private.example{sensitive_path}"
    search_payload = json.dumps(
        {
            "request_id": "request-policy",
            "results": [
                {
                    "title": "Blocked",
                    "url": result_url,
                    "raw_content": "must never bypass a public fetch policy failure",
                }
            ],
        }
    ).encode()

    class PolicyFailingFetcher:
        def __init__(self) -> None:
            self.urls = []

        def post_json(self, url, payload, *, headers=None):
            del payload, headers
            return fetch_response(url, search_payload, "application/json")

        def fetch(self, url, *, headers=None):
            del headers
            self.urls.append(url)
            raise FetchPolicyError("retrieval URL resolves to a non-public address")

    fetcher = PolicyFailingFetcher()
    result = TavilyWebProvider(fetcher=fetcher, api_keys=("credential",)).search(
        "fixed query", 1
    )

    attempt = result.provider_attempts[0]
    diagnostics = json.dumps(attempt["page_fetch_attempt_failures"])
    assert fetcher.urls == [result_url]
    assert len(result) == 0
    assert attempt["page_transport_retry_count"] == 0
    assert attempt["page_fetch_failure_count"] == 1
    assert attempt["page_fetch_attempt_failure_count"] == 1
    assert attempt["page_fetch_attempt_failures"][0]["category"] == "fetch_policy"
    assert attempt["provider_extracted_page_commit_count"] == 0
    assert sensitive_path not in diagnostics


def test_local_web_provider_uses_keyless_fallback_without_query_rewrite() -> None:
    query = "  preserve  RWKV spacing  "
    source = RetrievedSource(
        url="https://example.test/rwkv",
        raw=b"RWKV",
        media_type="text/plain",
        source_type="public_web_page",
    )

    class EmptyTavily:
        def search(self, selected_query, max_results):
            assert selected_query == query.strip()
            assert max_results == 2
            return WebSearchResult(
                sources=(),
                provider_attempts=({"provider": "tavily", "status": "error"},),
            )

    class WorkingKeyless:
        def search(self, selected_query, max_results):
            assert selected_query == query.strip()
            assert max_results == 2
            return WebSearchResult(
                sources=(source,),
                provider_attempts=({"provider": "bing-rss", "status": "ok"},),
            )

    result = LocalWebProvider(
        tavily=EmptyTavily(),
        keyless=WorkingKeyless(),
    ).search(query, 2)

    assert result.sources == (source,)
    assert result.provider_attempts == (
        {"provider": "tavily", "status": "error"},
        {"provider": "bing-rss", "status": "ok"},
    )


def test_structured_connector_preserves_priority_fields_beyond_source_order() -> None:
    value = {f"filler_{index}": f"value-{index}" for index in range(40)}
    value.update(
        {
            "full_name": "vllm-project/vllm",
            "html_url": "https://github.com/vllm-project/vllm",
            "default_branch": "main",
        }
    )
    fetcher = RoutedFetcher(
        [
            (
                "api.github.com/repos/vllm-project/vllm",
                fetch_response(
                    "https://api.github.com/repos/vllm-project/vllm",
                    json.dumps(value).encode(),
                    "application/json",
                ),
            )
        ]
    )

    source = PublicConnectorProvider(fetcher=fetcher).lookup(
        "github_repository", "vllm-project/vllm"
    )[0]

    assert source.structured_fields["full_name"] == "vllm-project/vllm"
    assert source.structured_fields["html_url"] == "https://github.com/vllm-project/vllm"
    assert source.structured_fields["default_branch"] == "main"


def test_cleanup_chunk_and_snapshot_preserve_exact_offsets(tmp_path) -> None:
    clean, title = clean_document(
        b"<html><head><title>Page</title><script>ignore</script></head>"
        b"<body><h1>Fact</h1><p>Version 4.2 is current.</p></body></html>",
        "text/html",
    )
    assert title == "Page"
    assert "ignore" not in clean
    assert "Version 4.2 is current." in clean
    chunks = chunk_text(clean, max_chars=256, overlap_chars=16)
    assert chunks
    assert all(clean[item.start_char : item.end_char] == item.text for item in chunks)

    store = SnapshotStore(tmp_path / "snapshots")
    snapshot = store.commit(
        url="https://example.test/page",
        media_type="text/html",
        raw=b"raw",
        clean_text=clean,
        retrieved_at="2026-08-25T00:00:00+00:00",
        title=title,
    )
    assert snapshot.snapshot_digest == hashlib.sha256(clean.encode()).hexdigest()
    assert store.read_clean(snapshot.snapshot_digest) == clean
    assert store.commit(
        url="https://example.test/page",
        media_type="text/html",
        raw=b"raw",
        clean_text=clean,
        retrieved_at="2026-08-25T00:00:00+00:00",
        title=title,
    ) == snapshot


def test_identical_clean_text_keeps_distinct_raw_sources_immutable(tmp_path) -> None:
    store = SnapshotStore(tmp_path / "snapshots")
    first = store.commit(
        url="https://one.example.test/page",
        media_type="text/plain",
        raw=b"same fact\n",
        clean_text="same fact",
        retrieved_at="2026-08-25T00:00:00+00:00",
    )
    second = store.commit(
        url="https://two.example.test/page",
        media_type="text/html",
        raw=b"<p>same fact</p>",
        clean_text="same fact",
        retrieved_at="2026-08-25T00:01:00+00:00",
    )

    directory = store.root / first.snapshot_digest[:2] / first.snapshot_digest
    assert first.snapshot_digest == second.snapshot_digest
    assert first.raw_digest != second.raw_digest
    assert store.read_clean(first.snapshot_digest) == "same fact"
    assert sorted(path.name for path in (directory / "raw").iterdir()) == [
        f"{first.raw_digest}.bin",
        f"{second.raw_digest}.bin",
    ]
    assert len(tuple((directory / "manifests").iterdir())) == 2


def test_url_policy_rejects_private_and_non_http_targets() -> None:
    assert validate_public_url(
        "https://example.test/path", resolver=lambda _host: ("93.184.216.34",)
    ) == "https://example.test/path"
    for url in ("file:///etc/passwd", "http://127.0.0.1/x", "http://example.test:8080"):
        with pytest.raises(FetchPolicyError):
            validate_public_url(url, resolver=lambda _host: ("127.0.0.1",))


def test_connected_peer_is_revalidated_after_dns_resolution() -> None:
    def response_for(address: str):
        peer = SimpleNamespace(getpeername=lambda: (address, 443))
        return SimpleNamespace(raw=SimpleNamespace(_connection=SimpleNamespace(sock=peer)))

    assert validate_public_peer(response_for("93.184.216.34")) == "93.184.216.34"
    with pytest.raises(FetchPolicyError, match="non-public"):
        validate_public_peer(response_for("127.0.0.1"))
    with pytest.raises(FetchPolicyError, match="unavailable"):
        validate_public_peer(SimpleNamespace(raw=SimpleNamespace()))


def test_streaming_http_error_response_is_always_closed() -> None:
    peer = SimpleNamespace(getpeername=lambda: ("93.184.216.34", 443))

    class ErrorResponse:
        status_code = 503
        headers = {}
        url = "https://example.test/unavailable"
        raw = SimpleNamespace(_connection=SimpleNamespace(sock=peer))
        closed = False

        def raise_for_status(self):
            raise RuntimeError("503 unavailable")

        def close(self):
            self.closed = True

    response = ErrorResponse()

    class ErrorSession:
        trust_env = True
        headers: dict[str, str] = {}

        @staticmethod
        def get(*_args, **_kwargs):
            return response

    fetcher = PublicHttpFetcher(
        resolver=lambda _host: ("93.184.216.34",),
        session=ErrorSession(),
    )

    with pytest.raises(RuntimeError, match="503 unavailable"):
        fetcher.fetch("https://example.test/unavailable")

    assert response.closed is True


def test_public_fetcher_uses_separate_connect_and_read_timeouts() -> None:
    peer = SimpleNamespace(getpeername=lambda: ("93.184.216.34", 443))

    class SuccessResponse:
        status_code = 200
        headers = {"Content-Type": "text/plain"}
        url = "https://example.test/evidence"
        raw = SimpleNamespace(_connection=SimpleNamespace(sock=peer))

        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def iter_content(chunk_size):
            del chunk_size
            return iter((b"evidence",))

        @staticmethod
        def close():
            return None

    class CapturingSession:
        trust_env = True
        headers: dict[str, str] = {}

        def __init__(self) -> None:
            self.timeouts = []

        def get(self, *_args, **kwargs):
            self.timeouts.append(kwargs["timeout"])
            return SuccessResponse()

        def post(self, *_args, **kwargs):
            self.timeouts.append(kwargs["timeout"])
            return SuccessResponse()

    session = CapturingSession()
    fetcher = PublicHttpFetcher(
        timeout_seconds=20,
        connect_timeout_seconds=5,
        resolver=lambda _host: ("93.184.216.34",),
        session=session,
    )

    fetcher.fetch("https://example.test/evidence")
    fetcher.post_json("https://example.test/evidence", {"query": "fixed"})

    assert session.timeouts == [(5.0, 20.0), (5.0, 20.0)]


def test_live_kernel_freezes_exact_evidence_and_reuses_route_cache(tmp_path) -> None:
    provider = FakeWebProvider()
    store = SnapshotStore(tmp_path / "snapshots")
    backend = LiveRetrievalBackend(
        store,
        web_provider=provider,
        connector_provider=FakeConnectorProvider(),
        clock=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
    )

    first = backend.execute(
        "web_search", {"query": "current release", "max_results": 3}
    )
    second = backend.execute(
        "web_search", {"query": "current release", "max_results": 3}
    )

    assert first == second
    assert provider.calls == 1
    assert first.status == "evidence_committed"
    assert first.records
    record = first.records[0]
    snapshot = store.read_clean(record.snapshot_digest)
    assert record.verify_snapshot(snapshot)
    assert "Version 4.2 is current." in record.exact_spans[0].text


def test_live_kernel_groups_chunk_spans_under_one_source_record(tmp_path) -> None:
    class LongSourceProvider:
        provider_name = "long-source"

        @staticmethod
        def search(query: str, max_results: int):
            assert query == "long evidence"
            assert max_results == 1
            return (
                RetrievedSource(
                    url="https://example.test/long",
                    raw=(("alpha evidence sentence. " * 800).encode("utf-8")),
                    media_type="text/plain; charset=utf-8",
                    source_type="public_web_page",
                    structured_fields={"rank": 1},
                ),
            )

    store = SnapshotStore(tmp_path / "snapshots")
    backend = LiveRetrievalBackend(
        store,
        web_provider=LongSourceProvider(),
        connector_provider=FakeConnectorProvider(),
        clock=lambda: datetime(2026, 8, 29, tzinfo=timezone.utc),
        max_records=3,
    )

    envelope = backend.execute(
        "web_search", {"query": "long evidence", "max_results": 1}
    )

    assert len(envelope.records) == 1
    assert len(envelope.records[0].exact_spans) == 3
    assert envelope.records[0].structured_fields == {"rank": 1}
    assert envelope.truncated is True
    snapshot = store.read_clean(envelope.records[0].snapshot_digest)
    assert envelope.records[0].verify_snapshot(snapshot)


def test_live_kernel_rejects_misplaced_route_without_provider_fallback(tmp_path) -> None:
    provider = FakeWebProvider()
    store = SnapshotStore(tmp_path / "snapshots")
    backend = LiveRetrievalBackend(
        store,
        web_provider=provider,
        connector_provider=FakeConnectorProvider(),
        clock=lambda: datetime(2026, 8, 25, tzinfo=timezone.utc),
    )
    request_b = {"query": "current release", "max_results": 3}
    envelope_b = backend.execute("web_search", request_b)
    assert provider.calls == 1

    request_a = {"query": "different request", "max_results": 3}
    digest_a = external_evidence_request_digest("web_search", request_a)
    misplaced_path = (
        store.root / "routes" / digest_a[:2] / f"{digest_a}.json"
    )
    store.write_immutable(
        misplaced_path,
        json.dumps(
            envelope_b.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    )

    with pytest.raises(ExternalEvidenceRequestMismatch):
        backend.execute("web_search", request_a)

    assert provider.calls == 1


def test_runtime_policy_is_goal_bound_and_offline_hides_network_tools(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE)
    goal = GoalState.create(
        request="Calculate 4+4.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    restored = GoalState.from_dict(goal.to_dict())
    assert restored.runtime_policy == runtime_policy_document(config)
    harness = build_product_harness(
        config=config,
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
    )
    names = {item["name"] for item in harness.g1i_tool_definitions()}
    assert "calculator" in names
    assert "web_search" not in names
    assert "connector_lookup" not in names


def test_goal_policy_is_the_single_menu_and_execution_authority(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    goal = GoalState.create(
        request="Search the public web for the current release.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(
            RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE)
        ),
    )
    # The Harness registration config intentionally disagrees with the Goal.
    # It keeps stable network classes registered but must not authorize them.
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
        stable_network_menu=True,
    )
    assert {"web_search", "connector_lookup"} <= {
        item["name"] for item in harness.g1i_tool_definitions()
    }
    assert operation_allowed_by_retrieval_policy(
        goal,
        network_access="public_web",
    ) is False
    assert network_policy_from_goal(goal).mode is NetworkPolicyMode.OFFLINE

    result = harness.execute(
        TaskAction("web_search", {"query": "current release", "max_results": 5}),
        goal,
    )

    assert result.success is False
    assert result.error is not None
    assert result.error["type"] == "NetworkPolicyRejected"
    assert result.metadata["network_policy"]["mode"] == "offline"
    assert result.metadata["network_policy"]["reason"] == "network_disabled"
    recovered = harness.recover_committed_action(
        TaskAction("web_search", {"query": "current release", "max_results": 5}),
        goal,
    )
    assert recovered is not None
    assert recovered.success is False
    assert recovered.error is not None
    assert recovered.error["type"] == "NetworkPolicyRejected"
    assert recovered.metadata["network_policy"]["mode"] == "offline"


def test_goal_bound_provenance_uses_goal_public_roots_not_registration_config(
    tmp_path,
) -> None:
    workspace = tmp_path / "workspace"
    public = workspace / "public"
    public.mkdir(parents=True)
    (public / "release.txt").write_text("release-4.2", encoding="utf-8")
    goal = GoalState.create(
        request="Find the release.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(
            RetrievalRuntimeConfig(
                mode=NetworkPolicyMode.EXPLICIT_EGRESS,
                explicit_approval=True,
                public_workspace_paths=("public",),
            )
        ),
    )
    resolver = WorkspaceProvenanceResolver(
        RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        goal_bound=True,
    )

    assert resolver(goal, "web_search", {"query": "release-4.2"}) == {
        "query": EgressProvenance.WORKSPACE_PUBLIC
    }


def test_fixed_selector_menu_exposes_network_tools_but_offline_rejects_execution(
    tmp_path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE)
    goal = GoalState.create(
        request="Search the public web for the current release.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    harness = build_product_harness(
        config=config,
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
        stable_network_menu=True,
    )
    names = {item["name"] for item in harness.g1i_tool_definitions()}
    assert {"web_search", "connector_lookup"} <= names

    result = harness.execute(
        TaskAction("web_search", {"query": "current release", "max_results": 5}),
        goal,
    )
    assert result.success is False
    assert result.error is not None
    assert result.error["type"] == "NetworkPolicyRejected"
    assert result.metadata["network_policy"]["reason"] == "network_disabled"


def test_runtime_policy_can_enable_advisory_state_router_shadow() -> None:
    policy = runtime_policy_document(
        RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        state_router_mode="shadow",
    )
    assert policy["state_router"] == {
        "schema_version": "rwkv-lh.state-router-runtime-policy.v1",
        "mode": "shadow",
    }


def test_product_connector_schema_only_discloses_configured_operations(tmp_path) -> None:
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
    )

    operations = harness.definition("connector_lookup").argument_schema[
        "operation"
    ]["enum"]

    assert operations == [
        "github_repository",
        "github_release",
        "github_commit",
        "package_release",
        "scholarly_record",
        "weather",
    ]
    assert "github_code" not in operations
    assert "weather_alerts" not in operations


def test_workspace_provenance_is_conservative_and_does_not_rewrite(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    (workspace / "public").mkdir(parents=True)
    (workspace / "private.txt").write_text("internal-customer-42", encoding="utf-8")
    (workspace / "public" / "release.txt").write_text("release-4.2", encoding="utf-8")
    config = RetrievalRuntimeConfig(
        mode=NetworkPolicyMode.EXPLICIT_EGRESS,
        explicit_approval=True,
        public_workspace_paths=("public",),
    )
    goal = GoalState.create(
        request="Find public release information.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    resolver = WorkspaceProvenanceResolver(config)
    assert resolver(goal, "web_search", {"query": "internal-customer-42"}) == {
        "query": EgressProvenance.WORKSPACE_SENSITIVE
    }
    assert resolver(goal, "web_search", {"query": "release-4.2"}) == {
        "query": EgressProvenance.WORKSPACE_PUBLIC
    }
    assert resolver(goal, "web_search", {"query": "api_key=abcdef123456"}) == {
        "query": EgressProvenance.SECRET
    }
    assert resolver(
        goal,
        "web_search",
        {"query": "sk-exampleCredentialValue123456"},
    ) == {"query": EgressProvenance.SECRET}


@pytest.mark.parametrize("incomplete_kind", ["file_budget", "total_budget", "skip"])
def test_incomplete_workspace_scan_is_unknown_and_rejected(
    tmp_path,
    incomplete_kind,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    max_file_bytes = 100
    max_scan_bytes = 100
    if incomplete_kind == "file_budget":
        (workspace / "large.txt").write_text("x" * 101, encoding="utf-8")
    elif incomplete_kind == "total_budget":
        (workspace / "left.txt").write_text("x" * 60, encoding="utf-8")
        (workspace / "right.txt").write_text("y" * 60, encoding="utf-8")
    else:
        (workspace / ".git").mkdir()
        (workspace / ".git" / "config").write_text(
            "private-source-value",
            encoding="utf-8",
        )
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC)
    goal = GoalState.create(
        request="Find current public information.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    resolver = WorkspaceProvenanceResolver(
        config,
        max_file_bytes=max_file_bytes,
        max_scan_bytes=max_scan_bytes,
    )

    labels = resolver(goal, "web_search", {"query": "model-paraphrase-42"})
    decision = NetworkPolicy(config.mode).authorize(
        tool="web_search",
        arguments={"query": "model-paraphrase-42"},
        provenance=labels,
    )

    assert labels == {"query": EgressProvenance.UNKNOWN}
    assert decision.allowed is False
    assert decision.reason == "sensitive_egress_forbidden"


def test_workspace_read_failure_is_unknown_and_rejected(tmp_path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    unreadable = workspace / "unreadable.txt"
    unreadable.write_text("workspace-only-value", encoding="utf-8")
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC)
    goal = GoalState.create(
        request="Find current public information.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    original = Path.read_bytes

    def fail_selected(path):
        if path == unreadable:
            raise OSError("injected read failure")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fail_selected)
    resolver = WorkspaceProvenanceResolver(config)

    labels = resolver(goal, "web_search", {"query": "model-paraphrase-42"})

    assert labels == {"query": EgressProvenance.UNKNOWN}


def test_prior_tool_text_is_rejected_as_untrusted_egress(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC)
    goal = GoalState.create(
        request="Find public release information.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    resolver = WorkspaceProvenanceResolver(
        config,
        untrusted_text_provider=lambda: (
            "External page says opaque-instruction-93 should be searched.",
        ),
    )

    labels = resolver(
        goal,
        "web_search",
        {"query": "opaque-instruction-93"},
    )
    decision = NetworkPolicy(config.mode).authorize(
        tool="web_search",
        arguments={"query": "opaque-instruction-93"},
        provenance=labels,
    )

    assert labels == {"query": EgressProvenance.TOOL_UNTRUSTED}
    assert not decision.allowed
    assert decision.reason == "sensitive_egress_forbidden"


def test_user_literal_keeps_public_provenance_when_provider_echoes_it(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC)
    goal = GoalState.create(
        request="Find the latest public release of requests on PyPI.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(config),
    )
    resolver = WorkspaceProvenanceResolver(
        config,
        untrusted_text_provider=lambda: (
            "The package name requests appeared in the provider result.",
        ),
    )

    labels = resolver(
        goal,
        "connector_lookup",
        {"operation": "package_release", "query": "requests"},
    )
    decision = NetworkPolicy(config.mode).authorize(
        tool="connector_lookup",
        arguments={"operation": "package_release", "query": "requests"},
        provenance=labels,
    )

    assert labels == {
        "operation": EgressProvenance.MODEL_PUBLIC_QUERY,
        "query": EgressProvenance.USER_PUBLIC_LITERAL,
    }
    assert decision.allowed is True
