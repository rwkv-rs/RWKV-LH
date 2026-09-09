from pathlib import Path
import hashlib
import json

import pytest
import torch

from scripts import prepare_rwkv_vllm_artifact as converter
from rwkv_lh.state_router.local_backend import ENGINE_SOURCE_MANIFEST_SCHEMA


def _shape_weights(width, heads, layers, vocab, ranks):
    shapes = {
        "emb.weight": (vocab, width), "head.weight": (vocab, width),
        "blocks.0.att.r_k": (heads, width // heads),
        "blocks.0.ffn.key.weight": (width * 4, width),
        "blocks.0.att.w1": (width, ranks[0]), "blocks.0.att.a1": (width, ranks[1]),
        "blocks.1.att.v1": (width, ranks[2]), "blocks.0.att.g1": (width, ranks[3]),
    }
    shapes.update({f"blocks.{layer}.ln1.weight": (width,) for layer in range(layers)})
    return {key: torch.empty(shape, device="meta", dtype=torch.bfloat16) for key, shape in shapes.items()}


@pytest.mark.parametrize("width,heads,layers,vocab,ranks,context", [
    (8, 2, 2, 16, (2, 3, 1, 4), 128),
    (12, 3, 3, 24, (3, 2, 4, 5), 256),
])
def test_artifact_config_follows_tensor_dimensions_not_model_names(width, heads, layers, vocab, ranks, context):
    weights = _shape_weights(width, heads, layers, vocab, ranks)
    config = converter.expected_config(weights, source_sha256="a" * 64, context_length=context)
    assert (config["hidden_size"], config["num_attention_heads"], config["num_hidden_layers"], config["vocab_size"]) == (width, heads, layers, vocab)
    assert tuple(config[key] for key in ("decay_low_rank_dim", "a_low_rank_dim", "v_low_rank_dim", "gate_low_rank_dim")) == ranks
    assert config["context_length"] == config["max_position_embeddings"] == context
    assert config["head_size"] * heads == width


def test_converter_requires_complete_uploaded_engine_identity(tmp_path: Path, monkeypatch):
    engine = tmp_path / "engine"
    engine.mkdir()
    source = engine / "engine.py"
    source.write_text("# frozen engine\n")
    manifest = tmp_path / "engine_manifest.json"
    revision = "a" * 40
    manifest.write_text(json.dumps({
        "schema_version": ENGINE_SOURCE_MANIFEST_SCHEMA, "engine_root": str(engine),
        "engine_revision": revision, "source_root": ".",
        "files": [{"path": source.name, "sha256": converter.file_sha256(source), "bytes": source.stat().st_size}],
    }))
    digest = converter.file_sha256(manifest)
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("Converter identity must not run Git or other processes"))
    identity = converter.engine_identity(engine, manifest=manifest, manifest_sha256=digest, revision=revision)
    assert identity["engine_source_manifest_sha256"] == digest
    source.write_text("# changed engine\n")
    with pytest.raises(RuntimeError, match="checksum|file set"):
        converter.engine_identity(engine, manifest=manifest, manifest_sha256=digest, revision=revision)


def test_weight_hashes_alone_cannot_validate_an_artifact(tmp_path: Path):
    paths = {
        "weights_sha256": "model.safetensors", "tensor_audit_sha256": "tensor_identity_audit.json",
        "unused_native_weights_sha256": "native_unused_layer0_value_mix.safetensors",
    }
    for name in paths.values():
        (tmp_path / name).write_bytes(b"fixture bytes; not a model")
    (tmp_path / "manifest.json").write_text(json.dumps({
        "schema_version": converter.SCHEMA_VERSION, "source": {"sha256": "a" * 64},
        "output": {key: converter.file_sha256(tmp_path / name) for key, name in paths.items()},
        "generation": {"values_changed": False},
    }))
    assert converter.validate_existing(tmp_path, "a" * 64) is False
