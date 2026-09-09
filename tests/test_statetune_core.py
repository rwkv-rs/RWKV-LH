from __future__ import annotations

import hashlib

import pytest
import torch

from rwkv_lh import statetune_core as core
from rwkv_lh.rwkv7_layout import RWKV7Layout
from rwkv_lh.statetune_native_model import NativeStateModel


def test_native_model_uses_checkpoint_geometry_including_ranks_and_ffn():
    layout = RWKV7Layout(2, 128, 2, 64, 384, 256, 8, 16, 24, 32, "bfloat16")
    with torch.device("meta"):
        model = NativeStateModel(layout)
    assert model.blocks[0].att.w1.shape == (128, 8)
    assert model.blocks[1].att.v1.shape == (128, 24)
    assert model.blocks[0].ffn.key.weight.shape == (384, 128)
    assert model.blocks[1].att.time_state.shape == (2, 64, 64)


def test_sealed_core_identity_rejects_mutation_and_validates_device(tmp_path):
    path = tmp_path / "sealed.json"
    path.write_text('{"value":1}')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert core.read_sealed_json(path, digest) == {"value": 1}
    path.write_text('{"value":2}')
    with pytest.raises(ValueError, match="SHA-256"):
        core.verify_file(path, digest)
    assert core.device_uuid_matches("3e07b500-7d09-ce83-cc1a-35c6b13f8863", "GPU-3e07b500-7d09-ce83-cc1a-35c6b13f8863")
    assert not core.device_uuid_matches("invalid", "GPU-invalid")


def test_target_only_loss_and_context_rejection():
    rows = [{"sample_id": "mechanism", "input_token_ids": [0, 2, 3], "target_token_ids": [4, 5]}]
    batch = core.collate_samples(rows, context_tokens=4)
    assert batch["input_ids"].tolist() == [[0, 2, 3, 4]]
    assert batch["labels"].tolist() == [[-100, -100, 4, 5]]
    logits = torch.randn(1, 4, 8, requires_grad=True)
    core.target_cross_entropy(logits, batch["labels"]).backward()
    assert torch.count_nonzero(logits.grad[:, :2]) == 0
    assert torch.count_nonzero(logits.grad[:, 2:]) > 0
    with pytest.raises(ValueError, match="truncation is forbidden"):
        core.collate_samples(rows, context_tokens=3)
