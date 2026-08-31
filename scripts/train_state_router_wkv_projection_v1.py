"""Run Stage-0 scheme B with WKV statistics, train-only PCA, and the shared MLP."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.state_router.local_backend import (
    DEFAULT_ROUTER_MODEL,
    DEFAULT_VLLM_RWKV_PYTHON,
    DEFAULT_VLLM_RWKV_REVISION,
    DEFAULT_VLLM_RWKV_ROOT,
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.protocol import RouterInput, canonical_digest, canonical_json
from rwkv_lh.state_router.training import file_sha256, read_rows, train_hidden_mlp


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl"
DEFAULT_OUTPUT = (
    ROOT / "data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827"
)
CACHE_SCHEMA = "rwkv-lh.state-router-wkv-feature-cache.v1"
PCA_SCHEMA = "rwkv-lh.state-router-wkv-pca.v1"


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pending.replace(path)


def atomic_torch_save(torch: Any, value: object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    torch.save(value, pending)
    pending.replace(path)


def projection_digest(metadata: Mapping[str, Any], tensors: list[Any]) -> str:
    digest = hashlib.sha256(canonical_json(metadata).encode("utf-8"))
    for tensor in tensors:
        value = tensor.detach().float().cpu().contiguous()
        tensor_identity = {"shape": list(value.shape), "dtype": "float32"}
        digest.update(canonical_json(tensor_identity).encode("utf-8"))
        digest.update(value.numpy().tobytes(order="C"))
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", type=Path, default=DEFAULT_ROUTER_MODEL)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_VLLM_RWKV_ROOT)
    parser.add_argument("--engine-revision", default=DEFAULT_VLLM_RWKV_REVISION)
    parser.add_argument("--engine-python", type=Path, default=DEFAULT_VLLM_RWKV_PYTHON)
    parser.add_argument("--wkv-mode", choices=("fp16", "fp32io16"), default="fp16")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--extract-batch-size", type=int, default=16)
    parser.add_argument("--train-batch-size", type=int, default=128)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--layer-index", type=int, default=-1)
    parser.add_argument("--pca-dim", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=829)
    args = parser.parse_args()

    import torch

    dataset = args.dataset.resolve()
    output = args.output.resolve()
    rows = read_rows(dataset)
    sample_ids = [str(row["sample_id"]) for row in rows]
    texts = [RouterInput.from_dict(row["input"]).render() for row in rows]
    input_digest = canonical_digest(texts)
    extractor = LocalVLLMRWKVExtractor(
        LocalVLLMRWKVSettings(
            model=args.model,
            engine_root=args.engine_root,
            engine_revision=args.engine_revision,
            engine_python=args.engine_python,
            batch_size=args.extract_batch_size,
            max_tokens=args.max_tokens,
            wkv_mode=args.wkv_mode,
        )
    )
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    cache_path = output / "features.wkv_stats.pt"
    extraction_started = time.perf_counter()
    if cache_path.is_file():
        cached = torch.load(cache_path, map_location="cpu", weights_only=True)
        if not isinstance(cached, Mapping) or cached.get("schema_version") != CACHE_SCHEMA:
            raise ValueError("unsupported WKV feature cache")
        if list(cached.get("sample_ids") or []) != sample_ids:
            raise ValueError("WKV feature cache sample order mismatch")
        if str(cached.get("input_digest") or "") != input_digest:
            raise ValueError("WKV feature cache input digest mismatch")
        if str(cached.get("model_hash") or "") != extractor.model_hash:
            raise ValueError("WKV feature cache model hash mismatch")
        statistics = cached.get("features")
        token_counts = [int(value) for value in cached.get("token_counts") or []]
        identity = dict(cached.get("identity") or {})
        if not isinstance(statistics, torch.Tensor) or statistics.ndim != 2:
            raise ValueError("WKV cached features must be a rank-2 tensor")
        if statistics.shape[0] != len(rows) or len(token_counts) != len(rows):
            raise ValueError("WKV feature cache row count mismatch")
        statistics = statistics.float()
    else:
        statistics, token_counts, identity = extractor.extract_wkv_statistics(
            texts, layer_index=args.layer_index
        )
        atomic_torch_save(
            torch,
            {
                "schema_version": CACHE_SCHEMA,
                "sample_ids": sample_ids,
                "input_digest": input_digest,
                "model_hash": identity["model_hash"],
                "identity": identity,
                "features": statistics,
                "token_counts": token_counts,
            },
            cache_path,
        )
    extraction_seconds = time.perf_counter() - extraction_started

    train_index = torch.tensor(
        [index for index, row in enumerate(rows) if row["split"] == "train"],
        dtype=torch.long,
    )
    if len(train_index) != 1400:
        raise ValueError("WKV PCA requires the frozen 1,400-row train split")
    if not 2 <= args.pca_dim <= min(len(train_index) - 1, statistics.shape[1]):
        raise ValueError("WKV PCA dimension is invalid for the frozen features")
    pca_started = time.perf_counter()
    projection_device = "cuda" if torch.cuda.is_available() else "cpu"
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    values = statistics.to(projection_device)
    train_mean = values[train_index.to(projection_device)].mean(dim=0)
    centered_train = values[train_index.to(projection_device)] - train_mean
    _, singular_values, components = torch.pca_lowrank(
        centered_train,
        q=args.pca_dim,
        center=False,
        niter=4,
    )
    projected = ((values - train_mean) @ components).float().cpu()
    projection_path = output / "projection.train_only.pt"
    projection_metadata = {
        "schema_version": PCA_SCHEMA,
        "source_model_hash": identity["model_hash"],
        "dataset_sha256": file_sha256(dataset),
        "fit_split": "train",
        "seed": args.seed,
        "pca_dim": args.pca_dim,
    }
    value_digest = projection_digest(
        projection_metadata, [train_mean, components, singular_values]
    )
    atomic_torch_save(
        torch,
        {
            **projection_metadata,
            "projection_digest": value_digest,
            "mean": train_mean.cpu(),
            "components": components.cpu(),
            "singular_values": singular_values.cpu(),
        },
        projection_path,
    )
    pca_seconds = time.perf_counter() - pca_started
    projection_sha256 = file_sha256(projection_path)
    classifier_model_hash = canonical_digest(
        {
            "source_model_hash": identity["model_hash"],
            "projection_schema": PCA_SCHEMA,
            "projection_digest": value_digest,
        }
    )

    training_started = time.perf_counter()
    artifact, report, history, probabilities = train_hidden_mlp(
        rows,
        projected,
        model_hash=classifier_model_hash,
        seed=args.seed,
        epochs=args.epochs,
        batch_size=args.train_batch_size,
        patience=args.patience,
        device=args.device,
    )
    training_seconds = time.perf_counter() - training_started
    unhashed_artifact = dict(artifact)
    unhashed_artifact.pop("head_hash")
    metadata = dict(unhashed_artifact["metadata"])
    metadata.update(
        {
            "scheme": "B",
            "source_feature_protocol": identity["feature_protocol"],
            "projection_schema": PCA_SCHEMA,
            "projection_digest": value_digest,
            "projection_sha256": projection_sha256,
        }
    )
    unhashed_artifact["metadata"] = metadata
    artifact = unhashed_artifact
    artifact["head_hash"] = canonical_digest(artifact)
    report["scheme"] = "B"
    report["head_hash"] = artifact["head_hash"]
    report["dataset"] = {
        "path": str(dataset),
        "sha256": file_sha256(dataset),
        "rows": len(rows),
    }
    report["runtime_identity"] = identity
    report["feature_cache"] = {
        "path": str(cache_path),
        "sha256": file_sha256(cache_path),
        "shape": list(statistics.shape),
        "minimum_tokens": min(token_counts),
        "maximum_tokens": max(token_counts),
        "mean_tokens": sum(token_counts) / len(token_counts),
    }
    report["projection"] = {
        "path": str(projection_path),
        "sha256": projection_sha256,
        "projection_digest": value_digest,
        "fit_split": "train",
        "shape": list(components.shape),
    }
    report["runtime_measurements"] = {
        "feature_extraction_seconds": extraction_seconds,
        "pca_seconds": pca_seconds,
        "head_training_seconds": training_seconds,
        "total_seconds": extraction_seconds + pca_seconds + training_seconds,
        "cuda_peak_allocated_bytes": max(
            int(identity.get("runtime", {}).get("cuda_peak_allocated_bytes", 0)),
            int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else 0,
        ),
        "cuda_peak_reserved_bytes": max(
            int(identity.get("runtime", {}).get("cuda_peak_reserved_bytes", 0)),
            int(torch.cuda.max_memory_reserved()) if torch.cuda.is_available() else 0,
        ),
    }
    write_json(output / "runtime_identity.json", identity)
    write_json(output / "state_router_head.json", artifact)
    write_json(output / "training_history.json", history)
    predictions_path = output / "predictions.test.jsonl"
    pending_predictions = predictions_path.with_suffix(".jsonl.pending")
    with pending_predictions.open("w", encoding="utf-8") as stream:
        for row, prediction in zip(rows, probabilities):
            if row["split"] == "test":
                stream.write(
                    json.dumps(
                        {
                            "schema_version": "rwkv-lh.state-router-prediction.v1",
                            "sample_id": row["sample_id"],
                            "probabilities": prediction,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
    pending_predictions.replace(predictions_path)
    write_json(output / "results.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
