"""Typed OpenAI-compatible request, response, and error contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


class RWKVRuntimeError(RuntimeError):
    """Base class for model-runtime failures."""


class RWKVTransportError(RWKVRuntimeError):
    """The server could not be reached or timed out."""


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
    seed: int | None = None
    stop: tuple[str, ...] = ()

    def payload(self, model: str) -> dict[str, Any]:
        if not self.prompt:
            raise ValueError("prompt must not be empty")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        payload: dict[str, Any] = {
            "model": model,
            "prompt": self.prompt,
            "max_tokens": int(self.max_tokens),
            "temperature": float(self.temperature),
            "stream": False,
        }
        if self.seed is not None:
            payload["seed"] = int(self.seed)
        if self.stop:
            payload["stop"] = list(self.stop)
        return payload


@dataclass(frozen=True)
class ChatCompletionRequest:
    messages: tuple[dict[str, Any], ...]
    max_tokens: int = 768
    temperature: float = 0.1
    seed: int | None = None
    stop: tuple[str, ...] = ()

    def payload(self, model: str) -> dict[str, Any]:
        if not self.messages:
            raise ValueError("messages must not be empty")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        payload: dict[str, Any] = {
            "model": model,
            "messages": [dict(item) for item in self.messages],
            "max_tokens": max(1, int(self.max_tokens)),
            "temperature": float(self.temperature),
            "stream": False,
        }
        if self.seed is not None:
            payload["seed"] = int(self.seed)
        if self.stop:
            payload["stop"] = list(self.stop)
        return payload


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


def normalize_stop(value: Sequence[str] | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(str(item) for item in value if str(item))


__all__ = [
    "ChatCompletionRequest",
    "CompletionResponse",
    "HealthStatus",
    "RWKVHTTPError",
    "RWKVProtocolError",
    "RWKVRuntimeError",
    "RWKVTransportError",
    "TextCompletionRequest",
    "TokenUsage",
    "normalize_stop",
]
