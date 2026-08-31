"""Optional Torch training utilities for the Stage-0 hidden + MLP router."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.state_router.local_backend import LocalVLLMRWKVExtractor
from rwkv_lh.state_router.metrics import (
    FIRST_ROUND_GATES,
    FORMAL_GATES,
    acceptance_gates,
    evaluate_probabilities,
)
from rwkv_lh.state_router.model import ROUTER_HEAD_ARTIFACT_SCHEMA_VERSION
from rwkv_lh.state_router.protocol import HEAD_LABELS, canonical_digest


FEATURE_CACHE_SCHEMA_VERSION = "rwkv-lh.state-router-feature-cache.v1"
TRAINING_PROTOCOL_VERSION = "rwkv-lh.state-router-hidden-mlp-training.v1"


def _torch() -> Any:
    try:
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "State Router training requires `uv run --extra state-router ...`"
        ) from exc
    return torch


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("State Router dataset must be non-empty JSONL objects")
    return rows


def extract_or_load_features(
    rows: Sequence[Mapping[str, Any]],
    extractor: LocalVLLMRWKVExtractor,
    cache_path: str | Path,
) -> tuple[Any, list[int], Mapping[str, Any]]:
    torch = _torch()
    cache = Path(cache_path)
    sample_ids = [str(row["sample_id"]) for row in rows]
    texts = []
    from rwkv_lh.state_router.protocol import RouterInput

    for row in rows:
        input_value = row.get("input")
        if not isinstance(input_value, Mapping):
            raise ValueError("State Router row input must be an object")
        texts.append(RouterInput.from_dict(input_value).render())
    input_digest = canonical_digest(texts)
    if cache.is_file():
        value = torch.load(cache, map_location="cpu", weights_only=True)
        if not isinstance(value, Mapping):
            raise ValueError("State Router feature cache must be an object")
        if value.get("schema_version") != FEATURE_CACHE_SCHEMA_VERSION:
            raise ValueError("unsupported State Router feature cache schema")
        if list(value.get("sample_ids") or []) != sample_ids:
            raise ValueError("State Router feature cache sample order mismatch")
        if str(value.get("input_digest") or "") != input_digest:
            raise ValueError("State Router feature cache input digest mismatch")
        if str(value.get("model_hash") or "") != extractor.model_hash:
            raise ValueError("State Router feature cache model hash mismatch")
        features = value.get("features")
        token_counts = [int(item) for item in value.get("token_counts") or []]
        if not isinstance(features, torch.Tensor) or features.ndim != 2:
            raise ValueError("State Router cached features must be a rank-2 tensor")
        if features.shape[0] != len(rows) or len(token_counts) != len(rows):
            raise ValueError("State Router feature cache row count mismatch")
        return features.float(), token_counts, dict(value.get("identity") or {})

    hidden = list(extractor.extract(texts))
    if len(hidden) != len(rows):
        raise RuntimeError("local hidden extractor returned the wrong row count")
    features = torch.tensor([item.values for item in hidden], dtype=torch.float32)
    token_counts = [item.token_count for item in hidden]
    identity = extractor.identity()
    value = {
        "schema_version": FEATURE_CACHE_SCHEMA_VERSION,
        "sample_ids": sample_ids,
        "input_digest": input_digest,
        "model_hash": extractor.model_hash,
        "identity": identity,
        "features": features,
        "token_counts": token_counts,
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    pending_cache = cache.with_suffix(cache.suffix + ".pending")
    torch.save(value, pending_cache)
    pending_cache.replace(cache)
    return features, token_counts, identity


def _label_tensors(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    torch = _torch()
    indices = {
        name: {label: index for index, label in enumerate(labels)}
        for name, labels in HEAD_LABELS.items()
    }
    return {
        name: torch.tensor(
            [indices[name][str(row["labels"][name])] for row in rows],
            dtype=torch.long,
        )
        for name in HEAD_LABELS
    }


def _macro_f1(expected: Any, predicted: Any, count: int) -> float:
    values: list[float] = []
    for label in range(count):
        true_positive = int(((expected == label) & (predicted == label)).sum().item())
        false_positive = int(((expected != label) & (predicted == label)).sum().item())
        false_negative = int(((expected == label) & (predicted != label)).sum().item())
        denominator = 2 * true_positive + false_positive + false_negative
        values.append(2 * true_positive / denominator if denominator else 0.0)
    return sum(values) / len(values)


def _class_weights(labels: Any, count: int, device: str) -> Any:
    torch = _torch()
    frequencies = torch.bincount(labels, minlength=count).float().clamp_min(1.0)
    weights = frequencies.sum().sqrt() / frequencies.sqrt()
    return (weights / weights.mean()).to(device)


def select_temperature(logits: Any, labels: Any) -> float:
    torch = _torch()
    best_temperature = 1.0
    best_loss = math.inf
    with torch.no_grad():
        for step in range(25, 401):
            temperature = step / 100.0
            loss = float(
                torch.nn.functional.cross_entropy(
                    logits / temperature, labels
                ).item()
            )
            if loss < best_loss:
                best_loss = loss
                best_temperature = temperature
    return best_temperature


def probability_records(
    logits: Mapping[str, Any], temperatures: Mapping[str, float]
) -> list[dict[str, dict[str, float]]]:
    torch = _torch()
    count = next(iter(logits.values())).shape[0]
    output: list[dict[str, dict[str, float]]] = [dict() for _ in range(count)]
    with torch.no_grad():
        for name, labels in HEAD_LABELS.items():
            values = torch.softmax(logits[name] / temperatures[name], dim=-1).cpu()
            for index in range(count):
                output[index][name] = {
                    label: float(values[index, label_index].item())
                    for label_index, label in enumerate(labels)
                }
    return output


def train_hidden_mlp(
    rows: Sequence[Mapping[str, Any]],
    features: Any,
    *,
    model_hash: str,
    seed: int = 829,
    hidden_dim: int = 256,
    dropout: float = 0.2,
    epochs: int = 60,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-3,
    patience: int = 10,
    device: str = "auto",
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, dict[str, float]]],
]:
    torch = _torch()
    if features.ndim != 2 or features.shape[0] != len(rows):
        raise ValueError("State Router features do not align with dataset rows")
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device not in {"cpu", "cuda"}:
        raise ValueError("State Router training device must be auto, cpu, or cuda")
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except TypeError:
        torch.use_deterministic_algorithms(True)

    split_indices = {
        split: torch.tensor(
            [index for index, row in enumerate(rows) if row["split"] == split],
            dtype=torch.long,
        )
        for split in ("train", "dev", "test")
    }
    if {name: len(value) for name, value in split_indices.items()} != {
        "train": 1400,
        "dev": 300,
        "test": 300,
    }:
        raise ValueError("State Router training requires frozen 1400/300/300 splits")
    labels = _label_tensors(rows)
    train_features = features[split_indices["train"]].float()
    feature_mean = train_features.mean(dim=0)
    feature_std = train_features.std(dim=0, unbiased=False).clamp_min(1e-6)
    normalized = ((features.float() - feature_mean) / feature_std).to(device)

    class MultiHeadMLP(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.shared = torch.nn.Linear(features.shape[1], hidden_dim)
            self.layer_norm = torch.nn.LayerNorm(hidden_dim, eps=1e-5)
            self.dropout = torch.nn.Dropout(dropout)
            self.heads = torch.nn.ModuleDict(
                {
                    name: torch.nn.Linear(hidden_dim, len(head_labels))
                    for name, head_labels in HEAD_LABELS.items()
                }
            )

        def forward(self, values: Any) -> dict[str, Any]:
            hidden = torch.nn.functional.gelu(
                self.shared(values), approximate="tanh"
            )
            hidden = self.dropout(self.layer_norm(hidden))
            return {name: head(hidden) for name, head in self.heads.items()}

    model = MultiHeadMLP().to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, epochs)
    )
    train_index = split_indices["train"]
    dev_index = split_indices["dev"]
    weights = {
        name: _class_weights(
            head_labels[train_index], len(HEAD_LABELS[name]), device
        )
        for name, head_labels in labels.items()
    }
    label_device = {name: value.to(device) for name, value in labels.items()}
    loss_scale = {
        "context_mode": 0.25,
        "execution_phase": 1.0,
        "route_family": 1.5,
        "network_recommendation": 1.0,
    }
    history: list[dict[str, Any]] = []
    best_score = -1.0
    best_state: dict[str, Any] | None = None
    best_epoch = 0
    stale_epochs = 0
    generator = torch.Generator(device="cpu").manual_seed(seed)

    for epoch in range(1, epochs + 1):
        model.train()
        permutation = train_index[torch.randperm(len(train_index), generator=generator)]
        total_loss = 0.0
        batches = 0
        for start in range(0, len(permutation), batch_size):
            indices = permutation[start : start + batch_size].to(device)
            logits = model(normalized[indices])
            loss = sum(
                loss_scale[name]
                * torch.nn.functional.cross_entropy(
                    logits[name], label_device[name][indices], weight=weights[name]
                )
                for name in HEAD_LABELS
            )
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.item())
            batches += 1
        scheduler.step()
        model.eval()
        with torch.no_grad():
            dev_logits = model(normalized[dev_index.to(device)])
        f1 = {
            name: _macro_f1(
                labels[name][dev_index],
                dev_logits[name].argmax(dim=-1).cpu(),
                len(HEAD_LABELS[name]),
            )
            for name in HEAD_LABELS
        }
        score = (
            1.5 * f1["route_family"]
            + f1["execution_phase"]
            + f1["network_recommendation"]
            + 0.25 * f1["context_mode"]
        ) / 3.75
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(1, batches),
                "dev_selection_score": score,
                "dev_macro_f1": f1,
            }
        )
        if score > best_score + 1e-8:
            best_score = score
            best_epoch = epoch
            best_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
        if stale_epochs >= patience:
            break
    if best_state is None:
        raise RuntimeError("State Router training did not produce a checkpoint")
    model.load_state_dict(best_state)
    model.eval()
    all_logits: dict[str, Any]
    with torch.no_grad():
        all_logits = {
            name: values.cpu()
            for name, values in model(normalized).items()
        }
    dev_logits = {name: values[dev_index] for name, values in all_logits.items()}
    temperatures = {
        name: select_temperature(dev_logits[name], labels[name][dev_index])
        for name in HEAD_LABELS
    }
    probabilities = probability_records(all_logits, temperatures)
    split_reports = {
        split: evaluate_probabilities(
            [rows[index] for index in indices.tolist()],
            [probabilities[index] for index in indices.tolist()],
        )
        for split, indices in split_indices.items()
    }

    state = model.state_dict()
    artifact: dict[str, Any] = {
        "schema_version": ROUTER_HEAD_ARTIFACT_SCHEMA_VERSION,
        "feature_dim": int(features.shape[1]),
        "hidden_dim": hidden_dim,
        "normalizer": {
            "mean": feature_mean.tolist(),
            "std": feature_std.tolist(),
        },
        "shared": {
            "weight": state["shared.weight"].cpu().tolist(),
            "bias": state["shared.bias"].cpu().tolist(),
        },
        "layer_norm": {
            "weight": state["layer_norm.weight"].cpu().tolist(),
            "bias": state["layer_norm.bias"].cpu().tolist(),
            "eps": 1e-5,
        },
        "heads": {
            name: {
                "weight": state[f"heads.{name}.weight"].cpu().tolist(),
                "bias": state[f"heads.{name}.bias"].cpu().tolist(),
                "labels": list(HEAD_LABELS[name]),
            }
            for name in HEAD_LABELS
        },
        "temperatures": temperatures,
        "thresholds": {
            "route_confidence": 0.92,
            "route_margin": 0.30,
            "ood_score": 0.50,
        },
        "model_hash": model_hash,
        "metadata": {
            "training_protocol": TRAINING_PROTOCOL_VERSION,
            "seed": seed,
            "hidden_dim": hidden_dim,
            "dropout": dropout,
            "epochs_requested": epochs,
            "epochs_completed": len(history),
            "best_epoch": best_epoch,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
            "patience": patience,
            "device": device,
            "split_counts": {name: len(value) for name, value in split_indices.items()},
            "selection_uses_test": False,
            "temperature_selection_split": "dev",
        },
    }
    artifact["head_hash"] = canonical_digest(artifact)
    report = {
        "schema_version": "rwkv-lh.state-router-training-result.v1",
        "training_protocol": TRAINING_PROTOCOL_VERSION,
        "model_hash": model_hash,
        "head_hash": artifact["head_hash"],
        "best_epoch": best_epoch,
        "best_dev_selection_score": best_score,
        "temperatures": temperatures,
        "metrics": split_reports,
        "label_counts": {
            split: {
                name: dict(
                    sorted(
                        Counter(
                            str(rows[index]["labels"][name])
                            for index in indices.tolist()
                        ).items()
                    )
                )
                for name in HEAD_LABELS
            }
            for split, indices in split_indices.items()
        },
    }
    report["acceptance"] = {
        split: {
            "first_round": acceptance_gates(split_reports[split], FIRST_ROUND_GATES),
            "formal": acceptance_gates(split_reports[split], FORMAL_GATES),
        }
        for split in ("dev", "test")
    }
    return artifact, report, history, probabilities


__all__ = [
    "FEATURE_CACHE_SCHEMA_VERSION",
    "TRAINING_PROTOCOL_VERSION",
    "extract_or_load_features",
    "file_sha256",
    "probability_records",
    "read_rows",
    "select_temperature",
    "train_hidden_mlp",
]
