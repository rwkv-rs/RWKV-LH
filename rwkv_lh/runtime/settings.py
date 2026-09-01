"""Deployment-local settings for the OpenAI-compatible RWKV runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import urlparse

from rwkv_lh.runtime.role_config import (
    role_bool,
    role_env,
    role_float,
    role_int,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env.local"
_STATE_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def load_local_env(
    path: str | Path = DEFAULT_ENV_FILE,
    *,
    allowed_prefixes: tuple[str, ...] | None = None,
) -> None:
    """Load an ignored env file without overriding process-level settings.

    ``allowed_prefixes`` keeps component-specific env files from leaking
    unrelated settings into a long-lived process.  A ``None`` value preserves
    the product runtime's existing behavior of loading the complete local
    deployment file.
    """

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
        if allowed_prefixes is not None and not key.startswith(allowed_prefixes):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class RuntimeSettings:
    base_url: str
    api_key: str
    model: str
    model_sha256: str = ""
    backend_profile: str = "vllm-rwkv-native"
    cf_access_client_id: str = ""
    cf_access_client_secret: str = ""
    proxy_url: str = ""
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 300.0
    retry_attempts: int = 2
    retry_backoff_seconds: float = 0.5
    default_temperature: float = 0.1
    default_top_p: float = 1.0
    default_top_k: int = 0
    default_presence_penalty: float = 0.0
    default_frequency_penalty: float = 0.0
    default_penalty_decay: float = 0.996
    max_model_len: int = 16384
    context_safety_margin: int = 32
    bos_token_count: int = 1
    return_token_ids: bool = False
    trust_environment_proxies: bool = False
    verify_tls: bool = True
    tool_disclosure_mode: str = "progressive"
    state_transport: str = "native_required"
    state_profile_id: str = ""
    state_profile_sha256: str = ""
    state_profile_delivery: str = "request"

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        load_local_env()
        settings = cls(
            base_url=role_env(
                "executor",
                "base_url",
                legacy="RWKV_BASE_URL",
                default="http://127.0.0.1:29613/v1",
            ).rstrip("/"),
            api_key=role_env("executor", "api_key", legacy="RWKV_API_KEY"),
            model=role_env("executor", "model", legacy="RWKV_MODEL"),
            model_sha256=role_env(
                "executor", "model_sha256", legacy="RWKV_MODEL_SHA256"
            ).casefold(),
            backend_profile=role_env(
                "executor",
                "backend_profile",
                legacy="RWKV_BACKEND_PROFILE",
                default="vllm-rwkv-native",
            ),
            cf_access_client_id=role_env(
                "executor",
                "cf_access_client_id",
                legacy="RWKV_CF_ACCESS_CLIENT_ID",
            ),
            cf_access_client_secret=role_env(
                "executor",
                "cf_access_client_secret",
                legacy="RWKV_CF_ACCESS_CLIENT_SECRET",
            ),
            proxy_url=role_env(
                "executor", "proxy_url", legacy="RWKV_PROXY_URL"
            ),
            connect_timeout_seconds=role_float(
                "executor", "connect_timeout", legacy="RWKV_CONNECT_TIMEOUT", default=10.0
            ),
            read_timeout_seconds=role_float(
                "executor", "read_timeout", legacy="RWKV_READ_TIMEOUT", default=300.0
            ),
            retry_attempts=role_int(
                "executor", "retry_attempts", legacy="RWKV_RETRY_ATTEMPTS", default=2
            ),
            retry_backoff_seconds=role_float(
                "executor", "retry_backoff", legacy="RWKV_RETRY_BACKOFF", default=0.5
            ),
            default_temperature=role_float(
                "executor",
                "default_temperature",
                legacy="RWKV_DEFAULT_TEMPERATURE",
                default=0.1,
            ),
            default_top_p=role_float(
                "executor", "default_top_p", legacy="RWKV_DEFAULT_TOP_P", default=1.0
            ),
            default_top_k=role_int(
                "executor", "default_top_k", legacy="RWKV_DEFAULT_TOP_K", default=0
            ),
            default_presence_penalty=role_float(
                "executor",
                "default_presence_penalty",
                legacy="RWKV_DEFAULT_PRESENCE_PENALTY",
                default=0.0,
            ),
            default_frequency_penalty=role_float(
                "executor",
                "default_frequency_penalty",
                legacy="RWKV_DEFAULT_FREQUENCY_PENALTY",
                default=0.0,
            ),
            default_penalty_decay=role_float(
                "executor",
                "default_penalty_decay",
                legacy="RWKV_DEFAULT_PENALTY_DECAY",
                default=0.996,
            ),
            max_model_len=role_int(
                "executor", "max_model_len", legacy="RWKV_MAX_MODEL_LEN", default=16384
            ),
            context_safety_margin=role_int(
                "executor",
                "context_safety_margin",
                legacy="RWKV_CONTEXT_SAFETY_MARGIN",
                default=32,
            ),
            bos_token_count=role_int(
                "executor", "bos_token_count", legacy="RWKV_BOS_TOKEN_COUNT", default=1
            ),
            return_token_ids=role_bool(
                "executor", "return_token_ids", legacy="RWKV_RETURN_TOKEN_IDS", default=True
            ),
            trust_environment_proxies=role_bool(
                "executor", "trust_env", legacy="RWKV_TRUST_ENV", default=False
            ),
            verify_tls=role_bool(
                "executor", "verify_tls", legacy="RWKV_VERIFY_TLS", default=True
            ),
            tool_disclosure_mode=role_env(
                "executor",
                "tool_disclosure_mode",
                legacy="RWKV_TOOL_DISCLOSURE_MODE",
                default="progressive",
            ).casefold(),
            state_transport=role_env(
                "executor",
                "state_transport",
                legacy="RWKV_STATE_TRANSPORT",
                default="native_required",
            ).casefold(),
            state_profile_id=role_env(
                "executor", "state_profile_id", legacy="RWKV_STATE_PROFILE_ID"
            ),
            state_profile_sha256=role_env(
                "executor",
                "state_profile_sha256",
                legacy="RWKV_STATE_PROFILE_SHA256",
            ).casefold(),
            state_profile_delivery=role_env(
                "executor",
                "state_profile_delivery",
                legacy="RWKV_STATE_PROFILE_DELIVERY",
                default="request",
            ).casefold(),
        )
        settings.validate()
        return settings

    @classmethod
    def for_role(
        cls,
        role: str,
        *,
        fallback: "RuntimeSettings",
    ) -> "RuntimeSettings":
        """Bind one replaceable RWKV role without inheriting another role's State.

        Missing role fields inherit deployment properties from ``fallback``.  A
        role-specific State profile is opt-in and never inherited.  The caller
        must still construct a distinct :class:`ModelSession`; this method shares
        configuration defaults, never a recurrent State or checkpoint.
        """

        normalized = str(role or "").strip().casefold()
        if not normalized or not re.fullmatch(r"[a-z][a-z0-9_]*", normalized):
            raise ValueError("RWKV role must be a lowercase identifier")
        prefix = f"RWKV_LH_{normalized.upper()}_"
        load_local_env(allowed_prefixes=(prefix,))

        def text(suffix: str, field: str) -> str:
            return role_env(
                normalized,
                suffix,
                default=str(getattr(fallback, field)),
            )

        settings = cls(
            base_url=text("base_url", "base_url").rstrip("/"),
            api_key=text("api_key", "api_key"),
            model=text("model", "model"),
            model_sha256=text("model_sha256", "model_sha256").casefold(),
            backend_profile=text("backend_profile", "backend_profile"),
            cf_access_client_id=text(
                "cf_access_client_id", "cf_access_client_id"
            ),
            cf_access_client_secret=text(
                "cf_access_client_secret", "cf_access_client_secret"
            ),
            proxy_url=text("proxy_url", "proxy_url"),
            connect_timeout_seconds=role_float(
                normalized,
                "connect_timeout",
                default=fallback.connect_timeout_seconds,
            ),
            read_timeout_seconds=role_float(
                normalized,
                "read_timeout",
                default=fallback.read_timeout_seconds,
            ),
            retry_attempts=role_int(
                normalized,
                "retry_attempts",
                default=fallback.retry_attempts,
            ),
            retry_backoff_seconds=role_float(
                normalized,
                "retry_backoff",
                default=fallback.retry_backoff_seconds,
            ),
            default_temperature=role_float(
                normalized,
                "default_temperature",
                default=fallback.default_temperature,
            ),
            default_top_p=role_float(
                normalized,
                "default_top_p",
                default=fallback.default_top_p,
            ),
            default_top_k=role_int(
                normalized,
                "default_top_k",
                default=fallback.default_top_k,
            ),
            default_presence_penalty=role_float(
                normalized,
                "default_presence_penalty",
                default=fallback.default_presence_penalty,
            ),
            default_frequency_penalty=role_float(
                normalized,
                "default_frequency_penalty",
                default=fallback.default_frequency_penalty,
            ),
            default_penalty_decay=role_float(
                normalized,
                "default_penalty_decay",
                default=fallback.default_penalty_decay,
            ),
            max_model_len=role_int(
                normalized,
                "max_model_len",
                default=fallback.max_model_len,
            ),
            context_safety_margin=role_int(
                normalized,
                "context_safety_margin",
                default=fallback.context_safety_margin,
            ),
            bos_token_count=role_int(
                normalized,
                "bos_token_count",
                default=fallback.bos_token_count,
            ),
            return_token_ids=role_bool(
                normalized,
                "return_token_ids",
                default=fallback.return_token_ids,
            ),
            trust_environment_proxies=role_bool(
                normalized,
                "trust_env",
                default=fallback.trust_environment_proxies,
            ),
            verify_tls=role_bool(
                normalized,
                "verify_tls",
                default=fallback.verify_tls,
            ),
            tool_disclosure_mode=text(
                "tool_disclosure_mode", "tool_disclosure_mode"
            ).casefold(),
            state_transport=text("state_transport", "state_transport").casefold(),
            state_profile_id=role_env(normalized, "state_profile_id"),
            state_profile_sha256=role_env(
                normalized,
                "state_profile_sha256",
            ).casefold(),
            state_profile_delivery=role_env(
                normalized,
                "state_profile_delivery",
                default="request",
            ).casefold(),
        )
        settings.validate(role=normalized)
        return settings

    def validate(self, *, role: str = "executor") -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RWKV_BASE_URL must be an absolute HTTP(S) URL")
        if not self.model:
            raise ValueError(f"RWKV_LH_{role.upper()}_MODEL must not be empty")
        if self.model_sha256 and not _SHA256_PATTERN.fullmatch(self.model_sha256):
            raise ValueError("RWKV_MODEL_SHA256 must be lowercase SHA-256")
        if self.tool_disclosure_mode not in {"full", "progressive"}:
            raise ValueError(
                "RWKV_TOOL_DISCLOSURE_MODE must be full or progressive"
            )
        if self.state_transport not in {
            "prompt_replay",
            "auto",
            "native_required",
        }:
            raise ValueError(
                "RWKV_STATE_TRANSPORT must be prompt_replay, auto, or native_required"
            )
        if bool(self.state_profile_id) != bool(self.state_profile_sha256):
            raise ValueError(
                "RWKV_STATE_PROFILE_ID and RWKV_STATE_PROFILE_SHA256 "
                "must be configured together"
            )
        if self.state_profile_id and not _STATE_PROFILE_ID_PATTERN.fullmatch(
            self.state_profile_id
        ):
            raise ValueError("RWKV_STATE_PROFILE_ID is invalid")
        if self.state_profile_sha256 and not _SHA256_PATTERN.fullmatch(
            self.state_profile_sha256
        ):
            raise ValueError("RWKV_STATE_PROFILE_SHA256 must be lowercase SHA-256")
        if self.state_profile_delivery not in {"request", "process_attested"}:
            raise ValueError(
                "RWKV_STATE_PROFILE_DELIVERY must be request or process_attested"
            )
        if self.state_profile_delivery == "process_attested" and not self.state_profile_id:
            raise ValueError(
                "process_attested state delivery requires an explicit profile identity"
            )
        if self.backend_profile not in {
            "vllm-rwkv-rapid",
            "vllm-rwkv-native",
            "rwkv-lightning-native",
        }:
            raise ValueError(
                "RWKV_BACKEND_PROFILE must be vllm-rwkv-rapid, "
                "vllm-rwkv-native, or rwkv-lightning-native"
            )
        if bool(self.cf_access_client_id) != bool(self.cf_access_client_secret):
            raise ValueError(
                "RWKV_CF_ACCESS_CLIENT_ID and RWKV_CF_ACCESS_CLIENT_SECRET "
                "must be configured together"
            )
        if self.proxy_url:
            proxy = urlparse(self.proxy_url)
            if proxy.scheme not in {"http", "https"} or not proxy.netloc:
                raise ValueError("RWKV_PROXY_URL must be an absolute HTTP(S) URL")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("RWKV timeouts must be positive")
        if self.retry_attempts < 1:
            raise ValueError("RWKV_RETRY_ATTEMPTS must be at least 1")
        minimum_temperature = (
            0.0 if self.backend_profile == "vllm-rwkv-native" else 1e-5
        )
        if not minimum_temperature <= self.default_temperature <= 2:
            raise ValueError(
                "RWKV_DEFAULT_TEMPERATURE must be between "
                f"{minimum_temperature:g} and 2 for {self.backend_profile}"
            )
        if not 0 < self.default_top_p <= 1:
            raise ValueError("RWKV_DEFAULT_TOP_P must be in (0, 1]")
        if self.default_top_k < 0:
            raise ValueError("RWKV_DEFAULT_TOP_K must be 0 (disabled) or positive")
        if not -2 <= self.default_presence_penalty <= 2:
            raise ValueError("RWKV_DEFAULT_PRESENCE_PENALTY must be in [-2, 2]")
        if not -2 <= self.default_frequency_penalty <= 2:
            raise ValueError("RWKV_DEFAULT_FREQUENCY_PENALTY must be in [-2, 2]")
        if not 0 <= self.default_penalty_decay <= 1:
            raise ValueError("RWKV_DEFAULT_PENALTY_DECAY must be in [0, 1]")
        if self.max_model_len < 2:
            raise ValueError("RWKV_MAX_MODEL_LEN must be at least 2")
        if self.context_safety_margin < 0 or self.bos_token_count < 0:
            raise ValueError("RWKV context reserves must not be negative")
        if self.context_safety_margin + self.bos_token_count >= self.max_model_len:
            raise ValueError("RWKV context reserves leave no usable model context")

    def max_prompt_tokens(self, max_output_tokens: int) -> int:
        """Return the largest safe locally-counted prompt for one request."""

        output = max(1, int(max_output_tokens))
        available = (
            self.max_model_len
            - output
            - self.context_safety_margin
            - self.bos_token_count
        )
        if available < 1:
            raise ValueError(
                f"max_output_tokens={output} leaves no prompt space in "
                f"max_model_len={self.max_model_len}"
            )
        return available


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
