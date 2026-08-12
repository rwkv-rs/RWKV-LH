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
    RWKVOutcomeUnknownError,
    RWKVProtocolError,
    RWKVTransportError,
    RuntimeCapabilities,
    TextCompletionRequest,
    TokenUsage,
    normalize_stop,
    normalize_stop_token_ids,
)
from rwkv_lh.runtime.sampling import get_request_sampling
from rwkv_lh.runtime.settings import RuntimeSettings, get_runtime_settings


AuditHook = Callable[[Mapping[str, Any]], None]
_RETRYABLE_STATUS = {425, 429, 500, 502, 503, 504}


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
        if self.settings.proxy_url:
            session.proxies.update(
                {
                    "http": self.settings.proxy_url,
                    "https": self.settings.proxy_url,
                }
            )
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
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        if self.settings.cf_access_client_id:
            headers["CF-Access-Client-Id"] = self.settings.cf_access_client_id
            headers["CF-Access-Client-Secret"] = (
                self.settings.cf_access_client_secret
            )
        return headers

    def _text_payload(self, request: TextCompletionRequest) -> dict[str, Any]:
        if self.settings.backend_profile == "vllm-rwkv-rapid":
            return request.payload(self.model_name)
        unsupported: list[str] = []
        if request.min_tokens:
            unsupported.append("min_tokens")
        if request.stop_token_ids:
            unsupported.append("stop_token_ids")
        if request.return_token_ids:
            unsupported.append("return_token_ids")
        if unsupported:
            raise ValueError(
                "rwkv-lightning-native does not support: "
                + ", ".join(unsupported)
            )
        return {
            "contents": [request.prompt],
            "max_tokens": int(request.max_tokens),
            "stop_tokens": list(request.stop),
            "temperature": float(request.temperature),
            "top_k": int(request.top_k),
            "top_p": float(request.top_p),
            "alpha_presence": float(request.presence_penalty),
            "alpha_frequency": float(request.frequency_penalty),
            "alpha_decay": float(request.penalty_decay),
            "stream": False,
        }

    def _generation_path(self) -> str:
        if self.settings.backend_profile == "rwkv-lightning-native":
            return "/chat/completions"
        return "/completions"

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
        generation: bool = False,
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
            except requests.ConnectTimeout as exc:
                last_error = RWKVTransportError(f"{type(exc).__name__}: {exc}")
                if attempt >= attempts:
                    raise last_error from exc
                self._backoff(attempt, None)
            except (requests.ReadTimeout, requests.ConnectionError) as exc:
                if generation:
                    raise RWKVOutcomeUnknownError(
                        "generation may have completed before the connection "
                        f"failed: {type(exc).__name__}: {exc}"
                    ) from exc
                last_error = RWKVTransportError(f"{type(exc).__name__}: {exc}")
                if attempt >= attempts:
                    raise last_error from exc
                self._backoff(attempt, None)
            except requests.Timeout as exc:
                if generation:
                    raise RWKVOutcomeUnknownError(
                        "generation outcome is unknown after timeout: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                last_error = RWKVTransportError(f"{type(exc).__name__}: {exc}")
                if attempt >= attempts:
                    raise last_error from exc
                self._backoff(attempt, None)
            except requests.RequestException as exc:
                if generation:
                    raise RWKVOutcomeUnknownError(
                        "generation outcome is unknown after transport failure: "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
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
        metadata: dict[str, Any] = {"http_attempts": attempts}
        if isinstance(data.get("prompt_token_ids"), list):
            metadata["prompt_token_ids"] = list(data["prompt_token_ids"])
        if isinstance(choice.get("token_ids"), list):
            metadata["token_ids"] = list(choice["token_ids"])
        return CompletionResponse(
            content=str(content),
            role=str(message.get("role") or "assistant"),
            finish_reason=str(choice.get("finish_reason") or "stop"),
            usage=usage.to_dict(),
            response_id=str(data.get("id") or ""),
            model=str(data.get("model") or ""),
            latency_ms=latency_ms,
            metadata=metadata,
        )

    def text_completion(
        self,
        prompt: str,
        max_tokens: int = 768,
        stop: Sequence[str] | None = None,
        *,
        temperature: float | None = None,
        seed: int | None = None,
        min_tokens: int = 0,
        stop_token_ids: Sequence[int] | None = None,
    ) -> CompletionResponse:
        if seed is not None:
            raise ValueError("seed is unsupported by vllm-rwkv rapid-sampling")
        sampling = get_request_sampling()
        request = TextCompletionRequest(
            prompt=str(prompt),
            max_tokens=max(1, int(max_tokens)),
            temperature=(
                sampling.temperature if temperature is None else float(temperature)
            ),
            top_p=sampling.top_p,
            top_k=sampling.top_k,
            presence_penalty=sampling.presence_penalty,
            frequency_penalty=sampling.frequency_penalty,
            penalty_decay=sampling.penalty_decay,
            min_tokens=int(min_tokens),
            stop=normalize_stop(stop),
            stop_token_ids=normalize_stop_token_ids(stop_token_ids),
            request_id=sampling.request_id,
            add_special_tokens=True,
            return_token_ids=self.settings.return_token_ids,
        )
        payload = self._text_payload(request)
        generation_path = self._generation_path()
        started = time.perf_counter()
        self._emit(
            {
                "type": "runtime_request_started",
                "endpoint": generation_path,
                "backend_profile": self.settings.backend_profile,
                "model": self.model_name,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "top_k": request.top_k,
                "presence_penalty": request.presence_penalty,
                "frequency_penalty": request.frequency_penalty,
                "penalty_decay": request.penalty_decay,
                "min_tokens": request.min_tokens,
                "stop_token_ids": list(request.stop_token_ids),
                "request_id": request.request_id,
                "max_tokens": request.max_tokens,
            }
        )
        try:
            data, latency_ms, attempts = self._request_json(
                "POST", generation_path, payload=payload, generation=True
            )
            response = self._completion_response(data, latency_ms, attempts)
            self._emit(
                {
                    "type": "runtime_request_returned",
                    "endpoint": generation_path,
                    "backend_profile": self.settings.backend_profile,
                    "model": self.model_name,
                    "temperature": request.temperature,
                    "request_id": request.request_id,
                    "latency_ms": response.latency_ms,
                    "finish_reason": response.finish_reason,
                    "usage": response.usage,
                    "http_attempts": attempts,
                }
            )
            return response
        except RWKVOutcomeUnknownError as exc:
            self._emit(
                {
                    "type": "runtime_request_unknown",
                    "endpoint": generation_path,
                    "backend_profile": self.settings.backend_profile,
                    "model": self.model_name,
                    "temperature": request.temperature,
                    "request_id": request.request_id,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "error": f"{type(exc).__name__}: {exc}"[:1000],
                }
            )
            raise
        except Exception as exc:
            self._emit(
                {
                    "type": "runtime_request_failed",
                    "endpoint": generation_path,
                    "backend_profile": self.settings.backend_profile,
                    "model": self.model_name,
                    "temperature": request.temperature,
                    "request_id": request.request_id,
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
        min_tokens: int = 0,
        stop_token_ids: Sequence[int] | None = None,
    ) -> CompletionResponse:
        if seed is not None:
            raise ValueError("seed is unsupported by vllm-rwkv rapid-sampling")
        sampling = get_request_sampling()
        request = ChatCompletionRequest(
            messages=tuple(dict(item) for item in messages),
            max_tokens=max(1, int(max_tokens)),
            temperature=(
                sampling.temperature if temperature is None else float(temperature)
            ),
            top_p=sampling.top_p,
            top_k=sampling.top_k,
            presence_penalty=sampling.presence_penalty,
            frequency_penalty=sampling.frequency_penalty,
            penalty_decay=sampling.penalty_decay,
            min_tokens=int(min_tokens),
            stop=normalize_stop(stop),
            stop_token_ids=normalize_stop_token_ids(stop_token_ids),
            request_id=sampling.request_id,
            add_special_tokens=False,
            return_token_ids=self.settings.return_token_ids,
        )
        if self.settings.backend_profile == "rwkv-lightning-native":
            rendered = "".join(
                f"{str(item.get('role') or 'user').title()}: "
                f"{str(item.get('content') or '')}\n"
                for item in request.messages
            )
            native_request = TextCompletionRequest(
                prompt=rendered,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                presence_penalty=request.presence_penalty,
                frequency_penalty=request.frequency_penalty,
                penalty_decay=request.penalty_decay,
                min_tokens=request.min_tokens,
                stop=request.stop,
                stop_token_ids=request.stop_token_ids,
                request_id=request.request_id,
                return_token_ids=request.return_token_ids,
            )
            payload = self._text_payload(native_request)
        else:
            payload = request.payload(self.model_name)
        data, latency_ms, attempts = self._request_json(
            "POST", "/chat/completions", payload=payload, generation=True
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

    def capabilities(self) -> RuntimeCapabilities:
        """Negotiate explicit RWKV extensions without inferring from caches.

        A server must expose `/capabilities` and affirm each state operation.
        OpenAI-compatible endpoints, cached tokens, or tool parser presence do
        not imply a resumable recurrent-state handle.
        """

        try:
            data, _, _ = self._request_json("GET", "/capabilities")
            return RuntimeCapabilities.from_mapping(
                data,
                source=self.settings.base_url + "/capabilities",
            )
        except Exception as exc:
            return RuntimeCapabilities(
                source="prompt_replay_fallback",
                error=f"{type(exc).__name__}: {exc}"[:500],
            )

    def close(self) -> None:
        self._main_session.close()
        session = getattr(self._thread_sessions, "session", None)
        if session is not None and session is not self._main_session:
            session.close()


__all__ = ["OpenAICompatibleRWKVClient"]
