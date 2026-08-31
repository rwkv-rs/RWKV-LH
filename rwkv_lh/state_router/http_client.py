"""Strict HTTP client for the separately managed local State Router service."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import requests

from rwkv_lh.state_router.protocol import RouterInput


ROUTER_SERVICE_REQUEST_SCHEMA = "rwkv-lh.state-router-service-request.v1"
ROUTER_SERVICE_RESPONSE_SCHEMA = "rwkv-lh.state-router-service-response.v1"
ROUTER_SERVICE_HEALTH_SCHEMA = "rwkv-lh.state-router-service-health.v1"


class StateRouterHTTPClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        value = str(base_url).strip().rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("State Router URL must be absolute HTTP(S)")
        if timeout_seconds <= 0:
            raise ValueError("State Router timeout must be positive")
        self.base_url = value
        self.timeout_seconds = float(timeout_seconds)
        self._session = session or requests.Session()
        self._owns_session = session is None
        self._session.trust_env = False

    def _json(self, response: requests.Response) -> Mapping[str, Any]:
        response.raise_for_status()
        try:
            value = response.json()
        except ValueError as exc:
            raise RuntimeError("State Router returned invalid JSON") from exc
        if not isinstance(value, Mapping):
            raise RuntimeError("State Router response must be an object")
        return value

    def health(self) -> dict[str, Any]:
        response = self._session.get(
            self.base_url + "/health",
            timeout=self.timeout_seconds,
        )
        value = dict(self._json(response))
        if value.get("schema_version") != ROUTER_SERVICE_HEALTH_SCHEMA:
            raise RuntimeError("State Router returned an unsupported health schema")
        if value.get("available") is not True:
            raise RuntimeError("State Router is not available")
        return value

    def route_many(self, inputs: Sequence[RouterInput]) -> list[dict[str, Any]]:
        if not inputs:
            raise ValueError("State Router request must contain at least one input")
        response = self._session.post(
            self.base_url + "/v1/route",
            json={
                "schema_version": ROUTER_SERVICE_REQUEST_SCHEMA,
                "inputs": [item.to_dict() for item in inputs],
            },
            timeout=self.timeout_seconds,
        )
        value = self._json(response)
        if value.get("schema_version") != ROUTER_SERVICE_RESPONSE_SCHEMA:
            raise RuntimeError("State Router returned an unsupported response schema")
        outputs = value.get("outputs")
        if not isinstance(outputs, list) or len(outputs) != len(inputs):
            raise RuntimeError("State Router returned the wrong output count")
        if not all(isinstance(item, Mapping) for item in outputs):
            raise RuntimeError("State Router outputs must be objects")
        return [dict(item) for item in outputs]

    def route(self, router_input: RouterInput) -> dict[str, Any]:
        return self.route_many([router_input])[0]

    def close(self) -> None:
        if self._owns_session:
            self._session.close()

    def __enter__(self) -> "StateRouterHTTPClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = [
    "ROUTER_SERVICE_HEALTH_SCHEMA",
    "ROUTER_SERVICE_REQUEST_SCHEMA",
    "ROUTER_SERVICE_RESPONSE_SCHEMA",
    "StateRouterHTTPClient",
]
