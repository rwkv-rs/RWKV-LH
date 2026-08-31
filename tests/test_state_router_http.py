from __future__ import annotations

import threading
from typing import Any, Mapping

import pytest

from rwkv_lh.inference.router_server import RouterHTTPServer
from rwkv_lh.state_router.http_client import StateRouterHTTPClient
from rwkv_lh.state_router.protocol import (
    ContextMode,
    EvidenceState,
    PolicyState,
    RouterInput,
)


class FakeRouterApp:
    def health(self) -> dict[str, Any]:
        return {
            "schema_version": "rwkv-lh.state-router-service-health.v1",
            "available": True,
            "head_hash": "head",
        }

    def route(self, value: Mapping[str, Any]) -> dict[str, Any]:
        assert value["schema_version"] == "rwkv-lh.state-router-service-request.v1"
        return {
            "schema_version": "rwkv-lh.state-router-service-response.v1",
            "outputs": [
                {
                    "schema_version": "rwkv-lh.state-router-output.v1",
                    "trace_id": item["trace_id"],
                }
                for item in value["inputs"]
            ],
        }


@pytest.fixture
def router_url() -> str:
    server = RouterHTTPServer(("127.0.0.1", 0), FakeRouterApp())  # type: ignore[arg-type]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_state_router_http_client_health_and_route(router_url: str) -> None:
    item = RouterInput(
        mode=ContextMode.FRESH,
        summary=None,
        evidence_state=EvidenceState.NONE,
        policy_state=PolicyState.NETWORK_ALLOWED,
        request="read pyproject.toml",
        trace_id="RTR-HTTP-001",
    )
    with StateRouterHTTPClient(router_url) as client:
        assert client.health()["head_hash"] == "head"
        assert client.route(item)["trace_id"] == "RTR-HTTP-001"


def test_state_router_http_client_rejects_non_object_protocol(router_url: str) -> None:
    with StateRouterHTTPClient(router_url + "/missing") as client:
        with pytest.raises(Exception):
            client.health()
