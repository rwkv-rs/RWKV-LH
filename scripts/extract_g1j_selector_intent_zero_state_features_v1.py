#!/usr/bin/env python3
"""Extract exact online-parity zero-State G1J Selector-Intent features."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path("/home/chase/GitHub/RWKV-LH")
ENGINE_REVISION = "67f0c5996c50dca0ad779da545cb491527de988f"
MODEL_WEIGHTS_SHA256 = "c1a316e75abd50f5edc3358fbb2c7d1cb18c611d9b2aa5b888091c8d45cc866c"
ZERO_SHA256 = "0" * 64
FEATURE_PROTOCOL = "rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_line(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _gpu_identity() -> dict[str, str]:
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "3":
        raise RuntimeError("G1J Selector feature extraction is pinned to physical GPU 3")
    output = subprocess.run(
        [
            "nvidia-smi",
            "-i",
            "3",
            "--query-gpu=index,uuid,name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    index, uuid, name, memory = [item.strip() for item in output.split(",")]
    if index != "3" or uuid != "GPU-a9570da2-547a-c2b3-0cab-7bbdc1a8a8b0":
        raise RuntimeError("physical GPU 3 identity changed")
    return {"index": index, "uuid": uuid, "name": name, "memory_total_mib": memory}


def extract(
    *,
    dataset: Path,
    output: Path,
    engine_root: Path,
    engine_python: Path,
    model_artifact: Path,
    runtime_temp: Path,
) -> None:
    import numpy as np
    import torch

    from rwkv_lh.exact_tool_selector.input_protocol import (
        G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
        network_selector_input_protocol,
    )
    from rwkv_lh.goal_state_protocols import selector_intent
    from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
    from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings

    dataset = dataset.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"feature output must not exist: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    manifest_path = dataset / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_id") != "rwkv_lh_g1j_selector_intent_state_tuning_v1":
        raise ValueError("feature extraction received the wrong dataset")
    if manifest.get("counts", {}).get("sealed") != 100:
        raise ValueError("frozen Selector sealed count changed")
    sources = _read_jsonl(dataset / "source_registry.jsonl")
    samples = _read_jsonl(dataset / "sample_index.jsonl")
    if len(sources) != 400 or len(samples) != 400:
        raise ValueError("feature extraction may read only the frozen 300 train + 100 dev rows")
    if any(sample["split"] == "sealed" for sample in samples):
        raise ValueError("sealed sample reached feature extraction")
    sample_by_source = {sample["source_id"]: sample for sample in samples}
    if set(sample_by_source) != {row["source_id"] for row in sources}:
        raise ValueError("source/sample index identities differ")

    gpu = _gpu_identity()
    model_manifest = json.loads((model_artifact / "manifest.json").read_text(encoding="utf-8"))
    if model_manifest.get("output", {}).get("weights_sha256") != MODEL_WEIGHTS_SHA256:
        raise ValueError("G1J 2.9B service artifact SHA changed")
    protocol = network_selector_input_protocol(G1J_SELECTOR_INTENT_INPUT_PROTOCOL)
    settings = LocalVLLMRWKVSettings(
        engine_root=engine_root,
        engine_revision=ENGINE_REVISION,
        engine_python=engine_python,
        model=model_artifact,
        batch_size=1,
        max_tokens=2048,
        wkv_mode="fp16",
        runtime_temp=runtime_temp,
        compatibility_sha256=ZERO_SHA256,
    )
    extractor = PersistentVLLMRWKVExtractor(settings)
    extractor.load()
    first_payload = sources[0]["payload"]
    bootstrap = protocol.render_bootstrap(first_payload)
    _ignored, bootstrap_state, bootstrap_tokens, bootstrap_identity = (
        extractor.advance_hidden_feature(
            bootstrap,
            parent_state=None,
            continuation=False,
            feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        )
    )
    feature_rows: list[np.ndarray[Any, Any]] = []
    records: list[dict[str, Any]] = []
    view_identity: dict[str, Any] | None = None
    for index, source in enumerate(sources):
        payload = source["payload"]
        prompt = selector_intent.render_prompt(payload)
        if protocol.render_step(payload) != prompt:
            raise ValueError("offline and online G1J Selector prompt renderers differ")
        views, _next_state, step_tokens, identity = extractor.advance_hidden_views(
            "\n" + prompt,
            parent_state=bootstrap_state,
            continuation=True,
        )
        mean = torch.as_tensor(views["mean"], dtype=torch.float32).flatten()
        last = torch.as_tensor(views["last"], dtype=torch.float32).flatten()
        feature = torch.cat((mean, last), dim=0)
        if tuple(feature.shape) != (5120,) or not bool(torch.isfinite(feature).all()):
            raise RuntimeError("G1J Selector feature shape/finiteness changed")
        sample = sample_by_source[source["source_id"]]
        feature_rows.append(feature.numpy())
        records.append(
            {
                "schema_version": "rwkv-lh.g1j-selector-intent-zero-feature-record.v1",
                "row_index": index,
                "sample_id": sample["sample_id"],
                "source_id": source["source_id"],
                "split": sample["split"],
                "label": payload["selected_operation"],
                "prompt_sha256": sample["prompt_sha256"],
                "bootstrap_tokens": bootstrap_tokens,
                "step_tokens": step_tokens,
                "feature_sha256": hashlib.sha256(feature.numpy().tobytes()).hexdigest(),
            }
        )
        view_identity = dict(identity)
    features = np.stack(feature_rows).astype(np.float32, copy=False)
    if features.shape != (400, 5120):
        raise RuntimeError("frozen G1J Selector feature matrix shape changed")
    portable_identity = {
        "batch_size": 1,
        "compact_input_schema_version": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
        "engine_revision": ENGINE_REVISION,
        "feature_dim": 5120,
        "feature_protocol": FEATURE_PROTOCOL,
        "fusion_order": ["mean", "last"],
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "one_current_forward_for_both_views": True,
        # Every row above starts from the same bootstrap State.  This frozen v1
        # extractor is an independent-row baseline, not a serving-parity
        # persistent trajectory extractor.
        "persistent_history_replayed": False,
        "training_trajectory_mode": "independent-bootstrap-rows.v1",
        "source_feature_protocols": {
            "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
            "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        },
        "state_profile": {"id": "zero", "sha256": ZERO_SHA256},
        "wkv_mode": "fp16",
    }
    feature_manifest = {
        "schema_version": "rwkv-lh.g1j-selector-intent-zero-feature-manifest.v1",
        "dataset_manifest_path": str(manifest_path),
        "dataset_manifest_sha256": _sha256(manifest_path),
        "rows": 400,
        "train_rows": 300,
        "dev_rows": 100,
        "sealed_rows_read": 0,
        "feature_shape": [400, 5120],
        "feature_protocol": FEATURE_PROTOCOL,
        "model_source_sha256": model_manifest["source"]["sha256"],
        "model_weights_sha256": MODEL_WEIGHTS_SHA256,
        "engine_revision": ENGINE_REVISION,
        "zero_state_sha256": ZERO_SHA256,
        "gpu": gpu,
        "bootstrap_state_reused_byte_exact": True,
        "persistent_history_replayed": False,
        "training_trajectory_mode": "independent-bootstrap-rows.v1",
        "bootstrap_identity": dict(bootstrap_identity),
        "view_identity": view_identity,
        "portable_feature_identity": portable_identity,
        "extractor_path": str(Path(__file__).resolve()),
        "extractor_sha256": _sha256(Path(__file__).resolve()),
        "status": "frozen",
    }
    pending = output.with_name(output.name + ".pending")
    if pending.exists():
        raise FileExistsError(pending)
    pending.mkdir()
    with (pending / "features.npz").open("wb") as stream:
        np.savez_compressed(stream, features=features)
    (pending / "feature_records.jsonl").write_bytes(b"".join(_json_line(row) for row in records))
    feature_manifest["features_sha256"] = _sha256(pending / "features.npz")
    feature_manifest["feature_records_sha256"] = _sha256(pending / "feature_records.jsonl")
    (pending / "FEATURE_MANIFEST.json").write_bytes(_json_line(feature_manifest))
    os.replace(pending, output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--engine-python", required=True, type=Path)
    parser.add_argument("--model-artifact", required=True, type=Path)
    parser.add_argument("--runtime-temp", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    extract(
        dataset=args.dataset,
        output=args.output,
        engine_root=args.engine_root,
        engine_python=args.engine_python,
        model_artifact=args.model_artifact,
        runtime_temp=args.runtime_temp,
    )
