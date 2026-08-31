from __future__ import annotations

from pathlib import Path

import pytest
import torch

from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.exact_tool_selector.takeover_model_v4 import (
    NETWORK_TAKEOVER_HEAD_SCHEMA,
    NETWORK_TAKEOVER_LABELS,
    NetworkTakeoverHead,
    NetworkTakeoverHeadNetwork,
)


def _artifact(path: Path) -> None:
    model = NetworkTakeoverHeadNetwork.create().eval()
    mean = torch.zeros(2560, dtype=torch.float32)
    std = torch.ones(2560, dtype=torch.float32)
    state = {name: value.detach().clone() for name, value in model.state_dict().items()}
    import hashlib

    digest = lambda value: hashlib.sha256(value.contiguous().numpy().tobytes()).hexdigest()
    metadata = {"raw_argmax_only": True}
    identity = {
        "schema_version": NETWORK_TAKEOVER_HEAD_SCHEMA,
        "labels": list(NETWORK_TAKEOVER_LABELS),
        "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        "model_hash": "a" * 64,
        "tensor_digests": {
            "normalizer.mean": digest(mean),
            "normalizer.std": digest(std),
            **{f"state_dict.{name}": digest(value) for name, value in sorted(state.items())},
        },
        "metadata": metadata,
    }
    torch.save({
        "schema_version": NETWORK_TAKEOVER_HEAD_SCHEMA,
        "labels": list(NETWORK_TAKEOVER_LABELS),
        "feature_protocol": identity["feature_protocol"],
        "model_hash": identity["model_hash"],
        "head_hash": canonical_digest(identity),
        "normalizer": {"mean": mean, "std": std},
        "state_dict": state,
        "metadata": metadata,
    }, path)


def test_takeover_head_preserves_three_raw_logits_and_argmax(tmp_path: Path) -> None:
    path = tmp_path / "head.pt"
    _artifact(path)
    head = NetworkTakeoverHead(path)
    logits = head.raw_logits([0.0] * 2560)
    assert len(logits) == 3
    assert head.select([0.0] * 2560) == NETWORK_TAKEOVER_LABELS[
        max(range(3), key=lambda index: (logits[index], -index))
    ]


def test_takeover_head_rejects_tensor_mutation(tmp_path: Path) -> None:
    path = tmp_path / "head.pt"
    _artifact(path)
    value = torch.load(path, map_location="cpu", weights_only=True)
    value["state_dict"]["head.bias"][0] += 1
    torch.save(value, path)
    with pytest.raises(ValueError, match="tensor identity"):
        NetworkTakeoverHead(path)
