"""Deployment-local settings for the OpenAI-compatible RWKV runtime."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import urlparse


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
    state_transport: str = "prompt_replay"
    state_profile_id: str = ""
    state_profile_sha256: str = ""
    state_profile_delivery: str = "request"

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
            model_sha256=os.environ.get("RWKV_MODEL_SHA256", "").strip().casefold(),
            backend_profile=os.environ.get(
                "RWKV_BACKEND_PROFILE",
                "vllm-rwkv-native",
            ).strip(),
            cf_access_client_id=os.environ.get(
                "RWKV_CF_ACCESS_CLIENT_ID",
                "",
            ).strip(),
            cf_access_client_secret=os.environ.get(
                "RWKV_CF_ACCESS_CLIENT_SECRET",
                "",
            ).strip(),
            proxy_url=os.environ.get("RWKV_PROXY_URL", "").strip(),
            connect_timeout_seconds=_float("RWKV_CONNECT_TIMEOUT", 10.0),
            read_timeout_seconds=_float("RWKV_READ_TIMEOUT", 300.0),
            retry_attempts=_int("RWKV_RETRY_ATTEMPTS", 2),
            retry_backoff_seconds=_float("RWKV_RETRY_BACKOFF", 0.5),
            default_temperature=_float("RWKV_DEFAULT_TEMPERATURE", 0.1),
            default_top_p=_float("RWKV_DEFAULT_TOP_P", 1.0),
            default_top_k=_int("RWKV_DEFAULT_TOP_K", 0),
            default_presence_penalty=_float("RWKV_DEFAULT_PRESENCE_PENALTY", 0.0),
            default_frequency_penalty=_float("RWKV_DEFAULT_FREQUENCY_PENALTY", 0.0),
            default_penalty_decay=_float("RWKV_DEFAULT_PENALTY_DECAY", 0.996),
            max_model_len=_int("RWKV_MAX_MODEL_LEN", 16384),
            context_safety_margin=_int("RWKV_CONTEXT_SAFETY_MARGIN", 32),
            bos_token_count=_int("RWKV_BOS_TOKEN_COUNT", 1),
            return_token_ids=_bool("RWKV_RETURN_TOKEN_IDS", True),
            trust_environment_proxies=_bool("RWKV_TRUST_ENV", False),
            verify_tls=_bool("RWKV_VERIFY_TLS", True),
            tool_disclosure_mode=os.environ.get(
                "RWKV_TOOL_DISCLOSURE_MODE",
                "progressive",
            ).strip().casefold(),
            state_transport=os.environ.get(
                "RWKV_STATE_TRANSPORT",
                "prompt_replay",
            ).strip().casefold(),
            state_profile_id=os.environ.get(
                "RWKV_STATE_PROFILE_ID",
                "",
            ).strip(),
            state_profile_sha256=os.environ.get(
                "RWKV_STATE_PROFILE_SHA256",
                "",
            ).strip().casefold(),
            state_profile_delivery=os.environ.get(
                "RWKV_STATE_PROFILE_DELIVERY",
                "request",
            ).strip().casefold(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RWKV_BASE_URL must be an absolute HTTP(S) URL")
        if not self.model:
            raise ValueError("RWKV_MODEL must not be empty")
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
