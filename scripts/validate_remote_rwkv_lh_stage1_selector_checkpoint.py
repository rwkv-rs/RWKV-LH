"""Validate Stage-1 selector checkpoints, losses, and parent-state delta."""

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
    "g1i-13.3b-rwkv-lh-stage1-selector500-cont-r1-lr5e-5-seed827"
)
PARENT = Path(
    "/home/chase/chase/RWKV-PEFT/out/"
    "g1i-13.3b-rwkv-lh-r1-2k-v1-state-target-ctx2496-lr2e-5-seed826/"
    "rwkv-step-2000.pth"
)
PARENT_SHA256 = "601c3c4df8c6e82918efa36d5425626eb9cffa4a0c5f0512da83aa5063e423f5"
EXPECTED_NAMES = [f"rwkv-step-{step}.pth" for step in range(100, 501, 100)]
EXPECTED_KEYS = {f"blocks.{layer}.att.time_state" for layer in range(61)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_checkpoint(path: Path) -> tuple[dict, Mapping[str, torch.Tensor]]:
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(payload, Mapping):
        raise SystemExit(f"checkpoint is not a tensor mapping: {path.name}")
    if set(payload) != EXPECTED_KEYS:
        raise SystemExit(f"checkpoint key mismatch: {path.name}")
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
        and result["elements"] == 15_990_784
        and result["shapes"] == [(64, 64, 64)]
        and result["dtypes"] == ["torch.bfloat16"]
        and result["all_finite"]
        and result["nonzero_elements"] == result["elements"]
    ):
        raise SystemExit(json.dumps({path.name: result}, ensure_ascii=False))
    return result, payload


if sha256(PARENT) != PARENT_SHA256:
    raise SystemExit("parent state digest changed")
parent_result, parent = validate_checkpoint(PARENT)
checkpoints: dict[str, dict] = {}
selected_payload: Mapping[str, torch.Tensor] | None = None
for name in EXPECTED_NAMES:
    path = RUN / name
    if not path.is_file():
        raise SystemExit(f"missing checkpoint: {path}")
    checkpoint, payload = validate_checkpoint(path)
    checkpoints[name] = checkpoint
    if name == "rwkv-step-500.pth":
        selected_payload = payload
assert selected_payload is not None

loss_path = RUN / "loss_data.jsonl"
loss_rows = [
    json.loads(line)
    for line in loss_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
losses = [float(row["loss"]) for row in loss_rows]
if len(losses) != 500 or not all(math.isfinite(loss) for loss in losses):
    raise SystemExit(f"invalid loss rows: {len(losses)}")

delta_abs_sum = 0.0
delta_squared_sum = 0.0
parent_squared_sum = 0.0
child_squared_sum = 0.0
dot_sum = 0.0
delta_max = 0.0
elements = 0
for key in sorted(EXPECTED_KEYS):
    left = parent[key].float()
    right = selected_payload[key].float()
    delta = right - left
    delta_abs_sum += float(delta.abs().sum())
    delta_squared_sum += float((delta * delta).sum())
    parent_squared_sum += float((left * left).sum())
    child_squared_sum += float((right * right).sum())
    dot_sum += float((left * right).sum())
    delta_max = max(delta_max, float(delta.abs().max()))
    elements += delta.numel()
if delta_max == 0.0:
    raise SystemExit("selected state is bytewise/numerically identical to parent")

metadata = json.loads((RUN / "state_init_metadata.json").read_text(encoding="utf-8"))
if metadata["sha256"] != PARENT_SHA256 or metadata["state_tensor_count"] != 61:
    raise SystemExit("state continuation metadata changed")
segments = {
    f"{start + 1}-{start + 100}": statistics.fmean(losses[start : start + 100])
    for start in range(0, 500, 100)
}
selected = checkpoints["rwkv-step-500.pth"]
result = {
    "schema_version": "rwkv-lh.state-tuning-checkpoint-validation.v2",
    "status": "validated",
    "selection_policy": "final_step_500_preregistered_bos_aligned_continuation",
    "parent_checkpoint": parent_result,
    "selected_checkpoint": selected,
    "state_delta": {
        "elements": elements,
        "mean_abs": delta_abs_sum / elements,
        "max_abs": delta_max,
        "l2_norm": delta_squared_sum**0.5,
        "parent_l2_norm": parent_squared_sum**0.5,
        "child_l2_norm": child_squared_sum**0.5,
        "parent_child_cosine": dot_sum
        / ((parent_squared_sum * child_squared_sum) ** 0.5),
    },
    "loss": {
        "rows": len(losses),
        "all_finite": True,
        "mean": statistics.fmean(losses),
        "median": statistics.median(losses),
        "first_50_mean": statistics.fmean(losses[:50]),
        "last_50_mean": statistics.fmean(losses[-50:]),
        "minimum": min(losses),
        "maximum": max(losses),
        "segment_100_means": segments,
    },
    "state_init_metadata": metadata,
    "checkpoints": checkpoints,
}
(RUN / "checkpoint_validation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(result, ensure_ascii=False, indent=2))
