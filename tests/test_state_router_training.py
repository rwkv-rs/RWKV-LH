from __future__ import annotations

import json
from pathlib import Path

import pytest


torch = pytest.importorskip("torch")

from rwkv_lh.state_router.model import MultiHeadMLPArtifact
from rwkv_lh.state_router.protocol import HEAD_LABELS
from rwkv_lh.state_router.training import train_hidden_mlp


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl"


def test_trained_torch_head_matches_dependency_light_runtime() -> None:
    rows = [
        json.loads(line)
        for line in DATA.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    features = torch.tensor(
        [
            [
                float(index % 17) / 17.0,
                float((index * 3) % 19) / 19.0,
                float((index * 5) % 23) / 23.0,
                float((index * 7) % 29) / 29.0,
            ]
            for index in range(len(rows))
        ],
        dtype=torch.float32,
    )
    artifact_value, _, _, probabilities = train_hidden_mlp(
        rows,
        features,
        model_hash="synthetic-model-sha256",
        hidden_dim=8,
        dropout=0.0,
        epochs=1,
        batch_size=512,
        patience=1,
        device="cpu",
    )
    artifact = MultiHeadMLPArtifact.from_dict(artifact_value)

    for index in (0, 1399, 1400, 1699, 1700, 1999):
        actual = artifact.predict_probabilities(features[index].tolist())
        for name, labels in HEAD_LABELS.items():
            for label in labels:
                assert actual[name][label] == pytest.approx(
                    probabilities[index][name][label], rel=1e-5, abs=1e-6
                )
