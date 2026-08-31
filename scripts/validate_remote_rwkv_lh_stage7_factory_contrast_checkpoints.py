"""Numerically validate every preregistered Stage7 state checkpoint."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Mapping

import torch


RUN = Path(
    "/home/chase/chase/RWKV-PEFT/out/"
    "g1i-13.3b-rwkv-lh-stage7-factory-contrast2000-cont-stage4-lr3e-6-seed833"
)
PARENT = Path(
    "/home/chase/chase/RWKV-PEFT/out/"
    "g1i-13.3b-rwkv-lh-stage4-balanced1140-cont-stage1-lr1e-5-seed830/"
    "rwkv-step-1140.pth"
)
PARENT_SHA256 = "8af6f29bb8cd68ed2f5e7ca6bcee56f7df7c53bccb083a80d1fa51e680d81960"
STEPS = (500, 1000, 1500, 2000)
EXPECTED_KEYS = {f"blocks.{layer}.att.time_state" for layer in range(61)}
EXPECTED_ELEMENTS = 15_990_784


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path) -> Mapping[str, torch.Tensor]:
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(payload, Mapping) or set(payload) != EXPECTED_KEYS:
        raise SystemExit(f"checkpoint mapping/key mismatch: {path}")
    return payload


def tensor_contract(path: Path, payload: Mapping[str, torch.Tensor]) -> dict:
    tensors = list(payload.values())
    result = {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "keys": len(tensors),
        "elements": sum(tensor.numel() for tensor in tensors),
        "shapes": sorted({tuple(tensor.shape) for tensor in tensors}),
        "dtypes": sorted({str(tensor.dtype) for tensor in tensors}),
        "all_finite": all(bool(torch.isfinite(tensor).all()) for tensor in tensors),
        "nonzero_elements": sum(int(torch.count_nonzero(tensor)) for tensor in tensors),
        "mean_abs": statistics.fmean(
            float(tensor.float().abs().mean()) for tensor in tensors
        ),
        "max_abs": max(float(tensor.float().abs().max()) for tensor in tensors),
    }
    if not (
        result["keys"] == 61
        and result["elements"] == EXPECTED_ELEMENTS
        and result["shapes"] == [(64, 64, 64)]
        and result["dtypes"] == ["torch.bfloat16"]
        and result["all_finite"]
        and result["nonzero_elements"] == EXPECTED_ELEMENTS
    ):
        raise SystemExit(json.dumps(result, ensure_ascii=False))
    return result


def delta_metrics(
    left: Mapping[str, torch.Tensor], right: Mapping[str, torch.Tensor]
) -> dict:
    absolute = squared = left_squared = right_squared = dot = maximum = 0.0
    elements = 0
    for key in sorted(EXPECTED_KEYS):
        before = left[key].float()
        after = right[key].float()
        delta = after - before
        absolute += float(delta.abs().sum())
        squared += float((delta * delta).sum())
        left_squared += float((before * before).sum())
        right_squared += float((after * after).sum())
        dot += float((before * after).sum())
        maximum = max(maximum, float(delta.abs().max()))
        elements += delta.numel()
    if maximum == 0:
        raise SystemExit("candidate state is numerically identical to its comparison state")
    return {
        "elements": elements,
        "mean_abs": absolute / elements,
        "max_abs": maximum,
        "l2_norm": squared**0.5,
        "left_l2_norm": left_squared**0.5,
        "right_l2_norm": right_squared**0.5,
        "cosine": dot / ((left_squared * right_squared) ** 0.5),
    }


def main() -> int:
    if sha256(PARENT) != PARENT_SHA256:
        raise SystemExit("parent state digest changed")
    run_manifest = json.loads(
        (RUN / "run_manifest.pretrain.json").read_text(encoding="utf-8")
    )
    if not (
        run_manifest["status"] == "preflight_passed"
        and run_manifest["mode"] == "commit"
        and run_manifest["training"]["candidate_steps"] == list(STEPS)
        and run_manifest["training"]["warmup_steps"] == 20
        and run_manifest["training"]["data_shuffle"] == 0
    ):
        raise SystemExit("committed preflight manifest changed")
    state_init = json.loads((RUN / "state_init_metadata.json").read_text(encoding="utf-8"))
    if not (
        state_init["sha256"] == PARENT_SHA256
        and state_init["state_tensor_count"] == 61
    ):
        raise SystemExit("state continuation metadata changed")

    loss_rows = [
        json.loads(line)
        for line in (RUN / "loss_data.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    losses = [float(row["loss"]) for row in loss_rows]
    if len(losses) != 2000 or not all(math.isfinite(loss) for loss in losses):
        raise SystemExit(f"invalid loss rows: {len(losses)}")
    parent = load(PARENT)
    parent_result = tensor_contract(PARENT, parent)
    previous = parent
    checkpoints: dict[str, dict] = {}
    for step in STEPS:
        path = RUN / f"rwkv-step-{step}.pth"
        candidate = load(path)
        checkpoints[str(step)] = {
            "checkpoint": tensor_contract(path, candidate),
            "delta_from_parent": delta_metrics(parent, candidate),
            "delta_from_previous_saved_state": delta_metrics(previous, candidate),
            "loss_through_step": {
                "rows": step,
                "mean": statistics.fmean(losses[:step]),
                "last_64_mean": statistics.fmean(losses[max(0, step - 64) : step]),
            },
        }
        previous = candidate

    result = {
        "schema_version": "rwkv-lh.stage7-checkpoint-validation.v1",
        "status": "validated",
        "selection_policy": "earliest checkpoint passing every preregistered hard gate",
        "parent_checkpoint": parent_result,
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
                f"{start + 1}-{start + 500}": statistics.fmean(
                    losses[start : start + 500]
                )
                for start in range(0, 2000, 500)
            },
        },
        "state_init_metadata": state_init,
        "checkpoints": checkpoints,
    }
    output = RUN / "checkpoint_validation.json"
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
