"""Convert the frozen 0.4B RWKV7 artifact for the local vllm-rwkv engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENGINE_ROOT = Path("/home/chase/GitHub/vllm-rwkv")
DEFAULT_SOURCE = Path(
    "/home/chase/.cache/huggingface/hub/"
    "models--fla-hub--rwkv7-0.4B-g1/snapshots/"
    "b84a6a3e9f51168241c733058098cb6354d3fc04/model.safetensors"
)
DEFAULT_OUTPUT = ROOT / "data/models/rwkv7-0.4b-g1-vllm-v1"
SOURCE_MODEL = "fla-hub/rwkv7-0.4B-g1"
SOURCE_REVISION = "b84a6a3e9f51168241c733058098cb6354d3fc04"
SOURCE_SHA256 = "c6751e01566942bcc13bca06afa8476ae5ed229a3778c8f8b27bddbdf5332af3"
SCHEMA_VERSION = "rwkv-lh.vllm-rwkv-artifact.v1"


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


def engine_revision(engine_root: Path) -> tuple[str, bool]:
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


def mapped_name(name: str) -> tuple[str, bool]:
    if name == "lm_head.weight":
        return "head.weight", False
    if name == "model.embeddings.weight":
        return name, False
    if name == "model.norm.weight":
        return "model.ln_out.weight", False
    if name == "model.norm.bias":
        return "model.ln_out.bias", False
    prefix = "model.layers."
    if not name.startswith(prefix):
        raise ValueError(f"unmapped RWKV7 weight: {name}")
    layer_text, suffix = name.removeprefix(prefix).split(".", 1)
    if not layer_text.isdigit():
        raise ValueError(f"invalid RWKV7 layer weight: {name}")
    base = f"model.blocks.{layer_text}."
    direct = {
        "pre_norm.weight": "ln0.weight",
        "pre_norm.bias": "ln0.bias",
        "attn_norm.weight": "ln1.weight",
        "attn_norm.bias": "ln1.bias",
        "ffn_norm.weight": "ln2.weight",
        "ffn_norm.bias": "ln2.bias",
        "attn.g_norm.weight": "att.ln_x.weight",
        "attn.g_norm.bias": "att.ln_x.bias",
        "attn.r_proj.weight": "att.receptance.weight",
        "attn.k_proj.weight": "att.key.weight",
        "attn.v_proj.weight": "att.value.weight",
        "attn.o_proj.weight": "att.output.weight",
        "attn.r_k": "att.r_k",
        "ffn.key.weight": "ffn.key.weight",
        "ffn.value.weight": "ffn.value.weight",
    }
    if suffix in direct:
        return base + direct[suffix], False
    vector = {
        **{f"attn.x_{part}": f"att.x_{part}" for part in "rwkvag"},
        "attn.k_k": "att.k_k",
        "attn.k_a": "att.k_a",
        "ffn.x_k": "ffn.x_k",
        "attn.w_lora.lora.2.bias": "att.w0",
        "attn.a_lora.lora.2.bias": "att.a0",
        "attn.v_lora.lora.2.bias": "att.v0",
    }
    if suffix in vector:
        return base + vector[suffix], True
    for source, target in (
        ("w_lora.lora.0.weight", "w1.weight"),
        ("w_lora.lora.2.weight", "w2.weight"),
        ("a_lora.lora.0.weight", "a1.weight"),
        ("a_lora.lora.2.weight", "a2.weight"),
        ("v_lora.lora.0.weight", "v1.weight"),
        ("v_lora.lora.2.weight", "v2.weight"),
        ("g_lora.lora.0.weight", "g1.weight"),
        ("g_lora.lora.2.weight", "g2.weight"),
    ):
        if suffix == f"attn.{source}":
            return base + f"att.{target}", False
    raise ValueError(f"unmapped RWKV7 weight: {name}")


def expected_config(source_sha256: str) -> dict[str, Any]:
    return {
        "a_low_rank_dim": 64,
        "architectures": ["Rwkv7ForCausalLM"],
        "bos_token_id": 0,
        "context_length": 2048,
        "decay_low_rank_dim": 64,
        "embedding_layer_norm_fused": False,
        "eos_token_id": 0,
        "gate_low_rank_dim": 128,
        "head_size": 64,
        "hidden_size": 1024,
        "intermediate_size": 4096,
        "max_position_embeddings": 2048,
        "model_type": "rwkv7",
        "num_attention_heads": 16,
        "num_hidden_layers": 24,
        "pad_token_id": 0,
        "rwkv_source_sha256": source_sha256,
        "tie_word_embeddings": False,
        "torch_dtype": "float16",
        "v_low_rank_dim": 32,
        "vocab_size": 65536,
    }


def validate_existing(output: Path, expected_source_sha256: str) -> bool:
    manifest_path = output / "manifest.json"
    weights_path = output / "model.safetensors"
    if not manifest_path.is_file() or not weights_path.is_file():
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("source", {}).get("sha256") != expected_source_sha256
    ):
        return False
    return manifest.get("output", {}).get("weights_sha256") == file_sha256(
        weights_path
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-root", type=Path, default=DEFAULT_ENGINE_ROOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    engine_root = args.engine_root.resolve()
    source = args.source.resolve()
    output = args.output.resolve()
    if not (engine_root / "vllm/model_executor/models/rwkv7.py").is_file():
        raise ValueError(f"not a local vllm-rwkv source tree: {engine_root}")
    if not source.is_file():
        raise FileNotFoundError(f"missing frozen RWKV7 source weights: {source}")
    source_sha256 = file_sha256(source)
    if source_sha256 != SOURCE_SHA256:
        raise ValueError(
            f"source RWKV7 SHA-256 mismatch: {source_sha256} != {SOURCE_SHA256}"
        )
    if validate_existing(output, source_sha256):
        print(output)
        return
    if output.exists():
        raise FileExistsError(
            f"refusing to overwrite an unverified local model artifact: {output}"
        )

    from safetensors import safe_open
    from safetensors.torch import save_file
    from vllm.transformers_utils.configs.rwkv7 import (
        RWKV7Config,
        rwkv7_checkpoint_weight_shapes,
        validate_rwkv7_hf_artifact_config,
    )

    revision, dirty = engine_revision(engine_root)
    if dirty:
        raise RuntimeError("local vllm-rwkv source tree must be clean for conversion")
    pending = output.with_name(output.name + ".pending")
    if pending.exists():
        shutil.rmtree(pending)
    pending.mkdir(parents=True)
    tensors: dict[str, Any] = {}
    with safe_open(source, framework="pt", device="cpu") as weights:
        for source_name in weights.keys():
            target_name, reshape_vector = mapped_name(source_name)
            if target_name in tensors:
                raise ValueError(f"duplicate converted RWKV7 weight: {target_name}")
            tensor = weights.get_tensor(source_name)
            if reshape_vector and tensor.ndim == 1:
                tensor = tensor.reshape(1, 1, -1)
            tensors[target_name] = tensor.contiguous()

    config_values = expected_config(source_sha256)
    config = RWKV7Config(**config_values)
    validate_rwkv7_hf_artifact_config(config)
    expected_shapes = rwkv7_checkpoint_weight_shapes(config)
    actual_shapes = {name: tuple(tensor.shape) for name, tensor in tensors.items()}
    if set(actual_shapes) != set(expected_shapes):
        missing = sorted(set(expected_shapes) - set(actual_shapes))
        unexpected = sorted(set(actual_shapes) - set(expected_shapes))
        raise ValueError(
            f"converted RWKV7 weight keys mismatch: missing={missing} "
            f"unexpected={unexpected}"
        )
    wrong_shapes = {
        name: {"actual": actual_shapes[name], "expected": expected_shapes[name]}
        for name in expected_shapes
        if actual_shapes[name] != expected_shapes[name]
    }
    if wrong_shapes:
        raise ValueError(f"converted RWKV7 weight shapes mismatch: {wrong_shapes}")

    weights_path = pending / "model.safetensors"
    save_file(
        tensors,
        weights_path,
        metadata={
            "format": "pt",
            "rwkv_lh_conversion": SCHEMA_VERSION,
            "source_sha256": source_sha256,
        },
    )
    del tensors
    write_json(pending / "config.json", config_values)
    vocab_source = engine_root / "vllm/tokenizers/assets/rwkv_vocab_v20230424.txt"
    shutil.copyfile(vocab_source, pending / vocab_source.name)
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
            "model": SOURCE_MODEL,
            "revision": SOURCE_REVISION,
            "path": str(source),
            "sha256": source_sha256,
        },
        "engine": {
            "path": str(engine_root),
            "revision": revision,
            "dirty": dirty,
        },
        "purpose": "RWKV-LH State Router Stage 0 local vllm-rwkv inference",
        "generation": {
            "script": str(Path(__file__).resolve()),
            "mapping": SCHEMA_VERSION,
            "weight_count": len(actual_shapes),
            "values_changed": False,
        },
        "output": {
            "config_sha256": file_sha256(pending / "config.json"),
            "vocab_sha256": file_sha256(pending / vocab_source.name),
            "weights_sha256": file_sha256(weights_path),
            "weights_size_bytes": weights_path.stat().st_size,
        },
    }
    write_json(pending / "manifest.json", manifest)
    (pending / "README.md").write_text(
        "# RWKV7 0.4B local vllm-rwkv artifact\n\n"
        "This directory is a deterministic, value-preserving name/shape conversion "
        "of the frozen Stage-0 0.4B weights for the standard RWKV7 artifact contract "
        "implemented by `/home/chase/GitHub/vllm-rwkv`. Source, revision, checksums, "
        "purpose and generation method are recorded in `manifest.json`.\n",
        encoding="utf-8",
    )
    os.replace(pending, output)
    print(output)


if __name__ == "__main__":
    main()
