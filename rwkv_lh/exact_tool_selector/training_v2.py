"""Torch training utilities for the frozen 25-class 2.9B Hidden+MLP Selector."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
)
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


def _torch() -> Any:
    import torch

    return torch


def select_temperature(logits: Any, labels: Any) -> float:
    torch = _torch()
    best_temperature = 1.0
    best_loss = math.inf
    with torch.no_grad():
        for step in range(25, 401):
            temperature = step / 100.0
            loss = float(
                torch.nn.functional.cross_entropy(logits / temperature, labels).item()
            )
            if loss < best_loss:
                best_loss = loss
                best_temperature = temperature
    return best_temperature


def classification_metrics(logits: Any, expected: Any) -> dict[str, Any]:
    torch = _torch()
    predicted = logits.argmax(dim=-1).cpu()
    expected = expected.cpu()
    labels = NETWORK_EXACT_TOOL_LABELS
    by_label: dict[str, Any] = {}
    confusion = torch.zeros((len(labels), len(labels)), dtype=torch.int64)
    for truth, guess in zip(expected.tolist(), predicted.tolist()):
        confusion[truth, guess] += 1
    for index, label in enumerate(labels):
        true_positive = int(confusion[index, index].item())
        false_positive = int(confusion[:, index].sum().item()) - true_positive
        false_negative = int(confusion[index, :].sum().item()) - true_positive
        precision_denominator = true_positive + false_positive
        recall_denominator = true_positive + false_negative
        precision = true_positive / precision_denominator if precision_denominator else 0.0
        recall = true_positive / recall_denominator if recall_denominator else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        by_label[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": recall_denominator,
        }
    accuracy = float((predicted == expected).float().mean().item())
    macro_f1 = sum(item["f1"] for item in by_label.values()) / len(labels)
    boundary_indices = {
        labels.index("search_text"),
        labels.index("web_search"),
        labels.index("connector_lookup"),
    }
    boundary_mask = torch.tensor(
        [int(item) in boundary_indices for item in expected.tolist()], dtype=torch.bool
    )
    boundary_accuracy = float(
        (predicted[boundary_mask] == expected[boundary_mask]).float().mean().item()
    )
    return {
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "boundary_accuracy": boundary_accuracy,
        "by_label": by_label,
        "confusion": confusion.tolist(),
    }


def train_network_selector_mlp(
    rows: Sequence[Mapping[str, Any]],
    features: Any,
    *,
    feature_protocol: str,
    model_hash: str,
    metadata: Mapping[str, Any],
    seed: int = 829,
    hidden_dim: int = 256,
    dropout: float = 0.2,
    epochs: int = 60,
    batch_size: int = 128,
    learning_rate: float = 1e-3,
    weight_decay: float = 1e-3,
    patience: int = 10,
    device: str = "auto",
    expected_split_counts: Mapping[str, int] | None = None,
    class_balanced_loss: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], Any]:
    torch = _torch()
    if features.ndim != 2 or tuple(features.shape) != (len(rows), 2560):
        raise ValueError("network Selector features do not align with frozen rows")
    if not bool(torch.isfinite(features).all()):
        raise ValueError("network Selector features contain non-finite values")
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device not in {"cpu", "cuda"}:
        raise ValueError("network Selector training device must be cpu/cuda/auto")
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)

    split_indices = {
        split: torch.tensor(
            [index for index, row in enumerate(rows) if row["split"] == split],
            dtype=torch.long,
        )
        for split in ("train", "dev", "test")
    }
    frozen_split_counts = dict(
        expected_split_counts
        if expected_split_counts is not None
        else {"train": 6000, "dev": 750, "test": 750}
    )
    if set(frozen_split_counts) != {"train", "dev", "test"} or any(
        not isinstance(value, int) or value < 1
        for value in frozen_split_counts.values()
    ):
        raise ValueError("network Selector split-count contract is invalid")
    actual_split_counts = {
        name: len(value) for name, value in split_indices.items()
    }
    if actual_split_counts != frozen_split_counts:
        raise ValueError(
            "network Selector split counts differ from the frozen contract: "
            f"expected {frozen_split_counts}, got {actual_split_counts}"
        )
    label_index = {label: index for index, label in enumerate(NETWORK_EXACT_TOOL_LABELS)}
    labels = torch.tensor(
        [label_index[str(row["label"])] for row in rows], dtype=torch.long
    )
    train_index = split_indices["train"]
    dev_index = split_indices["dev"]
    train_features = features[train_index].float()
    feature_mean = train_features.mean(dim=0)
    feature_std = train_features.std(dim=0, unbiased=False).clamp_min(1e-6)
    normalized = ((features.float() - feature_mean) / feature_std).to(device)
    labels_device = labels.to(device)
    train_class_counts = torch.bincount(
        labels[train_index], minlength=len(NETWORK_EXACT_TOOL_LABELS)
    )
    if bool((train_class_counts == 0).any()):
        raise ValueError("network Selector training split lacks a class")
    if class_balanced_loss:
        class_weights = len(train_index) / (
            len(NETWORK_EXACT_TOOL_LABELS) * train_class_counts.float()
        )
    else:
        class_weights = torch.ones(len(NETWORK_EXACT_TOOL_LABELS))
    class_weights_device = class_weights.to(device)

    class MLP(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.shared = torch.nn.Linear(2560, hidden_dim)
            self.layer_norm = torch.nn.LayerNorm(hidden_dim, eps=1e-5)
            self.dropout = torch.nn.Dropout(dropout)
            self.head = torch.nn.Linear(hidden_dim, len(NETWORK_EXACT_TOOL_LABELS))

        def forward(self, values: Any) -> Any:
            hidden = torch.nn.functional.gelu(
                self.shared(values), approximate="tanh"
            )
            hidden = self.dropout(self.layer_norm(hidden))
            return self.head(hidden)

    model = MLP().to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(1, epochs)
    )
    history: list[dict[str, Any]] = []
    best_score = -1.0
    best_loss = math.inf
    best_epoch = 0
    best_state: dict[str, Any] | None = None
    stale = 0
    generator = torch.Generator(device="cpu").manual_seed(seed)
    for epoch in range(1, epochs + 1):
        model.train()
        permutation = train_index[
            torch.randperm(len(train_index), generator=generator)
        ]
        total_loss = 0.0
        batches = 0
        for start in range(0, len(permutation), batch_size):
            indices = permutation[start : start + batch_size].to(device)
            logits = model(normalized[indices])
            loss = torch.nn.functional.cross_entropy(
                logits,
                labels_device[indices],
                weight=class_weights_device,
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
            dev_logits = model(normalized[dev_index.to(device)]).cpu()
            dev_loss = float(
                torch.nn.functional.cross_entropy(
                    dev_logits,
                    labels[dev_index],
                    weight=class_weights,
                ).item()
            )
        dev_metrics = classification_metrics(dev_logits, labels[dev_index])
        score = float(dev_metrics["macro_f1"])
        history.append(
            {
                "epoch": epoch,
                "train_loss": total_loss / max(1, batches),
                "dev_loss": dev_loss,
                "dev_accuracy": dev_metrics["accuracy"],
                "dev_macro_f1": score,
            }
        )
        if score > best_score + 1e-8 or (
            abs(score - best_score) <= 1e-8 and dev_loss < best_loss - 1e-8
        ):
            best_score = score
            best_loss = dev_loss
            best_epoch = epoch
            best_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
            stale = 0
        else:
            stale += 1
        if stale >= patience:
            break
    if best_state is None:
        raise RuntimeError("network Selector training produced no checkpoint")
    model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        all_logits = model(normalized).cpu()
    temperature = select_temperature(
        all_logits[dev_index], labels[dev_index]
    )
    split_reports = {
        split: classification_metrics(
            all_logits[indices], labels[indices]
        )
        for split, indices in split_indices.items()
    }
    test = split_reports["test"]
    new_labels = ("web_search", "connector_lookup", "calculator", "date_diff", "current_time")
    gates = {
        "accuracy": test["accuracy"] >= 0.90,
        "macro_f1": test["macro_f1"] >= 0.90,
        "all_class_recall": min(
            item["recall"] for item in test["by_label"].values()
        )
        >= 0.75,
        "new_operation_recall": min(
            test["by_label"][label]["recall"] for label in new_labels
        )
        >= 0.85,
        "search_boundary_accuracy": test["boundary_accuracy"] >= 0.85,
    }
    artifact: dict[str, Any] = {
        "schema_version": NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
        "feature_dim": 2560,
        "hidden_dim": hidden_dim,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "feature_protocol": feature_protocol,
        "feature_mean": feature_mean.tolist(),
        "feature_std": feature_std.tolist(),
        "shared_weight": best_state["shared.weight"].tolist(),
        "shared_bias": best_state["shared.bias"].tolist(),
        "layer_norm_weight": best_state["layer_norm.weight"].tolist(),
        "layer_norm_bias": best_state["layer_norm.bias"].tolist(),
        "head_weight": best_state["head.weight"].tolist(),
        "head_bias": best_state["head.bias"].tolist(),
        "temperature": temperature,
        "model_hash": model_hash,
        "metadata": {
            **dict(metadata),
            "seed": seed,
            "hidden_dim": hidden_dim,
            "dropout": dropout,
            "epochs_limit": epochs,
            "batch_size": batch_size,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
            "patience": patience,
            "best_epoch": best_epoch,
            "training_device": device,
            "raw_argmax_only": True,
            "class_balanced_loss": class_balanced_loss,
            "class_weights": class_weights.tolist(),
            "train_class_counts": train_class_counts.tolist(),
        },
    }
    artifact["head_hash"] = canonical_digest(artifact)
    report = {
        "feature_protocol": feature_protocol,
        "model_hash": model_hash,
        "head_hash": artifact["head_hash"],
        "best_epoch": best_epoch,
        "temperature": temperature,
        "split_reports": split_reports,
        "synthetic_test_gates": gates,
        "synthetic_test_accepted": all(gates.values()),
    }
    return artifact, report, history, all_logits


__all__ = [
    "classification_metrics",
    "select_temperature",
    "train_network_selector_mlp",
]
