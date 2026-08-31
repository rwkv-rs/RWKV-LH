"""Generic numerical validator for a preregistered final state checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Mapping

import torch


EXPECTED_KEYS = {f"blocks.{layer}.att.time_state" for layer in range(61)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate(path: Path) -> tuple[dict, Mapping[str, torch.Tensor]]:
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(payload, Mapping) or set(payload) != EXPECTED_KEYS:
        raise SystemExit(f"checkpoint mapping/key mismatch: {path.name}")
    tensors = list(payload.values())
    result = {
        "path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path),
        "keys": len(tensors), "elements": sum(t.numel() for t in tensors),
        "shapes": sorted({tuple(t.shape) for t in tensors}),
        "dtypes": sorted({str(t.dtype) for t in tensors}),
        "all_finite": all(bool(torch.isfinite(t).all()) for t in tensors),
        "nonzero_elements": sum(int(torch.count_nonzero(t)) for t in tensors),
        "mean_abs": statistics.fmean(float(t.float().abs().mean()) for t in tensors),
        "max_abs": max(float(t.float().abs().max()) for t in tensors),
    }
    if not (
        result["keys"] == 61 and result["elements"] == 15_990_784
        and result["shapes"] == [(64, 64, 64)]
        and result["dtypes"] == ["torch.bfloat16"] and result["all_finite"]
        and result["nonzero_elements"] == result["elements"]
    ):
        raise SystemExit(json.dumps(result, ensure_ascii=False))
    return result, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--parent-sha256", required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--step-save", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sha256(args.parent) != args.parent_sha256:
        raise SystemExit("parent state digest changed")
    parent_result, parent = validate(args.parent)
    saved_steps = list(range(args.step_save, args.steps, args.step_save)) + [args.steps]
    checkpoints: dict[str, dict] = {}
    child: Mapping[str, torch.Tensor] | None = None
    for step in saved_steps:
        name = f"rwkv-step-{step}.pth"
        result, payload = validate(args.run_dir / name)
        checkpoints[name] = result
        if step == args.steps:
            child = payload
    assert child is not None
    loss_rows = [json.loads(line) for line in (args.run_dir / "loss_data.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    losses = [float(row["loss"]) for row in loss_rows]
    if len(losses) != args.steps or not all(math.isfinite(loss) for loss in losses):
        raise SystemExit(f"invalid loss rows: {len(losses)}")
    delta_abs = delta_sq = parent_sq = child_sq = dot = delta_max = 0.0
    elements = 0
    for key in sorted(EXPECTED_KEYS):
        left, right = parent[key].float(), child[key].float()
        delta = right - left
        delta_abs += float(delta.abs().sum()); delta_sq += float((delta * delta).sum())
        parent_sq += float((left * left).sum()); child_sq += float((right * right).sum())
        dot += float((left * right).sum()); delta_max = max(delta_max, float(delta.abs().max()))
        elements += delta.numel()
    if delta_max == 0:
        raise SystemExit("selected state is numerically identical to parent")
    metadata = json.loads((args.run_dir / "state_init_metadata.json").read_text(encoding="utf-8"))
    if metadata["sha256"] != args.parent_sha256 or metadata["state_tensor_count"] != 61:
        raise SystemExit("state continuation metadata changed")
    segments = {
        f"{start + 1}-{min(start + args.step_save, args.steps)}": statistics.fmean(losses[start : start + args.step_save])
        for start in range(0, args.steps, args.step_save)
    }
    selected = checkpoints[f"rwkv-step-{args.steps}.pth"]
    result = {
        "schema_version": "rwkv-lh.state-tuning-checkpoint-validation.v2",
        "status": "validated", "selection_policy": f"final_step_{args.steps}_preregistered",
        "parent_checkpoint": parent_result, "selected_checkpoint": selected,
        "state_delta": {
            "elements": elements, "mean_abs": delta_abs / elements, "max_abs": delta_max,
            "l2_norm": delta_sq**0.5, "parent_l2_norm": parent_sq**0.5,
            "child_l2_norm": child_sq**0.5, "parent_child_cosine": dot / ((parent_sq * child_sq) ** 0.5),
        },
        "loss": {
            "rows": len(losses), "all_finite": True, "mean": statistics.fmean(losses),
            "median": statistics.median(losses), "first_64_mean": statistics.fmean(losses[:64]),
            "last_64_mean": statistics.fmean(losses[-64:]), "minimum": min(losses),
            "maximum": max(losses), "segment_means": segments,
        },
        "state_init_metadata": metadata, "checkpoints": checkpoints,
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
