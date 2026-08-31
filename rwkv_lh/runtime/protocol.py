"""Typed OpenAI-compatible request, response, and error contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


class RWKVRuntimeError(RuntimeError):
    """Base class for model-runtime failures."""


class RWKVTransportError(RWKVRuntimeError):
    """The server could not be reached or timed out."""


class RWKVOutcomeUnknownError(RWKVTransportError):
    """A generation may have completed, but its response was not received."""


class RWKVHTTPError(RWKVRuntimeError):
    """The server returned a non-success HTTP response."""

    def __init__(self, status_code: int, detail: str, *, retryable: bool = False):
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = int(status_code)
        self.detail = str(detail)
        self.retryable = bool(retryable)


class RWKVProtocolError(RWKVRuntimeError):
    """The server response did not satisfy the OpenAI-compatible contract."""


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "TokenUsage":
        raw = value if isinstance(value, Mapping) else {}
        prompt = int(raw.get("prompt_tokens", raw.get("input_tokens", 0)) or 0)
        completion = int(raw.get("completion_tokens", raw.get("output_tokens", 0)) or 0)
        total = int(raw.get("total_tokens") or prompt + completion)
        return cls(prompt, completion, total)

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(frozen=True)
class TextCompletionRequest:
    prompt: str
    max_tokens: int = 768
    temperature: float = 0.1
    top_p: float = 1.0
    top_k: int = 0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    penalty_decay: float = 0.996
    min_tokens: int = 0
    stop: tuple[str, ...] = ()
    stop_token_ids: tuple[int, ...] = ()
    request_id: str = ""
    seed: int | None = None
    add_special_tokens: bool = True
    return_token_ids: bool = False

    def payload(self, model: str, *, sampler_mode: str = "rapid") -> dict[str, Any]:
        if not self.prompt:
            raise ValueError("prompt must not be empty")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        _validate_vllm_sampling(self, sampler_mode=sampler_mode)
        payload: dict[str, Any] = {
            "model": model,
            "prompt": self.prompt,
            "max_tokens": int(self.max_tokens),
            "temperature": float(self.temperature),
            "top_p": float(self.top_p),
            "top_k": int(self.top_k),
            "presence_penalty": float(self.presence_penalty),
            "frequency_penalty": float(self.frequency_penalty),
            "penalty_decay": float(self.penalty_decay),
            "min_tokens": int(self.min_tokens),
            "add_special_tokens": bool(self.add_special_tokens),
            "stream": False,
        }
        if self.stop:
            payload["stop"] = list(self.stop)
        if self.stop_token_ids:
            payload["stop_token_ids"] = list(self.stop_token_ids)
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.seed is not None:
            payload["seed"] = int(self.seed)
        if self.return_token_ids:
            payload["return_token_ids"] = True
        return payload


@dataclass(frozen=True)
class ChatCompletionRequest:
    messages: tuple[dict[str, Any], ...]
    max_tokens: int = 768
    temperature: float = 0.1
    top_p: float = 1.0
    top_k: int = 0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    penalty_decay: float = 0.996
    min_tokens: int = 0
    stop: tuple[str, ...] = ()
    stop_token_ids: tuple[int, ...] = ()
    request_id: str = ""
    seed: int | None = None
    add_special_tokens: bool = False
    return_token_ids: bool = False

    def payload(self, model: str, *, sampler_mode: str = "rapid") -> dict[str, Any]:
        if not self.messages:
            raise ValueError("messages must not be empty")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        _validate_vllm_sampling(self, sampler_mode=sampler_mode)
        payload: dict[str, Any] = {
            "model": model,
            "messages": [dict(item) for item in self.messages],
            "max_tokens": int(self.max_tokens),
            "temperature": float(self.temperature),
            "top_p": float(self.top_p),
            "top_k": int(self.top_k),
            "presence_penalty": float(self.presence_penalty),
            "frequency_penalty": float(self.frequency_penalty),
            "penalty_decay": float(self.penalty_decay),
            "min_tokens": int(self.min_tokens),
            "add_special_tokens": bool(self.add_special_tokens),
            "stream": False,
        }
        if self.stop:
            payload["stop"] = list(self.stop)
        if self.stop_token_ids:
            payload["stop_token_ids"] = list(self.stop_token_ids)
        if self.request_id:
            payload["request_id"] = self.request_id
        if self.seed is not None:
            payload["seed"] = int(self.seed)
        if self.return_token_ids:
            payload["return_token_ids"] = True
        return payload


def _validate_vllm_sampling(
    request: TextCompletionRequest | ChatCompletionRequest,
    *,
    sampler_mode: str,
) -> None:
    if sampler_mode not in {"rapid", "native"}:
        raise ValueError("sampler_mode must be rapid or native")
    minimum_temperature = 1e-5 if sampler_mode == "rapid" else 0.0
    if not minimum_temperature <= request.temperature <= 2:
        raise ValueError(
            f"temperature must be between {minimum_temperature:g} and 2 "
            f"for vllm-rwkv {sampler_mode} sampling"
        )
    if request.seed is not None:
        if not isinstance(request.seed, int) or isinstance(request.seed, bool):
            raise ValueError("seed must be an integer or null")
        if sampler_mode == "rapid":
            raise ValueError("seed is unsupported by vllm-rwkv rapid sampling")
    if not 0 < request.top_p <= 1:
        raise ValueError("top_p must be in (0, 1]")
    if not isinstance(request.top_k, int) or request.top_k < 0:
        raise ValueError("top_k must be 0 (disabled) or a positive integer")
    if not -2 <= request.presence_penalty <= 2:
        raise ValueError("presence_penalty must be in [-2, 2]")
    if not -2 <= request.frequency_penalty <= 2:
        raise ValueError("frequency_penalty must be in [-2, 2]")
    if not 0 <= request.penalty_decay <= 1:
        raise ValueError("penalty_decay must be in [0, 1]")
    if request.min_tokens < 0 or request.min_tokens > request.max_tokens:
        raise ValueError("min_tokens must be between 0 and max_tokens")
    if any(not isinstance(token_id, int) or token_id < 0 for token_id in request.stop_token_ids):
        raise ValueError("stop_token_ids must contain non-negative integers")


@dataclass
class CompletionResponse:
    content: str
    role: str = "assistant"
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    response_id: str = ""
    model: str = ""
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthStatus:
    available: bool
    endpoint: str
    model: str
    models: tuple[str, ...] = ()
    latency_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "endpoint": self.endpoint,
            "model": self.model,
            "models": list(self.models),
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass(frozen=True)
class RuntimeCapabilities:
    """Server-declared capabilities; absence always means unsupported."""

    source: str = "local_fallback"
    prompt_replay: bool = True
    native_tool_calls_declared: bool = False
    recurrent_state_create: bool = False
    recurrent_state_resume: bool = False
    recurrent_state_fork: bool = False
    recurrent_state_commit: bool = False
    recurrent_state_rollback: bool = False
    recurrent_state_export: bool = False
    recurrent_state_import: bool = False
    error: str = ""

    @property
    def durable_recurrent_state(self) -> bool:
        return all(
            (
                self.recurrent_state_create,
                self.recurrent_state_resume,
                self.recurrent_state_fork,
                self.recurrent_state_commit,
                self.recurrent_state_rollback,
                self.recurrent_state_export,
                self.recurrent_state_import,
            )
        )

    @classmethod
    def from_mapping(
        cls,
        value: Mapping[str, Any],
        *,
        source: str,
    ) -> "RuntimeCapabilities":
        state = value.get("recurrent_state")
        raw_state = state if isinstance(state, Mapping) else {}
        tools = value.get("tools")
        raw_tools = tools if isinstance(tools, Mapping) else {}
        return cls(
            source=source,
            prompt_replay=True,
            native_tool_calls_declared=bool(raw_tools.get("native_tool_calls", False)),
            recurrent_state_create=bool(raw_state.get("create", False)),
            recurrent_state_resume=bool(raw_state.get("resume", False)),
            recurrent_state_fork=bool(raw_state.get("fork", False)),
            recurrent_state_commit=bool(raw_state.get("commit", False)),
            recurrent_state_rollback=bool(raw_state.get("rollback", False)),
            recurrent_state_export=bool(raw_state.get("export", False)),
            recurrent_state_import=bool(raw_state.get("import", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "prompt_replay": self.prompt_replay,
            "native_tool_calls_declared": self.native_tool_calls_declared,
            "recurrent_state": {
                "create": self.recurrent_state_create,
                "resume": self.recurrent_state_resume,
                "fork": self.recurrent_state_fork,
                "commit": self.recurrent_state_commit,
                "rollback": self.recurrent_state_rollback,
                "export": self.recurrent_state_export,
                "import": self.recurrent_state_import,
                "durable": self.durable_recurrent_state,
            },
            "error": self.error,
        }


def normalize_stop(value: Sequence[str] | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(item) for item in value if str(item))


def normalize_stop_token_ids(value: Sequence[int] | None) -> tuple[int, ...]:
    if not value:
        return ()
    normalized = tuple(value)
    if any(not isinstance(token_id, int) or token_id < 0 for token_id in normalized):
        raise ValueError("stop_token_ids must contain non-negative integers")
    return normalized


__all__ = [
    "ChatCompletionRequest",
    "CompletionResponse",
    "HealthStatus",
    "RWKVHTTPError",
    "RWKVOutcomeUnknownError",
    "RWKVProtocolError",
    "RWKVRuntimeError",
    "RWKVTransportError",
    "RuntimeCapabilities",
    "TextCompletionRequest",
    "TokenUsage",
    "normalize_stop",
    "normalize_stop_token_ids",
]
