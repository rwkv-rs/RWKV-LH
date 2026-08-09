"""Structured OpenAI-compatible client for local and remote RWKV servers."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import requests

from rwkv_lh.runtime.protocol import (
    ChatCompletionRequest,
    CompletionResponse,
    HealthStatus,
    RWKVHTTPError,
    RWKVProtocolError,
    RWKVTransportError,
    TextCompletionRequest,
    TokenUsage,
    normalize_stop,
)
from rwkv_lh.runtime.sampling import get_request_seed, get_request_temperature
from rwkv_lh.runtime.settings import RuntimeSettings, get_runtime_settings


AuditHook = Callable[[Mapping[str, Any]], None]
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class OpenAICompatibleRWKVClient:
    """Thread-safe, pooled client with explicit request and response contracts."""

    backend_name = "openai_compatible_rwkv"

    def __init__(
        self,
        settings: RuntimeSettings | None = None,
        *,
        audit_hook: AuditHook | None = None,
    ):
        self.settings = settings or get_runtime_settings()
        self.audit_hook = audit_hook
        self._main_session = self._new_session()
        self._thread_sessions = threading.local()

    @property
    def model_name(self) -> str:
        return self.settings.model

    def _new_session(self) -> requests.Session:
        session = requests.Session()
        session.trust_env = self.settings.trust_environment_proxies
        return session

    def _session(self) -> requests.Session:
        session = getattr(self._thread_sessions, "session", None)
        if session is None:
            session = (
                self._main_session
                if threading.current_thread() is threading.main_thread()
                else self._new_session()
            )
            self._thread_sessions.session = session
        return session

    def _headers(self) -> dict[str, str]:
        token = self.settings.api_key or "local"
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _emit(self, event: Mapping[str, Any]) -> None:
        if self.audit_hook is None:
            return
        try:
            self.audit_hook(dict(event))
        except Exception:
            # Observability must never change model-call semantics.
            return

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, Any], float, int]:
        endpoint = self.settings.base_url + path
        attempts = self.settings.retry_attempts
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                response = self._session().request(
                    method,
                    endpoint,
                    headers=self._headers(),
                    json=dict(payload) if payload is not None else None,
                    timeout=(
                        self.settings.connect_timeout_seconds,
                        self.settings.read_timeout_seconds,
                    ),
                    verify=self.settings.verify_tls,
                )
                latency_ms = round((time.perf_counter() - started) * 1000, 1)
                if response.status_code >= 400:
                    detail = response.text[:1000].replace("\n", " ")
                    error = RWKVHTTPError(
                        response.status_code,
                        detail,
                        retryable=response.status_code in _RETRYABLE_STATUS,
                    )
                    if error.retryable and attempt < attempts:
                        self._backoff(attempt, response.headers.get("Retry-After"))
                        last_error = error
                        continue
                    raise error
                try:
                    data = json.loads(response.content.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise RWKVProtocolError(
                        "server returned invalid UTF-8 JSON"
                    ) from exc
                if not isinstance(data, dict):
                    raise RWKVProtocolError("server returned a non-object JSON response")
                return data, latency_ms, attempt
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = RWKVTransportError(f"{type(exc).__name__}: {exc}")
                if attempt >= attempts:
                    raise last_error from exc
                self._backoff(attempt, None)
        raise last_error or RWKVTransportError("model request failed")

    def _backoff(self, attempt: int, retry_after: str | None) -> None:
        if retry_after:
            try:
                delay = max(0.0, min(float(retry_after), 30.0))
            except ValueError:
                delay = self.settings.retry_backoff_seconds * (2 ** (attempt - 1))
        else:
            delay = self.settings.retry_backoff_seconds * (2 ** (attempt - 1))
        if delay > 0:
            time.sleep(delay)

    @staticmethod
    def _completion_response(data: Mapping[str, Any], latency_ms: float, attempts: int) -> CompletionResponse:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise RWKVProtocolError("response has no valid choices[0]")
        choice = choices[0]
        message = choice.get("message") if isinstance(choice.get("message"), Mapping) else {}
        content = choice.get("text")
        if content is None:
            content = message.get("content", "")
        if content is None:
            content = ""
        usage = TokenUsage.from_mapping(data.get("usage") if isinstance(data.get("usage"), Mapping) else {})
        return CompletionResponse(
            content=str(content),
            role=str(message.get("role") or "assistant"),
            finish_reason=str(choice.get("finish_reason") or "stop"),
            usage=usage.to_dict(),
            response_id=str(data.get("id") or ""),
            model=str(data.get("model") or ""),
            latency_ms=latency_ms,
            metadata={"http_attempts": attempts},
        )

    def text_completion(
        self,
        prompt: str,
        max_tokens: int = 768,
        stop: Sequence[str] | None = None,
        *,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> CompletionResponse:
        request = TextCompletionRequest(
            prompt=str(prompt),
            max_tokens=max(1, int(max_tokens)),
            temperature=(
                get_request_temperature() if temperature is None else float(temperature)
            ),
            seed=get_request_seed() if seed is None else int(seed),
            stop=normalize_stop(stop),
        )
        payload = request.payload(self.model_name)
        started = time.perf_counter()
        self._emit(
            {
                "type": "runtime_request_started",
                "endpoint": "/completions",
                "model": self.model_name,
                "temperature": request.temperature,
                "seed": request.seed,
                "max_tokens": request.max_tokens,
            }
        )
        try:
            data, latency_ms, attempts = self._request_json(
                "POST", "/completions", payload=payload
            )
            response = self._completion_response(data, latency_ms, attempts)
            self._emit(
                {
                    "type": "runtime_request_returned",
                    "endpoint": "/completions",
                    "model": self.model_name,
                    "temperature": request.temperature,
                    "seed": request.seed,
                    "latency_ms": response.latency_ms,
                    "finish_reason": response.finish_reason,
                    "usage": response.usage,
                    "http_attempts": attempts,
                }
            )
            return response
        except Exception as exc:
            self._emit(
                {
                    "type": "runtime_request_failed",
                    "endpoint": "/completions",
                    "model": self.model_name,
                    "temperature": request.temperature,
                    "seed": request.seed,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                }
            )
            raise

    def chat_completion(
        self,
        messages: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int = 768,
        stop: Sequence[str] | None = None,
        temperature: float | None = None,
        seed: int | None = None,
    ) -> CompletionResponse:
        request = ChatCompletionRequest(
            messages=tuple(dict(item) for item in messages),
            max_tokens=max(1, int(max_tokens)),
            temperature=(
                get_request_temperature() if temperature is None else float(temperature)
            ),
            seed=get_request_seed() if seed is None else int(seed),
            stop=normalize_stop(stop),
        )
        data, latency_ms, attempts = self._request_json(
            "POST", "/chat/completions", payload=request.payload(self.model_name)
        )
        return self._completion_response(data, latency_ms, attempts)

    def health(self) -> HealthStatus:
        started = time.perf_counter()
        try:
            data, latency_ms, _ = self._request_json("GET", "/models")
            models = tuple(
                str(item.get("id"))
                for item in data.get("data", [])
                if isinstance(item, Mapping) and item.get("id")
            )
            return HealthStatus(
                available=True,
                endpoint=self.settings.base_url,
                model=self.model_name,
                models=models,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            return HealthStatus(
                available=False,
                endpoint=self.settings.base_url,
                model=self.model_name,
                latency_ms=round((time.perf_counter() - started) * 1000, 1),
                error=f"{type(exc).__name__}: {exc}"[:500],
            )

    def close(self) -> None:
        self._main_session.close()
        session = getattr(self._thread_sessions, "session", None)
        if session is not None and session is not self._main_session:
            session.close()


__all__ = ["OpenAICompatibleRWKVClient"]
