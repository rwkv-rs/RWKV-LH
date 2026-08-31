from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
    RWKV7InitialStateProfiles,
    resolve_request_profile,
)


def _write_manifest(
    directory: Path,
    profiles: dict[str, float],
    *,
    default_profile: str = "zero",
    layers: int = 2,
    heads: int = 2,
) -> tuple[Path, str, dict[str, str]]:
    entries = []
    digests = {}
    for profile_id, value in profiles.items():
        state_path = directory / f"{profile_id}.pth"
        torch.save(
            {
                f"blocks.{layer}.att.time_state": torch.full(
                    (heads, 64, 64), value, dtype=torch.bfloat16
                )
                for layer in range(layers)
            },
            state_path,
        )
        digest = hashlib.sha256(state_path.read_bytes()).hexdigest()
        digests[profile_id] = digest
        entries.append(
            {
                "id": profile_id,
                "format": "rwkv-peft-time-state.v1",
                "path": state_path.name,
                "sha256": digest,
            }
        )
    manifest_path = directory / "profiles.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "vllm.rwkv7-state-profiles.v1",
                "model_artifact": "/models/rwkv-13.3b.pth",
                "model_revision": "runtime",
                "default_profile": default_profile,
                "profiles": entries,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return manifest_path, manifest_digest, digests


def _load(manifest: Path, digest: str, **changes: object):
    values = {
        "model_artifact": "/models/rwkv-13.3b.pth",
        "model_revision": "runtime",
        "total_num_layers": 2,
        "total_num_heads": 2,
        "layer_offset": 0,
        "num_layers": 2,
        "tp_size": 1,
        "tp_rank": 0,
        "num_heads": 2,
        "head_size": 64,
        "device": torch.device("cpu"),
        "dtype": torch.float32,
    }
    values.update(changes)
    return RWKV7InitialStateProfiles.load(str(manifest), digest, **values)


def test_profiles_are_pinned_preloaded_and_selected_per_request(tmp_path: Path):
    manifest, manifest_digest, state_digests = _write_manifest(
        tmp_path, {"selector": 1.0, "executor": 2.0}
    )
    profiles = _load(manifest, manifest_digest)

    selector = resolve_request_profile(
        profiles,
        SimpleNamespace(
            extra_args={
                "rwkv_state_profile": "selector",
                "rwkv_state_profile_sha256": state_digests["selector"],
            }
        ),
    )
    executor = resolve_request_profile(
        profiles,
        SimpleNamespace(
            extra_args={
                "rwkv_state_profile": "executor",
                "rwkv_state_profile_sha256": state_digests["executor"],
            }
        ),
    )

    assert profiles.manifest_sha256 == manifest_digest
    assert selector.wkv_state is not None
    assert executor.wkv_state is not None
    assert selector.wkv_state.dtype == torch.float32
    assert tuple(selector.wkv_state.shape) == (2, 2, 64, 64)
    assert torch.all(selector.wkv_state == 1)
    assert torch.all(executor.wkv_state == 2)
    assert profiles.resolve(None).profile_id == "zero"


def test_manifest_requires_an_explicit_request_profile_pair(tmp_path: Path):
    manifest, manifest_digest, _ = _write_manifest(
        tmp_path, {"executor": 2.0}
    )
    profiles = _load(manifest, manifest_digest)

    with pytest.raises(ValueError, match="must explicitly select"):
        resolve_request_profile(profiles, SimpleNamespace(extra_args={}))

    zero = resolve_request_profile(
        profiles,
        SimpleNamespace(
            extra_args={
                "rwkv_state_profile": "zero",
                "rwkv_state_profile_sha256": "0" * 64,
            }
        ),
    )
    assert zero.profile_id == "zero"
    assert zero.wkv_state is None


def test_zero_only_runtime_preserves_implicit_native_zero_compatibility() -> None:
    profiles = RWKV7InitialStateProfiles.zero_only()

    zero = resolve_request_profile(profiles, SimpleNamespace(extra_args={}))

    assert zero.profile_id == "zero"
    assert zero.wkv_state is None


def test_tensor_parallel_rank_gets_only_its_heads(tmp_path: Path):
    manifest, manifest_digest, _ = _write_manifest(
        tmp_path, {"executor": 3.0}, heads=4
    )
    profiles = _load(
        manifest,
        manifest_digest,
        total_num_heads=4,
        tp_size=2,
        tp_rank=1,
        num_heads=2,
    )
    state = profiles.resolve("executor").wkv_state
    assert state is not None
    assert tuple(state.shape) == (2, 2, 64, 64)
    assert torch.all(state == 3)


@pytest.mark.parametrize(
    ("extra_args", "message"),
    [
        ({"rwkv_state_profile": "executor"}, "both required"),
        ({"rwkv_state_profile_sha256": "f" * 64}, "both required"),
        (
            {
                "rwkv_state_profile": "executor",
                "rwkv_state_profile_sha256": "f" * 64,
            },
            "SHA-256 mismatch",
        ),
        (
            {
                "rwkv_state_profile": "missing",
                "rwkv_state_profile_sha256": "f" * 64,
            },
            "unknown RWKV7 state-profile",
        ),
    ],
)
def test_request_identity_must_match_registry(
    tmp_path: Path, extra_args: dict[str, str], message: str
):
    manifest, manifest_digest, _ = _write_manifest(
        tmp_path, {"executor": 2.0}
    )
    profiles = _load(manifest, manifest_digest)
    with pytest.raises(ValueError, match=message):
        resolve_request_profile(profiles, SimpleNamespace(extra_args=extra_args))


def test_manifest_and_model_identity_fail_closed(tmp_path: Path):
    manifest, manifest_digest, _ = _write_manifest(
        tmp_path, {"executor": 2.0}
    )
    with pytest.raises(ValueError, match="must pin"):
        _load(manifest, "")
    with pytest.raises(ValueError, match="manifest SHA-256 mismatch"):
        _load(manifest, "f" * 64)
    with pytest.raises(ValueError, match="model artifact mismatch"):
        _load(manifest, manifest_digest, model_artifact="/models/wrong.pth")


def test_tuned_profile_cannot_be_implicit_default(tmp_path: Path):
    manifest, manifest_digest, _ = _write_manifest(
        tmp_path, {"executor": 2.0}, default_profile="executor"
    )
    with pytest.raises(ValueError, match="default must be zero"):
        _load(manifest, manifest_digest)
