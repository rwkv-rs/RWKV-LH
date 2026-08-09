"""Deployment-local settings for the OpenAI-compatible RWKV runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env.local"


def load_local_env(path: str | Path = DEFAULT_ENV_FILE) -> None:
    """Load an ignored env file without overriding process-level settings."""

    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _bool(name: str, default: bool) -> bool:
    value = str(os.environ.get(name, str(default))).strip().casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


@dataclass(frozen=True)
class RuntimeSettings:
    base_url: str
    api_key: str
    model: str
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 300.0
    retry_attempts: int = 2
    retry_backoff_seconds: float = 0.5
    default_temperature: float = 0.1
    trust_environment_proxies: bool = False
    verify_tls: bool = True

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        load_local_env()
        settings = cls(
            base_url=os.environ.get("RWKV_BASE_URL", "http://127.0.0.1:29613/v1").rstrip("/"),
            api_key=os.environ.get("RWKV_API_KEY", ""),
            model=os.environ.get(
                "RWKV_MODEL",
                "rwkv7-g1i-13.3b-20260805-ctx16384",
            ).strip(),
            connect_timeout_seconds=_float("RWKV_CONNECT_TIMEOUT", 10.0),
            read_timeout_seconds=_float("RWKV_READ_TIMEOUT", 300.0),
            retry_attempts=_int("RWKV_RETRY_ATTEMPTS", 2),
            retry_backoff_seconds=_float("RWKV_RETRY_BACKOFF", 0.5),
            default_temperature=_float("RWKV_DEFAULT_TEMPERATURE", 0.1),
            trust_environment_proxies=_bool("RWKV_TRUST_ENV", False),
            verify_tls=_bool("RWKV_VERIFY_TLS", True),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RWKV_BASE_URL must be an absolute HTTP(S) URL")
        if not self.model:
            raise ValueError("RWKV_MODEL must not be empty")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("RWKV timeouts must be positive")
        if self.retry_attempts < 1:
            raise ValueError("RWKV_RETRY_ATTEMPTS must be at least 1")
        if not 0 <= self.default_temperature <= 2:
            raise ValueError("RWKV_DEFAULT_TEMPERATURE must be between 0 and 2")


@lru_cache(maxsize=1)
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings.from_env()


def reset_runtime_settings() -> None:
    get_runtime_settings.cache_clear()


__all__ = [
    "DEFAULT_ENV_FILE",
    "PROJECT_ROOT",
    "RuntimeSettings",
    "get_runtime_settings",
    "load_local_env",
    "reset_runtime_settings",
]
