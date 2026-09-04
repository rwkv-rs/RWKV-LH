#!/usr/bin/env python3
"""Train the sole preregistered fresh G1J Selector-Intent MLP Head."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.input_protocol import (
    G1J_SELECTOR_INTENT_HEAD_ID,
    G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
    G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
)
from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
    NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
    NetworkSelectorMLPArtifact,
)
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SEED = 20260902
EPOCHS = 200
BATCH_SIZE = 64
HIDDEN_DIM = 64
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001
DROPOUT = 0.05
ZERO_SHA256 = "0" * 64
MODEL_WEIGHTS_SHA256 = "c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_line(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _metrics(predictions, labels) -> dict[str, Any]:
    import torch

    by_label: dict[str, Any] = {}
    f1_values: list[float] = []
    for index, name in enumerate(NETWORK_EXACT_TOOL_LABELS):
        true_positive = int(((predictions == index) & (labels == index)).sum())
        false_positive = int(((predictions == index) & (labels != index)).sum())
        false_negative = int(((predictions != index) & (labels == index)).sum())
        support = int((labels == index).sum())
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        f1_values.append(f1)
        by_label[name] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return {
        "accuracy": float((predictions == labels).float().mean()),
        "macro_f1": sum(f1_values) / len(f1_values),
        "by_label": by_label,
    }


def _gpu_identity() -> dict[str, str]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "3":
        raise RuntimeError("G1J Selector Head training is pinned to physical GPU 3")
    output = subprocess.run(
        ["nvidia-smi", "-i", "3", "--query-gpu=index,uuid,name", "--format=csv,noheader,nounits"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    index, uuid, name = [item.strip() for item in output.split(",")]
    if index != "3" or uuid != "GPU-a9570da2-547a-c2b3-0cab-7bbdc1a8a8b0":
        raise RuntimeError("physical GPU 3 identity changed")
    return {"index": index, "uuid": uuid, "name": name}


def train(*, features_directory: Path, preregistration: Path, output: Path) -> None:
    import numpy as np
    import torch

    features_directory = features_directory.resolve()
    preregistration = preregistration.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Head output must not exist: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    gpu = _gpu_identity()
    feature_manifest_path = features_directory / "FEATURE_MANIFEST.json"
    feature_manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    if feature_manifest.get("sealed_rows_read") != 0 or feature_manifest.get("feature_shape") != [400, 5120]:
        raise ValueError("feature manifest is not the frozen train/dev zero-State matrix")
    if feature_manifest.get("model_weights_sha256") != MODEL_WEIGHTS_SHA256:
        raise ValueError("feature model identity changed")
    portable_identity = feature_manifest.get("portable_feature_identity")
    if (
        feature_manifest.get("training_trajectory_mode")
        != G1J_SELECTOR_TRAINING_TRAJECTORY_MODE
        or feature_manifest.get("persistent_history_replayed") is not True
        or not isinstance(portable_identity, dict)
        or portable_identity.get("training_trajectory_mode")
        != G1J_SELECTOR_TRAINING_TRAJECTORY_MODE
        or portable_identity.get("persistent_history_replayed") is not True
    ):
        raise ValueError(
            "G1J Selector Head training requires serving-parity persistent "
            "causal trajectories; independent bootstrap rows are not eligible"
        )
    with np.load(features_directory / "features.npz") as archive:
        features = np.asarray(archive["features"], dtype=np.float32)
    records = [
        json.loads(line)
        for line in (features_directory / "feature_records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if features.shape != (400, 5120) or len(records) != 400:
        raise ValueError("feature rows differ from the preregistered matrix")
    label_to_index = {name: index for index, name in enumerate(NETWORK_EXACT_TOOL_LABELS)}
    labels = torch.tensor([label_to_index[row["label"]] for row in records], dtype=torch.long)
    train_indices = torch.tensor([index for index, row in enumerate(records) if row["split"] == "train"])
    dev_indices = torch.tensor([index for index, row in enumerate(records) if row["split"] == "dev"])
    if tuple(train_indices.shape) != (300,) or tuple(dev_indices.shape) != (100,):
        raise ValueError("Head split counts changed")
    x_cpu = torch.from_numpy(features)
    mean = x_cpu.index_select(0, train_indices).mean(dim=0)
    std = x_cpu.index_select(0, train_indices).std(dim=0, unbiased=False).clamp_min(1e-6)

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    torch.use_deterministic_algorithms(True)
    device = torch.device("cuda:0")

    class Head(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.shared = torch.nn.Linear(5120, HIDDEN_DIM)
            self.norm = torch.nn.LayerNorm(HIDDEN_DIM)
            self.dropout = torch.nn.Dropout(DROPOUT)
            self.output = torch.nn.Linear(HIDDEN_DIM, len(NETWORK_EXACT_TOOL_LABELS))
            torch.nn.init.xavier_uniform_(self.shared.weight)
            torch.nn.init.zeros_(self.shared.bias)
            torch.nn.init.ones_(self.norm.weight)
            torch.nn.init.zeros_(self.norm.bias)
            torch.nn.init.xavier_uniform_(self.output.weight)
            torch.nn.init.zeros_(self.output.bias)

        def forward(self, value):
            value = torch.nn.functional.gelu(self.shared(value))
            return self.output(self.dropout(self.norm(value)))

    model = Head().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    x_train = ((x_cpu.index_select(0, train_indices) - mean) / std).to(device)
    y_train = labels.index_select(0, train_indices).to(device)
    generator = torch.Generator(device="cpu").manual_seed(SEED)
    history: list[dict[str, Any]] = []
    for epoch in range(1, EPOCHS + 1):
        model.train()
        permutation = torch.randperm(len(x_train), generator=generator)
        losses: list[float] = []
        for start in range(0, len(x_train), BATCH_SIZE):
            batch = permutation[start : start + BATCH_SIZE].to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x_train.index_select(0, batch))
            loss = torch.nn.functional.cross_entropy(logits, y_train.index_select(0, batch))
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        if epoch in {1, 25, 50, 100, 150, 200}:
            history.append({"epoch": epoch, "mean_train_loss": sum(losses) / len(losses)})

    model.eval()
    normalized = ((x_cpu - mean) / std).to(device)
    with torch.inference_mode():
        logits = model(normalized)
        predictions = logits.argmax(dim=1).cpu()
    train_metrics = _metrics(predictions.index_select(0, train_indices), labels.index_select(0, train_indices))
    dev_metrics = _metrics(predictions.index_select(0, dev_indices), labels.index_select(0, dev_indices))

    portable_identity = dict(portable_identity)
    metadata = {
        "head_id": G1J_SELECTOR_INTENT_HEAD_ID,
        "compact_input_schema_version": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "training_trajectory_mode": G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
        "portable_feature_identity": portable_identity,
        "base_state_profile": "zero",
        "state_tuned": False,
        "fresh_xavier_initialization": True,
        "seed": SEED,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "dropout": DROPOUT,
        "temperature_calibrated": False,
        "dev_used_for_selection": False,
        "sealed_rows_accessed": 0,
        "feature_manifest_sha256": _sha256(feature_manifest_path),
        "preregistration_sha256": _sha256(preregistration),
        "training_device": "cuda:physical-gpu3",
        "physical_gpu_uuid": gpu["uuid"],
    }
    state = model.state_dict()
    artifact: dict[str, Any] = {
        "schema_version": NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
        "feature_dim": 5120,
        "hidden_dim": HIDDEN_DIM,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
        "feature_mean": mean.tolist(),
        "feature_std": std.tolist(),
        "shared_weight": state["shared.weight"].detach().cpu().tolist(),
        "shared_bias": state["shared.bias"].detach().cpu().tolist(),
        "layer_norm_weight": state["norm.weight"].detach().cpu().tolist(),
        "layer_norm_bias": state["norm.bias"].detach().cpu().tolist(),
        "head_weight": state["output.weight"].detach().cpu().tolist(),
        "head_bias": state["output.bias"].detach().cpu().tolist(),
        "temperature": 1.0,
        "model_hash": MODEL_WEIGHTS_SHA256,
        "metadata": metadata,
    }
    artifact["head_hash"] = canonical_digest(artifact)
    # Dependency-light production replay must accept the exact serialized Head.
    NetworkSelectorMLPArtifact.from_dict(artifact)
    pending = output.with_name(output.name + ".pending")
    pending.mkdir()
    head_path = pending / "selector_head.json"
    head_path.write_bytes(_json_line(artifact))
    prediction_rows = [
        {
            "schema_version": "rwkv-lh.g1j-selector-intent-head-dev-prediction.v1",
            "sample_id": records[index]["sample_id"],
            "label": records[index]["label"],
            "prediction": NETWORK_EXACT_TOOL_LABELS[int(predictions[index])],
            "correct": bool(int(predictions[index]) == int(labels[index])),
        }
        for index in dev_indices.tolist()
    ]
    (pending / "DEV_PREDICTIONS.jsonl").write_bytes(b"".join(_json_line(row) for row in prediction_rows))
    (pending / "TRAINING_HISTORY.json").write_bytes(_json_line({"epochs": history}))
    result = {
        "schema_version": "rwkv-lh.g1j-selector-intent-head-result.v1",
        "head_id": G1J_SELECTOR_INTENT_HEAD_ID,
        "head_hash": artifact["head_hash"],
        "head_file_sha256": _sha256(head_path),
        "train_metrics": train_metrics,
        "dev_metrics": dev_metrics,
        "sealed_rows_accessed": 0,
        "selected_epoch": EPOCHS,
        "candidate_count": 1,
        "gpu": gpu,
        "status": "frozen",
    }
    (pending / "HEAD_RESULT.json").write_bytes(_json_line(result))
    os.replace(pending, output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True, type=Path)
    parser.add_argument("--preregistration", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(features_directory=args.features, preregistration=args.preregistration, output=args.output)
