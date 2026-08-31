from __future__ import annotations

import hashlib
import json
from pathlib import Path

import torch

from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
    RWKV7InitialStateProfiles,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / (
    "data/models/state_profiles/"
    "network-selector-true-trajectory-s31-step2000-v1"
)
MANIFEST = PROFILE_DIR / "profiles.json"
STATE = PROFILE_DIR / "selector-true-trajectory-s31-step2000.vllm.pth"
MANIFEST_SHA256 = "706ff62cc8ae5851f9c918509911d4ee701f9db5d00bef16f24d2a568e3a0b47"
STATE_SHA256 = "1d7ab37e2ef3a87a6ff8e6792ed426f4c84694902ada62b60d15c16a6a8ce853"
PROFILE_ID = "selector-true-trajectory-s31-step2000-v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s31_state_profile_is_content_addressed_and_zero_is_default() -> None:
    assert sha256_file(MANIFEST) == MANIFEST_SHA256
    assert sha256_file(STATE) == STATE_SHA256
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["default_profile"] == "zero"
    assert manifest["profiles"] == [
        {
            "id": PROFILE_ID,
            "format": "rwkv-peft-time-state.v1",
            "path": STATE.name,
            "sha256": STATE_SHA256,
        }
    ]


def test_s31_state_profile_has_exact_2p9_tensor_contract() -> None:
    payload = torch.load(STATE, map_location="cpu", weights_only=True, mmap=True)
    assert set(payload) == {
        f"blocks.{layer}.att.time_state" for layer in range(32)
    }
    assert {tuple(value.shape) for value in payload.values()} == {(40, 64, 64)}
    assert {value.dtype for value in payload.values()} == {torch.bfloat16}
    assert all(bool(torch.isfinite(value).all()) for value in payload.values())
    assert all(bool(torch.count_nonzero(value)) for value in payload.values())


def test_s31_state_profile_loads_explicitly_without_becoming_default() -> None:
    profiles = RWKV7InitialStateProfiles.load(
        str(MANIFEST),
        MANIFEST_SHA256,
        model_artifact=str(
            ROOT / "data/models/rwkv7-g1i-2.9b-vllm-v1"
        ),
        model_revision="67f0c5996c50dca0ad779da545cb491527de988f",
        total_num_layers=32,
        total_num_heads=40,
        layer_offset=0,
        num_layers=32,
        tp_size=1,
        tp_rank=0,
        num_heads=40,
        head_size=64,
        device=torch.device("cpu"),
        dtype=torch.float32,
    )
    assert profiles.resolve(None).profile_id == "zero"
    tuned = profiles.resolve(PROFILE_ID)
    assert tuned.state_sha256 == STATE_SHA256
    assert tuned.wkv_state is not None
    assert tuple(tuned.wkv_state.shape) == (32, 40, 64, 64)
    assert tuned.wkv_state.dtype == torch.float32
