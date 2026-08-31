"""Confirm the persistent reduced Router against frozen Stage-0 predictions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.state_router.http_client import StateRouterHTTPClient
from rwkv_lh.state_router.model import MultiHeadMLPArtifact
from rwkv_lh.state_router.protocol import RouterInput, resolve_router_output


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/test.jsonl"
PREDICTIONS = (
    ROOT
    / "data/experiments/STATE_ROUTER_STAGE0_VLLM_WKV_PCA_MLP_V1_20260827"
    / "predictions.test.jsonl"
)
HEAD = PREDICTIONS.with_name("state_router_head.json")
DEFAULT_OUTPUT = (
    ROOT
    / "data/experiments/RWKV_RUNTIME_STACK_V1_20260827"
    / "PERSISTENT_ROUTER_EQUIVALENCE.json"
)
DISCRETE_KEYS = (
    "context_mode",
    "execution_phase",
    "route_family",
    "network_recommendation",
    "state_profile",
    "abstain",
    "abstain_reasons",
    "candidate_route_family",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    result = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not all(isinstance(item, Mapping) for item in result):
        raise RuntimeError(f"non-object JSONL row in {path}")
    return result


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:29620")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 128:
        parser.error("--batch-size must be in [1, 128]")
    dataset_rows = rows(DATASET)
    frozen_rows = rows(PREDICTIONS)
    frozen_by_id = {item["sample_id"]: item for item in frozen_rows}
    if len(frozen_by_id) != len(dataset_rows):
        raise RuntimeError("frozen prediction/sample counts do not match")
    artifact = MultiHeadMLPArtifact.load(HEAD)
    inputs = [RouterInput.from_dict(item["input"]) for item in dataset_rows]
    started = time.perf_counter()
    outputs: list[dict[str, Any]] = []
    with StateRouterHTTPClient(args.url, timeout_seconds=180.0) as client:
        health = client.health()
        for start in range(0, len(inputs), args.batch_size):
            outputs.extend(client.route_many(inputs[start : start + args.batch_size]))
    elapsed = time.perf_counter() - started
    mismatches: list[dict[str, Any]] = []
    maximum_confidence_difference = 0.0
    for row, router_input, output in zip(
        dataset_rows, inputs, outputs, strict=True
    ):
        frozen = resolve_router_output(
            router_input,
            frozen_by_id[row["sample_id"]]["probabilities"],
            model_hash=artifact.model_hash,
            head_hash=artifact.head_hash,
            thresholds=artifact.thresholds,
        ).to_dict()
        changed = [
            key for key in DISCRETE_KEYS if output.get(key) != frozen.get(key)
        ]
        if changed:
            mismatches.append(
                {
                    "sample_id": row["sample_id"],
                    "changed_fields": changed,
                    "current": {key: output.get(key) for key in DISCRETE_KEYS},
                    "frozen": {key: frozen.get(key) for key in DISCRETE_KEYS},
                }
            )
        for head, current in output["confidence"].items():
            maximum_confidence_difference = max(
                maximum_confidence_difference,
                abs(float(current) - float(frozen["confidence"][head])),
            )
    passed = (
        not mismatches
        and all(item["model_hash"] == artifact.model_hash for item in outputs)
        and all(item["head_hash"] == artifact.head_hash for item in outputs)
        and health.get("engine_build_profile", {}).get("profile") == "rwkv"
        and health.get("engine_build_profile", {}).get("unrestricted") is False
        and health.get("torch_version") == "2.11.0+cu128"
        and maximum_confidence_difference <= 0.05
    )
    result = {
        "schema_version": "rwkv-lh.persistent-router-equivalence.v1",
        "passed": passed,
        "thresholds": {
            "discrete_mismatches": 0,
            "maximum_confidence_absolute_difference": 0.05,
            "required_build_profile": "rwkv",
            "required_torch_version": "2.11.0+cu128",
        },
        "inputs": {
            "dataset": str(DATASET),
            "dataset_sha256": sha256(DATASET),
            "frozen_predictions": str(PREDICTIONS),
            "frozen_predictions_sha256": sha256(PREDICTIONS),
            "head": str(HEAD),
            "head_sha256": sha256(HEAD),
        },
        "runtime_health": health,
        "results": {
            "rows": len(outputs),
            "discrete_mismatches": len(mismatches),
            "mismatch_examples": mismatches[:20],
            "maximum_confidence_absolute_difference": maximum_confidence_difference,
            "elapsed_seconds": elapsed,
            "rows_per_second": len(outputs) / elapsed,
        },
    }
    atomic_json(args.output.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
