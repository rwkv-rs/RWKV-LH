"""Validate all Round1 2K training checkpoints and loss rows, fail closed."""

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
    "g1i-13.3b-rwkv-lh-r1-2k-v1-state-target-ctx2496-lr2e-5-seed826"
)
EXPECTED_NAMES = [f"rwkv-step-{step}.pth" for step in range(250, 2001, 250)]
EXPECTED_KEYS = {f"blocks.{layer}.att.time_state" for layer in range(61)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


checkpoints: dict[str, dict] = {}
for name in EXPECTED_NAMES:
    path = RUN / name
    if not path.is_file():
        raise SystemExit(f"missing checkpoint: {path}")
    payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(payload, Mapping):
        raise SystemExit(f"checkpoint is not a tensor mapping: {name}")
    if set(payload) != EXPECTED_KEYS:
        raise SystemExit(f"checkpoint key mismatch: {name}")
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
    }
    if not (
        result["keys"] == 61
        and result["elements"] == 15_990_784
        and result["shapes"] == [(64, 64, 64)]
        and result["dtypes"] == ["torch.bfloat16"]
        and result["all_finite"]
        and result["nonzero_elements"] == result["elements"]
    ):
        raise SystemExit(json.dumps({name: result}, ensure_ascii=False))
    checkpoints[name] = result

loss_path = RUN / "loss_data.jsonl"
loss_rows = [
    json.loads(line)
    for line in loss_path.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
losses = [float(row["loss"]) for row in loss_rows]
if len(losses) != 2000 or not all(math.isfinite(loss) for loss in losses):
    raise SystemExit(f"invalid loss rows: {len(losses)}")

segments = {
    f"{start + 1}-{start + 250}": statistics.fmean(losses[start : start + 250])
    for start in range(0, 2000, 250)
}
selected = checkpoints["rwkv-step-2000.pth"]
result = {
    "schema_version": "rwkv-lh.state-tuning-checkpoint-validation.v1",
    "status": "validated",
    "selection_policy": "final_step_2000_preregistered_single_epoch",
    "selected_checkpoint": selected,
    "loss": {
        "rows": len(losses),
        "all_finite": True,
        "mean": statistics.fmean(losses),
        "median": statistics.median(losses),
        "first_100_mean": statistics.fmean(losses[:100]),
        "last_100_mean": statistics.fmean(losses[-100:]),
        "minimum": min(losses),
        "maximum": max(losses),
        "segment_250_means": segments,
    },
    "checkpoints": checkpoints,
}
(RUN / "checkpoint_validation.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(result, ensure_ascii=False, indent=2))
