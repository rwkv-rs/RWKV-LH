#!/usr/bin/env python3
"""Serialize the frozen native 2.9B G1i checkpoint for pinned vllm-rwkv.

The native checkpoint uses the engine's internal names.  The standard artifact
contract adds the ``model.`` prefix and transposes only legacy low-rank matrix
layout.  Three layer-zero value-mix tensors are deliberately unused by RWKV7;
they are retained byte-exact in a separate safetensors file.  Every source
tensor is reopened and checked before publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENGINE_ROOT = ROOT / "data/runtime/engines/vllm-rwkv-67f0c5996c50"
DEFAULT_SOURCE = Path(
    "/home/chase/GitHub/ReproBench/tmp/rwkv7-g1i-2.9b-20260805-ctx16384.pth"
)
DEFAULT_OUTPUT = ROOT / "data/models/rwkv7-g1i-2.9b-vllm-v1"
SOURCE_MODEL = "rwkv7-g1i-2.9b-20260805-ctx16384"
SOURCE_SHA256 = "ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320"
ENGINE_REVISION = "67f0c5996c50dca0ad779da545cb491527de988f"
SCHEMA_VERSION = "rwkv-lh.vllm-rwkv-artifact.v1"
AUDIT_SCHEMA_VERSION = "rwkv-lh.tensor-container-identity-audit.v1"
LOW_RANK_NAMES = frozenset(("w1", "w2", "a1", "a2", "v1", "v2", "g1", "g2"))
LAYER_ZERO_UNUSED = frozenset(
    ("blocks.0.att.v0", "blocks.0.att.v1", "blocks.0.att.v2")
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def tensor_sha256(tensor: Any) -> str:
    import torch

    contiguous = tensor.detach().cpu().contiguous()
    byte_view = contiguous.view(torch.uint8).numpy()
    return hashlib.sha256(memoryview(byte_view)).hexdigest()


def tensor_record(tensor: Any) -> dict[str, Any]:
    return {
        "dtype": str(tensor.dtype).removeprefix("torch."),
        "shape": list(tensor.shape),
        "numel": int(tensor.numel()),
        "bytes": int(tensor.numel() * tensor.element_size()),
        "content_sha256": tensor_sha256(tensor),
    }


def expected_config(source_sha256: str) -> dict[str, Any]:
    return {
        "a_low_rank_dim": 96,
        "architectures": ["Rwkv7ForCausalLM"],
        "bos_token_id": 0,
        "context_length": 16384,
        "decay_low_rank_dim": 96,
        "embedding_layer_norm_fused": False,
        "eos_token_id": 0,
        "gate_low_rank_dim": 320,
        "head_size": 64,
        "hidden_size": 2560,
        "intermediate_size": 10240,
        "max_position_embeddings": 16384,
        "model_type": "rwkv7",
        "num_attention_heads": 40,
        "num_hidden_layers": 32,
        "pad_token_id": 0,
        "rwkv_source_sha256": source_sha256,
        "tie_word_embeddings": False,
        "torch_dtype": "bfloat16",
        "v_low_rank_dim": 64,
        "vocab_size": 65536,
    }


def map_native_weight(name: str, tensor: Any) -> tuple[str, Any, str]:
    """Return standard target name/value and the reversible layout operation."""

    if name == "emb.weight":
        return "model.embeddings.weight", tensor, "identity"
    if name == "head.weight":
        return name, tensor, "identity"
    if name.startswith("ln_out."):
        return f"model.{name}", tensor, "identity"
    if not name.startswith("blocks."):
        raise ValueError(f"unmapped native RWKV7 key: {name}")
    parts = name.split(".")
    if len(parts) == 4 and parts[2] == "att" and parts[3] in LOW_RANK_NAMES:
        return f"model.{name}.weight", tensor.transpose(0, 1).contiguous(), "transpose-0-1"
    return f"model.{name}", tensor, "identity"


def engine_identity(engine_root: Path) -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=engine_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=engine_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return revision, dirty


def validate_existing(output: Path, source_sha256: str = SOURCE_SHA256) -> bool:
    manifest_path = output / "manifest.json"
    weights_path = output / "model.safetensors"
    audit_path = output / "tensor_identity_audit.json"
    unused_path = output / "native_unused_layer0_value_mix.safetensors"
    if (
        not manifest_path.is_file()
        or not weights_path.is_file()
        or not audit_path.is_file()
        or not unused_path.is_file()
    ):
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return bool(
        manifest.get("schema_version") == SCHEMA_VERSION
        and manifest.get("source", {}).get("sha256") == source_sha256
        and manifest.get("output", {}).get("weights_sha256")
        == file_sha256(weights_path)
        and manifest.get("output", {}).get("tensor_audit_sha256")
        == file_sha256(audit_path)
        and manifest.get("output", {}).get("unused_native_weights_sha256")
        == file_sha256(unused_path)
        and manifest.get("generation", {}).get("values_changed") is False
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_ENGINE_ROOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-model", default=SOURCE_MODEL)
    parser.add_argument("--source-sha256", default=SOURCE_SHA256)
    args = parser.parse_args()

    engine_root = args.engine_root.resolve()
    source = args.source.resolve()
    output = args.output.resolve()
    source_model = str(args.source_model).strip()
    expected_source_sha256 = str(args.source_sha256).strip()
    if not source_model or len(expected_source_sha256) != 64:
        raise ValueError("source model identity is incomplete")
    if not (engine_root / "vllm/model_executor/models/rwkv7.py").is_file():
        raise ValueError(f"not the project-pinned vllm-rwkv tree: {engine_root}")
    revision, dirty = engine_identity(engine_root)
    if revision != ENGINE_REVISION or dirty:
        raise RuntimeError(
            f"pinned engine identity mismatch: revision={revision} dirty={dirty}"
        )
    if not source.is_file():
        raise FileNotFoundError(source)
    source_sha256 = file_sha256(source)
    if source_sha256 != expected_source_sha256:
        raise ValueError(
            "source SHA-256 mismatch: "
            f"{source_sha256} != {expected_source_sha256}"
        )
    if validate_existing(output, expected_source_sha256):
        print(output)
        return
    if output.exists():
        raise FileExistsError(f"refusing to overwrite unverified artifact: {output}")

    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file
    from vllm.transformers_utils.configs.rwkv7 import (
        RWKV7Config,
        rwkv7_checkpoint_weight_shapes,
        validate_rwkv7_hf_artifact_config,
    )

    value = torch.load(source, map_location="cpu", weights_only=True, mmap=True)
    if not isinstance(value, dict) or not value:
        raise ValueError("native RWKV checkpoint must be a non-empty tensor mapping")
    if any(not isinstance(name, str) or not isinstance(tensor, torch.Tensor) for name, tensor in value.items()):
        raise ValueError("native RWKV checkpoint contains non-tensor entries")
    source_tensors = {
        name: tensor.detach().cpu().contiguous() for name, tensor in value.items()
    }
    config_values = expected_config(source_sha256)
    config = RWKV7Config(**config_values)
    validate_rwkv7_hf_artifact_config(config)
    expected_shapes = rwkv7_checkpoint_weight_shapes(config)
    runtime_tensors: dict[str, Any] = {}
    transformations: dict[str, dict[str, str]] = {}
    unused_tensors: dict[str, Any] = {}
    for source_name, source_tensor in source_tensors.items():
        if source_name in LAYER_ZERO_UNUSED:
            unused_tensors[source_name] = source_tensor
            transformations[source_name] = {
                "target": "native_unused_layer0_value_mix.safetensors:" + source_name,
                "operation": "byte-exact-auxiliary-preservation",
            }
            continue
        target_name, target_tensor, operation = map_native_weight(
            source_name, source_tensor
        )
        if target_name in runtime_tensors:
            raise ValueError(f"duplicate mapped RWKV7 target: {target_name}")
        runtime_tensors[target_name] = target_tensor
        transformations[source_name] = {
            "target": "model.safetensors:" + target_name,
            "operation": operation,
        }
    if set(unused_tensors) != set(LAYER_ZERO_UNUSED):
        raise ValueError("native layer-zero unused tensor set changed")
    actual_shapes = {
        name: tuple(tensor.shape) for name, tensor in runtime_tensors.items()
    }
    if set(actual_shapes) != set(expected_shapes):
        raise ValueError(
            "native 2.9B keys differ from pinned vllm-rwkv contract: "
            f"missing={sorted(set(expected_shapes) - set(actual_shapes))} "
            f"unexpected={sorted(set(actual_shapes) - set(expected_shapes))}"
        )
    wrong_shapes = {
        name: {"actual": list(actual_shapes[name]), "expected": list(expected_shapes[name])}
        for name in expected_shapes
        if actual_shapes[name] != expected_shapes[name]
    }
    if wrong_shapes:
        raise ValueError(f"native 2.9B shapes differ from vllm-rwkv: {wrong_shapes}")
    if {str(tensor.dtype) for tensor in source_tensors.values()} != {"torch.bfloat16"}:
        raise ValueError("native 2.9B tensors must all remain bfloat16")

    pending = output.with_name(f"{output.name}.pending.{os.getpid()}")
    pending.mkdir(parents=True, exist_ok=False)
    source_records = {
        name: tensor_record(source_tensors[name]) for name in sorted(source_tensors)
    }
    weights_path = pending / "model.safetensors"
    save_file(
        runtime_tensors,
        weights_path,
        metadata={
            "format": "pt",
            "rwkv_lh_conversion": AUDIT_SCHEMA_VERSION,
            "source_sha256": source_sha256,
            "values_changed": "false",
        },
    )
    unused_path = pending / "native_unused_layer0_value_mix.safetensors"
    save_file(
        unused_tensors,
        unused_path,
        metadata={
            "format": "pt",
            "rwkv_lh_preservation": AUDIT_SCHEMA_VERSION,
            "source_sha256": source_sha256,
            "runtime_consumed": "false",
            "values_changed": "false",
        },
    )

    output_records: dict[str, Any] = {}
    with safe_open(weights_path, framework="pt", device="cpu") as weights:
        if set(weights.keys()) != set(runtime_tensors):
            raise RuntimeError("safetensors key set changed during serialization")
        for source_name in sorted(set(source_tensors) - set(unused_tensors)):
            target_name = transformations[source_name]["target"].split(":", 1)[1]
            restored = weights.get_tensor(target_name)
            record = tensor_record(restored)
            operation = transformations[source_name]["operation"]
            logical_restored = (
                restored.transpose(0, 1).contiguous()
                if operation == "transpose-0-1"
                else restored
            )
            if not torch.equal(logical_restored, source_tensors[source_name]):
                raise RuntimeError(
                    f"tensor values changed during mapping: {source_name}"
                )
            output_records[source_name] = {
                "target_name": target_name,
                "operation": operation,
                "serialized": record,
                "logical_source_equal": True,
            }
    with safe_open(unused_path, framework="pt", device="cpu") as weights:
        if set(weights.keys()) != set(unused_tensors):
            raise RuntimeError("unused native tensor key set changed")
        for source_name in sorted(unused_tensors):
            restored = weights.get_tensor(source_name)
            record = tensor_record(restored)
            if record != source_records[source_name] or not torch.equal(
                restored, source_tensors[source_name]
            ):
                raise RuntimeError(
                    f"unused native tensor changed during preservation: {source_name}"
                )
            output_records[source_name] = {
                "target_name": source_name,
                "operation": "byte-exact-auxiliary-preservation",
                "serialized": record,
                "logical_source_equal": True,
            }

    audit = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "source_sha256": source_sha256,
        "source_weight_count": len(source_tensors),
        "runtime_weight_count": len(runtime_tensors),
        "unused_preserved_weight_count": len(unused_tensors),
        "source_records": source_records,
        "output_records": output_records,
        "transformations": transformations,
        "all_source_tensors_accounted_for": set(source_records) == set(output_records),
        "logical_dtype_shape_value_equal": True,
        "unused_native_tensors_preserved_byte_exact": True,
        "values_changed": False,
    }
    write_json(pending / "tensor_identity_audit.json", audit)
    write_json(pending / "config.json", config_values)
    vocab_source = engine_root / "vllm/tokenizers/assets/rwkv_vocab_v20230424.txt"
    (pending / vocab_source.name).write_bytes(vocab_source.read_bytes())
    write_json(
        pending / "tokenizer_config.json",
        {
            "bos_token": "<|endoftext|>",
            "eos_token": "<|endoftext|>",
            "pad_token": "<|endoftext|>",
            "tokenizer_class": "RWKVTokenizer",
            "vocab_file": vocab_source.name,
        },
    )
    write_json(
        pending / "special_tokens_map.json",
        {
            "bos_token": "<|endoftext|>",
            "eos_token": "<|endoftext|>",
            "pad_token": "<|endoftext|>",
        },
    )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "model": source_model,
            "path": str(source),
            "sha256": source_sha256,
            "container": "torch-pth-native-vllm-rwkv-names",
        },
        "engine": {
            "path": str(engine_root),
            "revision": revision,
            "dirty": dirty,
        },
        "purpose": "RWKV-LH independent 2.9B exact-tool Selector hidden extraction",
        "generation": {
            "script": str(Path(__file__).resolve()),
            "mapping": "identity-names-dtypes-shapes-values",
            "source_weight_count": len(source_tensors),
            "weight_count": len(runtime_tensors),
            "unused_preserved_weight_count": len(unused_tensors),
            "values_changed": False,
        },
        "output": {
            "config_sha256": file_sha256(pending / "config.json"),
            "vocab_sha256": file_sha256(pending / vocab_source.name),
            "weights_sha256": file_sha256(weights_path),
            "weights_size_bytes": weights_path.stat().st_size,
            "tensor_audit_sha256": file_sha256(pending / "tensor_identity_audit.json"),
            "unused_native_weights_sha256": file_sha256(unused_path),
            "unused_native_weights_size_bytes": unused_path.stat().st_size,
        },
    }
    write_json(pending / "manifest.json", manifest)
    (pending / "README.md").write_text(
        f"# {source_model} local vllm-rwkv artifact\n\n"
        "Value-preserving container serialization of the frozen native 2.9B "
        "checkpoint for the project-pinned local vllm-rwkv engine. Every tensor "
        "is independently audited in `tensor_identity_audit.json`.\n",
        encoding="utf-8",
    )
    os.replace(pending, output)
    print(output)


if __name__ == "__main__":
    main()
