#!/usr/bin/env python3
"""Fail-closed validation for every EXE-G1-V2 training/vLLM checkpoint."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import torch


PROJECT = Path("/home/chase/chase/RWKV-PEFT")
RUN = PROJECT / "out/g1i-13.3b-rwkv-lh-exe-g1-v2-2k-zero-lr2e-5-seed829"
PREFLIGHT = PROJECT / "temp/exe_g1_v2_training/RUN_MANIFEST.pretrain.json"
OUTPUT = RUN / "CHECKPOINT_VALIDATION.json"
PROFILE = "EXE-G1-V2"
REPORT_SCHEMA_VERSION = "rwkv-lh.exe-g1-v2-checkpoint-validation.v1"
STEPS = tuple(range(250, 2001, 250))
EXPECTED_KEYS = {f"blocks.{layer}.att.time_state" for layer in range(61)}
EXPECTED_ELEMENTS = 61 * 64 * 64 * 64


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_payload(path: Path) -> tuple[dict[str, Any], Mapping[str, torch.Tensor]]:
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(payload, Mapping) or set(payload) != EXPECTED_KEYS:
        raise SystemExit(f"checkpoint key mismatch: {path}")
    tensors = list(payload.values())
    result: dict[str, Any] = {
        "path": str(path.relative_to(PROJECT)),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "tensor_count": len(tensors),
        "elements": sum(tensor.numel() for tensor in tensors),
        "shapes": sorted({tuple(tensor.shape) for tensor in tensors}),
        "dtypes": sorted({str(tensor.dtype) for tensor in tensors}),
        "all_finite": all(bool(torch.isfinite(tensor).all()) for tensor in tensors),
        "all_layers_nonzero": all(
            bool(torch.count_nonzero(tensor)) for tensor in tensors
        ),
        "mean_abs": statistics.fmean(
            float(tensor.float().abs().mean()) for tensor in tensors
        ),
        "max_abs": max(float(tensor.float().abs().max()) for tensor in tensors),
    }
    if not (
        result["tensor_count"] == 61
        and result["elements"] == EXPECTED_ELEMENTS
        and result["shapes"] == [(64, 64, 64)]
        and result["dtypes"] == ["torch.bfloat16"]
        and result["all_finite"]
        and result["all_layers_nonzero"]
    ):
        raise SystemExit(json.dumps(result, default=list))
    result["shapes"] = [list(shape) for shape in result["shapes"]]
    return result, payload


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to replace validation report: {OUTPUT}")
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
    if not (
        preflight.get("profile") == PROFILE
        and preflight.get("initialization") == "native_zero"
        and preflight.get("continuation_state") is None
        and preflight.get("physical_gpu") == 0
        and preflight.get("dataset", {}).get("rows") == 2000
        and preflight.get("dataset", {}).get("loss_mask") == "target_suffix"
        and preflight.get("dataset", {}).get("jsonl_bos_token_id") == 0
        and preflight.get("training", {}).get("epoch_steps") == 2000
        and preflight.get("training", {}).get("step_save") == 250
        and preflight.get("training", {}).get("seed") == 829
    ):
        raise SystemExit("preflight manifest contract changed")

    checkpoints: dict[str, dict[str, Any]] = {}
    final_payload: Mapping[str, torch.Tensor] | None = None
    for step in STEPS:
        training_path = RUN / f"rwkv-step-{step}.pth"
        vllm_path = RUN / f"rwkv-step-{step}.vllm.pth"
        training_result, training = validate_payload(training_path)
        vllm_result, vllm = validate_payload(vllm_path)
        tensors_equal = all(
            torch.equal(training[key], vllm[key]) for key in EXPECTED_KEYS
        )
        if not tensors_equal:
            raise SystemExit(f"training/vLLM tensor mismatch at step {step}")
        sidecar = json.loads(
            (RUN / f"rwkv-step-{step}.vllm.json").read_text(encoding="utf-8")
        )
        expected_sidecar = {
            "format": "rwkv7-state-tuning-v2",
            "tensor_key_pattern": "blocks.{layer}.att.time_state",
            "training_layout": "[head,value,key]",
            "vllm_layout": "[head,value,key]",
            "conversion": "identity",
            "num_layers": 61,
            "num_heads": 64,
            "head_size": 64,
            "dtype": "bfloat16",
            "training_checkpoint": training_path.name,
            "vllm_checkpoint": vllm_path.name,
        }
        if sidecar != expected_sidecar:
            raise SystemExit(f"vLLM sidecar mismatch at step {step}")
        checkpoints[str(step)] = {
            "training": training_result,
            "vllm": vllm_result,
            "tensor_values_equal": True,
            "sidecar": sidecar,
        }
        if step == STEPS[-1]:
            final_payload = vllm

    loss_rows = [
        json.loads(line)
        for line in (RUN / "loss_data.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    losses = [float(row["loss"]) for row in loss_rows]
    if len(losses) != 2000 or not all(math.isfinite(loss) for loss in losses):
        raise SystemExit(f"loss row contract failed: {len(losses)}")
    assert final_payload is not None
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "profile": PROFILE,
        "status": "validated_not_selected",
        "initialization": "native_zero",
        "physical_gpu": 0,
        "selection_policy": "evaluate_all_checkpoints_on_frozen_dev480",
        "loss": {
            "rows": len(losses),
            "all_finite": True,
            "mean": statistics.fmean(losses),
            "median": statistics.median(losses),
            "first_64_mean": statistics.fmean(losses[:64]),
            "last_64_mean": statistics.fmean(losses[-64:]),
            "minimum": min(losses),
            "maximum": max(losses),
            "segment_means": {
                f"{start + 1}-{start + 250}": statistics.fmean(
                    losses[start : start + 250]
                )
                for start in range(0, 2000, 250)
            },
        },
        "final_zero_delta": {
            "elements": EXPECTED_ELEMENTS,
            "mean_abs": checkpoints["2000"]["vllm"]["mean_abs"],
            "max_abs": checkpoints["2000"]["vllm"]["max_abs"],
            "l2_norm": sum(
                float((tensor.float() ** 2).sum()) for tensor in final_payload.values()
            )
            ** 0.5,
        },
        "checkpoints": checkpoints,
        "preflight_manifest_sha256": sha256_file(PREFLIGHT),
    }
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
