"""Fail-closed vLLM-RWKV preflight for the selected Round1 2K state."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
from typing import Mapping

import torch
import vllm
import vllm.rwkv7_ops


EXPECTED_KEYS = {f"blocks.{layer}.att.time_state" for layer in range(61)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def checked(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"{label} SHA mismatch: expected {expected}, got {actual}")
    return actual


def source_tree_digest(root: Path) -> dict[str, int | str]:
    records: list[tuple[str, str, int]] = []
    for path in sorted(root.rglob("*")):
        if (
            not path.is_file()
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        records.append(
            (
                path.relative_to(root).as_posix(),
                sha256(path),
                path.stat().st_size,
            )
        )
    digest = hashlib.sha256()
    for relative_path, file_sha, size in records:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_sha.encode("ascii"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\n")
    return {
        "file_count": len(records),
        "byte_count": sum(size for _path, _sha, size in records),
        "sha256": digest.hexdigest(),
    }


parser = argparse.ArgumentParser()
parser.add_argument("--state", type=Path, required=True)
parser.add_argument("--state-sha256", required=True)
parser.add_argument("--base", type=Path, required=True)
parser.add_argument("--base-sha256", required=True)
parser.add_argument("--adapter", type=Path, required=True)
parser.add_argument("--adapter-sha256", required=True)
parser.add_argument("--runtime-manifest", type=Path, required=True)
parser.add_argument("--runtime-manifest-sha256", required=True)
parser.add_argument("--report", type=Path, required=True)
args = parser.parse_args()

state_sha = checked(args.state, args.state_sha256, "state")
base_sha = checked(args.base, args.base_sha256, "base")
adapter_sha = checked(args.adapter, args.adapter_sha256, "adapter")
runtime_manifest_sha = checked(
    args.runtime_manifest,
    args.runtime_manifest_sha256,
    "vLLM runtime manifest",
)
runtime_manifest = json.loads(args.runtime_manifest.read_text(encoding="utf-8"))
if runtime_manifest.get("schema_version") != "rwkv-lh.vllm-runtime-manifest.v1":
    raise ValueError("unsupported vLLM runtime manifest schema")
source_root = Path(runtime_manifest["source_root"]).resolve()
actual_package_root = Path(inspect.getfile(vllm)).resolve().parent
if actual_package_root != source_root / "vllm":
    raise ValueError(
        "imported vLLM package root mismatch: "
        f"expected {source_root / 'vllm'}, got {actual_package_root}"
    )
actual_vllm_version = str(getattr(vllm, "__version__", ""))
if actual_vllm_version != runtime_manifest.get("vllm_version"):
    raise ValueError(
        "imported vLLM version mismatch: "
        f"expected {runtime_manifest.get('vllm_version')}, got {actual_vllm_version}"
    )
if torch.__version__ != runtime_manifest.get("torch_version"):
    raise ValueError(
        "vLLM torch version mismatch: "
        f"expected {runtime_manifest.get('torch_version')}, got {torch.__version__}"
    )
expected_tree = dict(runtime_manifest.get("source_tree") or {})
if expected_tree.get("root") != "vllm":
    raise ValueError("vLLM source-tree manifest must pin the vllm package root")
actual_tree = source_tree_digest(actual_package_root)
for key in ("file_count", "byte_count", "sha256"):
    if actual_tree[key] != expected_tree.get(key):
        raise ValueError(
            f"vLLM source-tree {key} mismatch: "
            f"expected {expected_tree.get(key)}, got {actual_tree[key]}"
        )
validated_runtime_files = []
for entry in runtime_manifest.get("files") or []:
    relative_path = Path(entry["path"])
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"invalid vLLM runtime manifest path: {relative_path}")
    runtime_path = (source_root / relative_path).resolve()
    try:
        runtime_path.relative_to(source_root)
    except ValueError as exc:
        raise ValueError(f"vLLM runtime path escapes source root: {relative_path}") from exc
    actual_sha = checked(runtime_path, str(entry["sha256"]), "vLLM runtime file")
    validated_runtime_files.append(
        {"path": str(relative_path), "sha256": actual_sha}
    )
actual_extension = Path(inspect.getfile(vllm.rwkv7_ops)).resolve()
expected_extension = (source_root / "vllm/rwkv7_ops.abi3.so").resolve()
if actual_extension != expected_extension:
    raise ValueError(
        "loaded RWKV extension mismatch: "
        f"expected {expected_extension}, got {actual_extension}"
    )
payload = torch.load(args.state, map_location="cpu", weights_only=True, mmap=True)
if not isinstance(payload, Mapping) or set(payload) != EXPECTED_KEYS:
    raise ValueError("state key set is not exactly 61 G1i time_state tensors")
tensors = list(payload.values())
if any(tuple(tensor.shape) != (64, 64, 64) for tensor in tensors):
    raise ValueError("state tensor shape mismatch")
if any(tensor.dtype != torch.bfloat16 for tensor in tensors):
    raise ValueError("state tensor dtype mismatch")
if any(not bool(torch.isfinite(tensor).all()) for tensor in tensors):
    raise ValueError("state contains non-finite values")
if any(int(torch.count_nonzero(tensor)) == 0 for tensor in tensors):
    raise ValueError("state contains an all-zero layer")
distribution_version = importlib.metadata.version("vllm")
if "rwkv" not in actual_vllm_version.casefold():
    raise ValueError(f"vLLM source build is not RWKV-enabled: {actual_vllm_version}")
result = {
    "schema_version": "rwkv-lh.round1-2k-vllm-preflight.v2",
    "status": "validated",
    "state": {"path": str(args.state), "sha256": state_sha, "keys": 61},
    "base": {"path": str(args.base), "sha256": base_sha},
    "adapter": {"path": str(args.adapter), "sha256": adapter_sha},
    "vllm_runtime": {
        "manifest_path": str(args.runtime_manifest),
        "manifest_sha256": runtime_manifest_sha,
        "source_root": str(source_root),
        "package_root": str(actual_package_root),
        "source_version": actual_vllm_version,
        "distribution_version": distribution_version,
        "distribution_metadata_matches_source": (
            distribution_version == actual_vllm_version
        ),
        "torch_version": torch.__version__,
        "loaded_extension": str(actual_extension),
        "source_tree": actual_tree,
        "files": validated_runtime_files,
    },
    "runtime": {
        "gpu": 0,
        "port": 18070,
        "wkv_mode": "fp32io16",
        "max_model_len": 16384,
        "gpu_memory_utilization": 0.98,
        "max_num_batched_tokens": 98304,
        "max_num_seqs": 64,
        "tool_disclosure_mode": "progressive_via_rwkv_lh_completions",
    },
}
args.report.parent.mkdir(parents=True, exist_ok=True)
temporary = args.report.with_name(f".{args.report.name}.tmp-{os.getpid()}")
temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(temporary, args.report)
print(json.dumps(result, ensure_ascii=False))
