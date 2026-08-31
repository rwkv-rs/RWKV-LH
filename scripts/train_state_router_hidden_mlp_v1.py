"""Train and calibrate the Stage-0 0.4B RWKV hidden + multi-head MLP."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from rwkv_lh.state_router.local_backend import (
    DEFAULT_ROUTER_MODEL,
    DEFAULT_VLLM_RWKV_PYTHON,
    DEFAULT_VLLM_RWKV_REVISION,
    DEFAULT_VLLM_RWKV_ROOT,
    LocalVLLMRWKVExtractor,
    LocalVLLMRWKVSettings,
)
from rwkv_lh.state_router.training import (
    extract_or_load_features,
    file_sha256,
    read_rows,
    train_hidden_mlp,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl"
DEFAULT_OUTPUT = (
    ROOT / "data/experiments/STATE_ROUTER_STAGE0_VLLM_HIDDEN_MLP_V1_R2_20260827"
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    pending.replace(path)


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
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=829)
    args = parser.parse_args()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    dataset = args.dataset.resolve()
    rows = read_rows(dataset)
    settings = LocalVLLMRWKVSettings(
        model=args.model,
        engine_root=args.engine_root,
        engine_revision=args.engine_revision,
        engine_python=args.engine_python,
        batch_size=args.extract_batch_size,
        max_tokens=args.max_tokens,
        wkv_mode=args.wkv_mode,
    )
    extractor = LocalVLLMRWKVExtractor(settings)
    import torch

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    extraction_started = time.perf_counter()
    features, token_counts, identity = extract_or_load_features(
        rows, extractor, output / "features.hidden.pt"
    )
    extraction_seconds = time.perf_counter() - extraction_started
    write_json(output / "runtime_identity.json", identity)
    training_started = time.perf_counter()
    artifact, report, history, probabilities = train_hidden_mlp(
        rows,
        features,
        model_hash=extractor.model_hash,
        seed=args.seed,
        epochs=args.epochs,
        batch_size=args.train_batch_size,
        patience=args.patience,
        device=args.device,
    )
    training_seconds = time.perf_counter() - training_started
    write_json(output / "state_router_head.json", artifact)
    write_json(output / "training_history.json", history)
    predictions_path = output / "predictions.test.jsonl"
    pending_predictions = predictions_path.with_suffix(".jsonl.pending")
    with pending_predictions.open("w", encoding="utf-8") as stream:
        for row, prediction in zip(rows, probabilities):
            if row["split"] != "test":
                continue
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
    report["dataset"] = {
        "path": str(dataset),
        "sha256": file_sha256(dataset),
        "rows": len(rows),
    }
    report["feature_cache"] = {
        "path": str(output / "features.hidden.pt"),
        "sha256": file_sha256(output / "features.hidden.pt"),
        "shape": list(features.shape),
        "minimum_tokens": min(token_counts),
        "maximum_tokens": max(token_counts),
        "mean_tokens": sum(token_counts) / len(token_counts),
    }
    report["runtime_identity"] = identity
    report["runtime_measurements"] = {
        "feature_extraction_seconds": extraction_seconds,
        "head_training_seconds": training_seconds,
        "total_seconds": extraction_seconds + training_seconds,
        "cuda_peak_allocated_bytes": int(
            identity.get("runtime", {}).get("cuda_peak_allocated_bytes", 0)
        ),
        "cuda_peak_reserved_bytes": int(
            identity.get("runtime", {}).get("cuda_peak_reserved_bytes", 0)
        ),
    }
    write_json(output / "results.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
