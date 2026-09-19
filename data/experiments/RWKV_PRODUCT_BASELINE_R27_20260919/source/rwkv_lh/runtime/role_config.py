"""Small, fail-closed environment binding for replaceable model roles."""

from __future__ import annotations

import os


def role_env_name(role: str, suffix: str) -> str:
    return f"RWKV_LH_{role.strip().upper()}_{suffix.strip().upper()}"


def role_env(
    role: str,
    suffix: str,
    *,
    legacy: str = "",
    default: str = "",
) -> str:
    """Resolve one role setting without silently mixing old and new bindings."""

    canonical = role_env_name(role, suffix)
    canonical_present = canonical in os.environ
    legacy_present = bool(legacy) and legacy in os.environ
    canonical_value = os.environ.get(canonical, "").strip()
    legacy_value = os.environ.get(legacy, "").strip() if legacy else ""
    if canonical_present and legacy_present and canonical_value != legacy_value:
        raise ValueError(
            f"conflicting role settings: {canonical} and {legacy} must match"
        )
    if canonical_present:
        return canonical_value
    if legacy_present:
        return legacy_value
    return str(default).strip()


def role_float(
    role: str,
    suffix: str,
    *,
    legacy: str = "",
    default: float,
) -> float:
    name = role_env_name(role, suffix)
    value = role_env(role, suffix, legacy=legacy, default=str(default))
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc


def role_int(
    role: str,
    suffix: str,
    *,
    legacy: str = "",
    default: int,
) -> int:
    name = role_env_name(role, suffix)
    value = role_env(role, suffix, legacy=legacy, default=str(default))
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be an integer") from exc


def role_bool(
    role: str,
    suffix: str,
    *,
    legacy: str = "",
    default: bool,
) -> bool:
    name = role_env_name(role, suffix)
    value = role_env(
        role,
        suffix,
        legacy=legacy,
        default=str(default),
    ).casefold()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


__all__ = [
    "role_bool",
    "role_env",
    "role_env_name",
    "role_float",
    "role_int",
]
