"""Fail-closed RWKV7 initial-state profiles for vLLM-RWKV.

This module deliberately contains no request generation or output processing.
It only validates a pinned manifest, preloads immutable WKV tensors, and
resolves an explicitly pinned profile identity for each request.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import torch


RWKV7_STATE_PROFILE_MANIFEST_SCHEMA = "vllm.rwkv7-state-profiles.v1"
RWKV7_STATE_PROFILE_XARG = "rwkv_state_profile"
RWKV7_STATE_PROFILE_SHA256_XARG = "rwkv_state_profile_sha256"
RWKV7_ZERO_STATE_PROFILE = "zero"
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class RWKV7InitialStateProfile:
    profile_id: str
    state_sha256: str
    wkv_state: torch.Tensor | None


class RWKV7InitialStateProfiles:
    """Immutable initial WKV states selected by registered request identities."""

    def __init__(
        self,
        profiles: dict[str, RWKV7InitialStateProfile],
        default_profile_id: str,
        *,
        manifest_sha256: str | None = None,
        requires_explicit_request_profile: bool = False,
    ) -> None:
        self._profiles = dict(profiles)
        self.default_profile_id = default_profile_id
        self.manifest_sha256 = manifest_sha256
        self.requires_explicit_request_profile = requires_explicit_request_profile
        if default_profile_id not in self._profiles:
            raise ValueError("RWKV7 default state profile is not registered")

    @classmethod
    def zero_only(cls) -> "RWKV7InitialStateProfiles":
        return cls(
            {
                RWKV7_ZERO_STATE_PROFILE: RWKV7InitialStateProfile(
                    profile_id=RWKV7_ZERO_STATE_PROFILE,
                    state_sha256="0" * 64,
                    wkv_state=None,
                )
            },
            RWKV7_ZERO_STATE_PROFILE,
        )

    @classmethod
    def load(
        cls,
        manifest_path: str,
        manifest_sha256: str | None,
        *,
        model_artifact: str,
        model_revision: str,
        total_num_layers: int,
        total_num_heads: int,
        layer_offset: int,
        num_layers: int,
        tp_size: int,
        tp_rank: int,
        num_heads: int,
        head_size: int,
        device: torch.device,
        dtype: torch.dtype,
    ) -> "RWKV7InitialStateProfiles":
        path = Path(manifest_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(
                f"RWKV7 state-profile manifest does not exist: {path}"
            )
        expected_manifest_sha256 = str(manifest_sha256 or "").lower()
        if not _SHA256_PATTERN.fullmatch(expected_manifest_sha256):
            raise ValueError(
                "VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256 must pin the manifest"
            )
        actual_manifest_sha256 = sha256_file(path)
        if actual_manifest_sha256 != expected_manifest_sha256:
            raise ValueError(
                "RWKV7 state-profile manifest SHA-256 mismatch: "
                f"expected {expected_manifest_sha256}, got {actual_manifest_sha256}"
            )

        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise TypeError("RWKV7 state-profile manifest must be an object")
        if manifest.get("schema_version") != RWKV7_STATE_PROFILE_MANIFEST_SCHEMA:
            raise ValueError("unsupported RWKV7 state-profile manifest schema")
        if manifest.get("model_artifact") != model_artifact:
            raise ValueError("RWKV7 state-profile model artifact mismatch")
        if manifest.get("model_revision") != model_revision:
            raise ValueError("RWKV7 state-profile model revision mismatch")

        entries = manifest.get("profiles")
        if not isinstance(entries, list) or not entries:
            raise ValueError("RWKV7 state-profile manifest requires profiles")
        profiles = cls.zero_only()._profiles
        expected_keys = {
            f"blocks.{layer}.att.time_state" for layer in range(total_num_layers)
        }
        for entry in entries:
            if not isinstance(entry, dict):
                raise TypeError("RWKV7 state-profile entries must be objects")
            profile_id = entry.get("id")
            if not isinstance(profile_id, str) or not _PROFILE_ID_PATTERN.fullmatch(
                profile_id
            ):
                raise ValueError("RWKV7 state-profile ID is invalid")
            if profile_id == RWKV7_ZERO_STATE_PROFILE or profile_id in profiles:
                raise ValueError(f"duplicate RWKV7 state-profile ID: {profile_id}")
            if entry.get("format") != "rwkv-peft-time-state.v1":
                raise ValueError("unsupported RWKV7 state-profile format")
            state_sha256 = str(entry.get("sha256") or "").lower()
            if not _SHA256_PATTERN.fullmatch(state_sha256):
                raise ValueError(f"RWKV7 state-profile {profile_id!r} lacks SHA-256")
            state_path_value = entry.get("path")
            if not isinstance(state_path_value, str) or not state_path_value:
                raise ValueError(f"RWKV7 state-profile {profile_id!r} lacks path")
            state_path = Path(state_path_value)
            if not state_path.is_absolute():
                state_path = path.parent / state_path
            state_path = state_path.resolve()
            if not state_path.is_file():
                raise FileNotFoundError(
                    f"RWKV7 state-profile does not exist: {state_path}"
                )
            actual_state_sha256 = sha256_file(state_path)
            if actual_state_sha256 != state_sha256:
                raise ValueError(f"RWKV7 state-profile {profile_id!r} SHA-256 mismatch")

            checkpoint = torch.load(
                state_path,
                map_location="cpu",
                weights_only=True,
            )
            if not isinstance(checkpoint, dict) or set(checkpoint) != expected_keys:
                raise ValueError(f"RWKV7 state-profile {profile_id!r} key set mismatch")
            layer_tensors: list[torch.Tensor] = []
            for global_layer in range(layer_offset, layer_offset + num_layers):
                key = f"blocks.{global_layer}.att.time_state"
                value = checkpoint[key]
                if not isinstance(value, torch.Tensor):
                    raise TypeError(
                        f"RWKV7 state-profile {profile_id!r} value is not a tensor"
                    )
                expected_shape = (total_num_heads, head_size, head_size)
                if tuple(value.shape) != expected_shape:
                    raise ValueError(
                        f"RWKV7 state-profile {profile_id!r} shape mismatch for {key}"
                    )
                if value.dtype != torch.bfloat16:
                    raise ValueError(
                        f"RWKV7 state-profile {profile_id!r} dtype mismatch for {key}"
                    )
                if (
                    not torch.isfinite(value).all().item()
                    or not torch.count_nonzero(value).item()
                ):
                    raise ValueError(
                        f"RWKV7 state-profile {profile_id!r} has invalid values in {key}"
                    )
                layer_tensors.append(value.detach())
            initial = torch.stack(layer_tensors, dim=0)
            if tp_size <= 0 or not 0 <= tp_rank < tp_size:
                raise ValueError("RWKV7 state-profile TP identity is invalid")
            if initial.shape[1] % tp_size:
                raise ValueError("RWKV7 state-profile heads are not TP divisible")
            heads_per_rank = initial.shape[1] // tp_size
            initial = initial.narrow(1, tp_rank * heads_per_rank, heads_per_rank)
            expected_runtime_shape = (
                num_layers,
                num_heads,
                head_size,
                head_size,
            )
            if tuple(initial.shape) != expected_runtime_shape:
                raise ValueError(
                    f"RWKV7 state-profile {profile_id!r} runtime shape mismatch"
                )
            profiles[profile_id] = RWKV7InitialStateProfile(
                profile_id=profile_id,
                state_sha256=state_sha256,
                wkv_state=initial.contiguous().to(device=device, dtype=dtype),
            )

        default_profile_id = manifest.get("default_profile", RWKV7_ZERO_STATE_PROFILE)
        if not isinstance(default_profile_id, str):
            raise TypeError("RWKV7 default state-profile ID must be a string")
        if default_profile_id != RWKV7_ZERO_STATE_PROFILE:
            raise ValueError("RWKV7 state-profile manifest default must be zero")
        return cls(
            profiles,
            default_profile_id,
            manifest_sha256=actual_manifest_sha256,
            requires_explicit_request_profile=True,
        )

    def resolve(self, profile_id: str | None) -> RWKV7InitialStateProfile:
        resolved_id = profile_id or self.default_profile_id
        profile = self._profiles.get(resolved_id)
        if profile is None:
            raise ValueError(f"unknown RWKV7 state-profile ID: {resolved_id!r}")
        return profile

    def identities(self) -> dict[str, str]:
        return {
            profile_id: profile.state_sha256
            for profile_id, profile in sorted(self._profiles.items())
        }


def resolve_request_profile(
    profiles: RWKV7InitialStateProfiles,
    sampling_params: object | None,
) -> RWKV7InitialStateProfile:
    """Resolve a request profile before the caller allocates recurrent state."""

    requested_profile_id = None
    requested_profile_sha256 = None
    extra_args = (
        getattr(sampling_params, "extra_args", None)
        if sampling_params is not None
        else None
    )
    if extra_args is not None:
        if not isinstance(extra_args, dict):
            raise TypeError("RWKV7 sampling extra_args must be a dictionary")
        requested_profile_id = extra_args.get(RWKV7_STATE_PROFILE_XARG)
        requested_profile_sha256 = extra_args.get(
            RWKV7_STATE_PROFILE_SHA256_XARG
        )
        if requested_profile_id is not None and not isinstance(
            requested_profile_id, str
        ):
            raise TypeError("RWKV7 state-profile request value must be a string")
        if requested_profile_sha256 is not None and not isinstance(
            requested_profile_sha256, str
        ):
            raise TypeError("RWKV7 state-profile SHA-256 must be a string")
    if bool(requested_profile_id) != bool(requested_profile_sha256):
        raise ValueError("RWKV7 request state-profile ID and SHA-256 are both required")
    if profiles.requires_explicit_request_profile and not requested_profile_id:
        raise ValueError(
            "RWKV7 request must explicitly select a registered state-profile pair"
        )
    profile = profiles.resolve(requested_profile_id)
    if (
        requested_profile_sha256 is not None
        and requested_profile_sha256 != profile.state_sha256
    ):
        raise ValueError("RWKV7 request state-profile SHA-256 mismatch")
    return profile


__all__ = [
    "RWKV7InitialStateProfile",
    "RWKV7InitialStateProfiles",
    "RWKV7_STATE_PROFILE_MANIFEST_SCHEMA",
    "RWKV7_STATE_PROFILE_SHA256_XARG",
    "RWKV7_STATE_PROFILE_XARG",
    "RWKV7_ZERO_STATE_PROFILE",
    "resolve_request_profile",
    "sha256_file",
]
