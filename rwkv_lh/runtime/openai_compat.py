"""Structured OpenAI-compatible client for local and remote RWKV servers."""

from __future__ import annotations

import hashlib
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
from rwkv_lh.runtime.native_state import (
    NATIVE_STATE_PROTOCOL_VERSION,
    NativeStateCacheBinding,
    NativeStateCandidate,
    NativeStateSnapshot,
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
        if self.settings.backend_profile in {
            "vllm-rwkv-rapid",
            "vllm-rwkv-native",
        }:
            sampler_mode = (
                "native"
                if self.settings.backend_profile == "vllm-rwkv-native"
                else "rapid"
            )
            return self._attach_state_profile(
                request.payload(self.model_name, sampler_mode=sampler_mode)
            )
        unsupported: list[str] = []
        if request.min_tokens:
            unsupported.append("min_tokens")
        if request.stop_token_ids:
            unsupported.append("stop_token_ids")
        if request.return_token_ids:
            unsupported.append("return_token_ids")
        if request.seed is not None:
            unsupported.append("seed")
        if unsupported:
            raise ValueError(
                "rwkv-lightning-native does not support: "
                + ", ".join(unsupported)
            )
        return self._attach_state_profile(
            {
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
        )

    def _attach_state_profile(self, payload: dict[str, Any]) -> dict[str, Any]:
        profile_id = self.settings.state_profile_id
        if not profile_id:
            return payload
        if self.settings.state_profile_delivery == "process_attested":
            return payload
        if self.settings.backend_profile not in {
            "vllm-rwkv-rapid",
            "vllm-rwkv-native",
        }:
            raise ValueError("RWKV state profiles require a vllm-rwkv backend")
        payload["vllm_xargs"] = {
            "rwkv_state_profile": profile_id,
            "rwkv_state_profile_sha256": self.settings.state_profile_sha256,
        }
        return payload

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
        if not isinstance(content, str):
            raise RWKVProtocolError("response content must be a string")
        usage = TokenUsage.from_mapping(data.get("usage") if isinstance(data.get("usage"), Mapping) else {})
        metadata: dict[str, Any] = {"http_attempts": attempts}
        if isinstance(data.get("prompt_token_ids"), list):
            if any(
                not isinstance(item, int) or isinstance(item, bool) or item < 0
                for item in data["prompt_token_ids"]
            ):
                raise RWKVProtocolError("prompt_token_ids must be non-negative integers")
            metadata["prompt_token_ids"] = list(data["prompt_token_ids"])
        if isinstance(choice.get("token_ids"), list):
            if any(
                not isinstance(item, int) or isinstance(item, bool) or item < 0
                for item in choice["token_ids"]
            ):
                raise RWKVProtocolError("token_ids must be non-negative integers")
            metadata["token_ids"] = list(choice["token_ids"])
        return CompletionResponse(
            content=content,
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
            seed=sampling.seed if seed is None else seed,
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
                "seed": request.seed,
                "max_tokens": request.max_tokens,
                "state_profile_id": self.settings.state_profile_id,
                "state_profile_sha256": self.settings.state_profile_sha256,
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
                    "raw_output": response.content,
                    "raw_output_sha256": self._raw_output_sha256(response.content),
                    "raw_token_ids": list(response.metadata.get("token_ids") or []),
                    "response_id": response.response_id,
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
            seed=sampling.seed if seed is None else seed,
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
                seed=request.seed,
                return_token_ids=request.return_token_ids,
            )
            payload = self._text_payload(native_request)
        else:
            sampler_mode = (
                "native"
                if self.settings.backend_profile == "vllm-rwkv-native"
                else "rapid"
            )
            payload = request.payload(
                self.model_name,
                sampler_mode=sampler_mode,
            )
            payload = self._attach_state_profile(payload)
        data, latency_ms, attempts = self._request_json(
            "POST", "/chat/completions", payload=payload, generation=True
        )
        return self._completion_response(data, latency_ms, attempts)

    @staticmethod
    def _raw_output_sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def health(self) -> HealthStatus:
        started = time.perf_counter()
        try:
            data, latency_ms, _ = self._request_json("GET", "/models")
            models = tuple(
                str(item.get("id"))
                for item in data.get("data", [])
                if isinstance(item, Mapping) and item.get("id")
            )
            model_available = self.model_name in models
            return HealthStatus(
                available=model_available,
                endpoint=self.settings.base_url,
                model=self.model_name,
                models=models,
                latency_ms=latency_ms,
                error=(
                    "configured model is absent from /models: "
                    f"{self.model_name}"
                    if not model_available
                    else ""
                ),
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

    @staticmethod
    def _native_snapshot(
        value: Mapping[str, Any],
        *,
        expected_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot:
        raw = value.get("snapshot")
        selected = raw if isinstance(raw, Mapping) else value
        export_record = selected.get("export_record")
        if not isinstance(export_record, Mapping):
            raise RWKVProtocolError("native state response has no export record")
        snapshot = NativeStateSnapshot(
            state_ref=str(selected.get("state_ref") or ""),
            state_digest=str(selected.get("state_digest") or ""),
            export_record=dict(export_record),
            state_format_version=str(selected.get("state_format_version") or ""),
            server_build=str(selected.get("server_build") or ""),
            tokenizer_build=str(selected.get("tokenizer_build") or ""),
            cache_binding_digest=str(selected.get("cache_binding_digest") or ""),
            protocol_version=str(
                selected.get("protocol_version") or NATIVE_STATE_PROTOCOL_VERSION
            ),
        )
        if snapshot.cache_binding_digest != expected_binding.digest:
            raise RWKVProtocolError("native state response cache binding mismatch")
        return snapshot

    def _native_payload(
        self,
        cache_binding: NativeStateCacheBinding,
        **values: Any,
    ) -> dict[str, Any]:
        return self._attach_state_profile(
            {
                "schema_version": NATIVE_STATE_PROTOCOL_VERSION,
                "model": self.model_name,
                "cache_binding": cache_binding.to_dict(),
                **values,
            }
        )

    def state_create(
        self,
        *,
        lane_id: str,
        text: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot:
        data, _, _ = self._request_json(
            "POST",
            "/state/create",
            payload=self._native_payload(
                cache_binding,
                lane_id=str(lane_id),
                delta=str(text),
            ),
        )
        return self._native_snapshot(data, expected_binding=cache_binding)

    def state_append(
        self,
        *,
        parent_state_ref: str,
        lane_id: str,
        text: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot:
        data, _, _ = self._request_json(
            "POST",
            "/state/append",
            payload=self._native_payload(
                cache_binding,
                parent_state_ref=str(parent_state_ref),
                lane_id=str(lane_id),
                delta=str(text),
            ),
        )
        return self._native_snapshot(data, expected_binding=cache_binding)

    def state_fork(
        self,
        *,
        parent_state_ref: str,
        lane_id: str,
        text: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot:
        data, _, _ = self._request_json(
            "POST",
            "/state/fork",
            payload=self._native_payload(
                cache_binding,
                parent_state_ref=str(parent_state_ref),
                lane_id=str(lane_id),
                delta=str(text),
            ),
        )
        return self._native_snapshot(data, expected_binding=cache_binding)

    def state_generate(
        self,
        *,
        parent_state_ref: str,
        request_id: str,
        max_tokens: int,
        stop: Sequence[str],
        sampling: Mapping[str, Any],
        parent_cache_binding_digest: str,
    ) -> NativeStateCandidate:
        data, _, _ = self._request_json(
            "POST",
            "/state/generate",
            payload=self._attach_state_profile(
                {
                    "schema_version": NATIVE_STATE_PROTOCOL_VERSION,
                    "model": self.model_name,
                    "parent_state_ref": str(parent_state_ref),
                    "parent_cache_binding_digest": str(
                        parent_cache_binding_digest
                    ),
                    "request_id": str(request_id),
                    "max_tokens": max(1, int(max_tokens)),
                    "stop": [str(item) for item in stop],
                    "sampling": dict(sampling),
                }
            ),
            generation=True,
        )
        raw = data.get("candidate")
        selected = raw if isinstance(raw, Mapping) else data
        metadata = selected.get("metadata")
        candidate = NativeStateCandidate(
            state_ref=str(selected.get("state_ref") or ""),
            state_digest=str(selected.get("state_digest") or ""),
            content=str(selected.get("content") or ""),
            finish_reason=str(selected.get("finish_reason") or "stop"),
            metadata=dict(metadata) if isinstance(metadata, Mapping) else {},
            parent_state_digest=str(selected.get("parent_state_digest") or ""),
            parent_cache_binding_digest=str(
                selected.get("parent_cache_binding_digest") or ""
            ),
        )
        if candidate.parent_cache_binding_digest != parent_cache_binding_digest:
            raise RWKVProtocolError("native candidate parent cache binding mismatch")
        return candidate

    def state_commit(
        self,
        *,
        candidate_state_ref: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot:
        data, _, _ = self._request_json(
            "POST",
            "/state/commit",
            payload=self._native_payload(
                cache_binding,
                candidate_state_ref=str(candidate_state_ref),
            ),
        )
        return self._native_snapshot(data, expected_binding=cache_binding)

    def state_rollback(
        self,
        *,
        candidate_state_ref: str,
        parent_state_ref: str,
    ) -> None:
        self._request_json(
            "POST",
            "/state/rollback",
            payload={
                "schema_version": NATIVE_STATE_PROTOCOL_VERSION,
                "model": self.model_name,
                "candidate_state_ref": str(candidate_state_ref),
                "parent_state_ref": str(parent_state_ref),
            },
        )

    def state_import(
        self,
        *,
        export_record: Mapping[str, Any],
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot:
        data, _, _ = self._request_json(
            "POST",
            "/state/import",
            payload=self._native_payload(
                cache_binding,
                export_record=dict(export_record),
            ),
        )
        return self._native_snapshot(data, expected_binding=cache_binding)

    def close(self) -> None:
        self._main_session.close()
        session = getattr(self._thread_sessions, "session", None)
        if session is not None and session is not self._main_session:
            session.close()


__all__ = ["OpenAICompatibleRWKVClient"]
