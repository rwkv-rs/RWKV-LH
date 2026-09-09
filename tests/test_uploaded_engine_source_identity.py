from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from rwkv_lh.state_router import local_backend as backend


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def deployment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = tmp_path / "engine"
    source = engine / "vllm/model_executor/models/rwkv7.py"
    source.parent.mkdir(parents=True)
    source.write_text("# frozen engine source\n")
    (engine / "vllm/__init__.py").write_text("__version__ = 'test'\n")
    (engine / "vllm/_build_profile.json").write_text('{"profile": "test"}\n')
    (engine / "setup.py").write_text("# frozen package build\n")
    python = engine / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexit 1\n")
    python.chmod(0o755)
    model = tmp_path / "model"
    model.mkdir()
    (model / "config.json").write_text(json.dumps({
        "architectures": ["Rwkv7ForCausalLM"], "hidden_size": 8,
        "num_hidden_layers": 2, "head_size": 4, "vocab_size": 16,
    }))
    (model / "model.safetensors").write_bytes(b"fake weights, never loaded")
    (model / "rwkv_vocab_v20230424.txt").write_text("fake vocabulary\n")
    revision = "a" * 40
    (model / "manifest.json").write_text(json.dumps({
        "schema_version": backend.MODEL_MANIFEST_SCHEMA,
        "engine": {"revision": revision}, "source": {"model": "fixture"},
        "output": {"config_sha256": _sha(model / "config.json"),
                   "vocab_sha256": _sha(model / "rwkv_vocab_v20230424.txt"),
                   "weights_sha256": _sha(model / "model.safetensors")},
    }))
    manifest = tmp_path / "engine-source.json"
    manifest.write_text(json.dumps({
        "schema_version": "rwkv-lh.uploaded-engine-source-manifest.v1",
        "engine_root": str(engine), "engine_revision": revision,
        "source_root": ".",
        "files": [{"path": name, "sha256": _sha(engine / name),
                   "bytes": (engine / name).stat().st_size}
                  for name in ("setup.py", "vllm/__init__.py", "vllm/_build_profile.json",
                               "vllm/model_executor/models/rwkv7.py")],
    }))
    calls = []

    def no_git(*_args, **_kwargs):
        raise AssertionError("Git must not be invoked for uploaded engines")

    def probe(args, **kwargs):
        calls.append(args)
        assert args[0] == str(python), "only the dependency import probe is allowed"
        return subprocess.CompletedProcess(args, 0, json.dumps({
            "torch": "fixture", "transformers": "fixture", "vllm": "fixture",
            "module": str(engine / "vllm/__init__.py"),
        }) + "\n", "")

    monkeypatch.setattr(backend, "_git_value", no_git)
    monkeypatch.setattr(backend.subprocess, "run", probe)
    settings = backend.LocalVLLMRWKVSettings(
        engine_root=engine, engine_revision=revision, engine_python=python,
        model=model, runtime_temp=tmp_path / "runtime", compatibility_sha256="0" * 64,
        engine_source_manifest=manifest, engine_source_manifest_sha256=_sha(manifest),
    )
    return settings, manifest, engine, calls


def test_uploaded_engine_loads_identity_without_git(deployment) -> None:
    settings, manifest, _engine, calls = deployment
    identity = backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert identity["engine_revision"] == settings.engine_revision
    assert identity["engine_source_manifest_sha256"] == _sha(manifest)
    assert identity["engine_dirty"] is None
    assert identity["engine_identity_backend"] == "uploaded_source_manifest"
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["edited", "added", "shadow", "deleted", "symlink", "bytecode"])
def test_uploaded_engine_rejects_source_set_or_content_changes(deployment, change: str) -> None:
    settings, _manifest, engine, calls = deployment
    target = engine / "vllm/model_executor/models/rwkv7.py"
    if change == "edited":
        target.write_text("# changed source\n")
    elif change == "added":
        (engine / "vllm/new_module.py").write_text("pass\n")
    elif change == "shadow":
        (engine / "transformers.py").write_text("pass\n")
    elif change == "deleted":
        (engine / "setup.py").unlink()
    elif change == "symlink":
        target.unlink()
        target.symlink_to(engine / "vllm/__init__.py")
    else:
        (engine / "transformers.pyc").write_bytes(b"sourceless shadow module")
    with pytest.raises(RuntimeError, match="engine source"):
        backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert not calls


def test_uploaded_engine_rejects_manifest_checksum_mismatch(deployment) -> None:
    settings, manifest, _engine, calls = deployment
    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(RuntimeError, match="engine source manifest checksum"):
        backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert not calls


@pytest.mark.parametrize("field,value", [
    ("engine_revision", "b" * 40), ("source_root", "vllm"),
    ("engine_root", "/different/deployment"), ("schema_version", "unknown"),
])
def test_uploaded_engine_rejects_manifest_identity_changes(deployment, field, value) -> None:
    settings, manifest, _engine, calls = deployment
    data = json.loads(manifest.read_text())
    data[field] = value
    manifest.write_text(json.dumps(data))
    settings = replace(settings, engine_source_manifest_sha256=_sha(manifest))
    with pytest.raises(RuntimeError, match="engine source manifest"):
        backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert not calls


@pytest.mark.parametrize("path", ["../escape.py", "/absolute.py", "vllm/../escape.py", "vllm\\escape.py"])
def test_uploaded_engine_rejects_noncanonical_manifest_paths(deployment, path) -> None:
    settings, manifest, _engine, calls = deployment
    data = json.loads(manifest.read_text())
    data["files"][0]["path"] = path
    manifest.write_text(json.dumps(data))
    settings = replace(settings, engine_source_manifest_sha256=_sha(manifest))
    with pytest.raises(RuntimeError, match="engine source manifest"):
        backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert not calls


def test_uploaded_engine_ignores_only_non_source_directories(deployment) -> None:
    settings, _manifest, engine, _calls = deployment
    for name in (".git", "__pycache__"):
        directory = engine / name
        directory.mkdir()
        (directory / "generated").write_text("runtime metadata")
    backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()


def test_uploaded_engine_still_requires_build_profile(deployment) -> None:
    settings, manifest, engine, calls = deployment
    (engine / "vllm/_build_profile.json").unlink()
    data = json.loads(manifest.read_text())
    data["files"] = [entry for entry in data["files"] if entry["path"] != "vllm/_build_profile.json"]
    manifest.write_text(json.dumps(data))
    settings = replace(settings, engine_source_manifest_sha256=_sha(manifest))
    with pytest.raises(RuntimeError, match="immutable build profile"):
        backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert not calls


def test_local_development_without_manifest_retains_git_checks(deployment, monkeypatch: pytest.MonkeyPatch) -> None:
    settings, _manifest, _engine, _calls = deployment
    settings = replace(settings, engine_source_manifest=None, engine_source_manifest_sha256="")
    git_calls = []

    def git_value(_root, *args):
        git_calls.append(args)
        return settings.engine_revision if args == ("rev-parse", "HEAD") else ""

    monkeypatch.setattr(backend, "_git_value", git_value)
    identity = backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()
    assert identity["engine_dirty"] is False
    assert "engine_source_manifest_sha256" not in identity
    assert git_calls == [("rev-parse", "HEAD"), ("status", "--short")]
    monkeypatch.setattr(backend, "_git_value", lambda _root, *args: settings.engine_revision if args[0] == "rev-parse" else " M changed.py")
    with pytest.raises(RuntimeError, match="source tree must be clean"):
        backend.LocalVLLMRWKVExtractor(settings)._load_base_identity()


@pytest.mark.parametrize("kwargs", [
    {"engine_source_manifest": Path("engine-source.json")},
    {"engine_source_manifest_sha256": "a" * 64},
    {"engine_source_manifest": Path("engine-source.json"), "engine_source_manifest_sha256": "invalid"},
])
def test_uploaded_engine_requires_manifest_and_sha256(kwargs) -> None:
    with pytest.raises(ValueError, match="engine source"):
        backend.LocalVLLMRWKVSettings(**kwargs)


def test_native_selector_cli_forwards_uploaded_source_identity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from rwkv_lh.exact_tool_selector import native_network_service as service

    captured = []
    manifest = tmp_path / "source.json"
    (tmp_path / "model").mkdir()
    (tmp_path / "model/config.json").write_text(json.dumps({"context_length": 16384, "max_position_embeddings": 16384}))

    class Extractor:
        def __init__(self, settings):
            captured.append(settings)

        def load(self):
            pass

    class Server:
        def __init__(self, *_args):
            pass

        def serve_forever(self):
            pass

    monkeypatch.setattr(service, "load_native_selector_decoder_manifest", lambda *_: {})
    monkeypatch.setattr(service, "NativeNetworkSelectorService", lambda *_: object())
    monkeypatch.setattr(service, "_handler", lambda *_: object())
    monkeypatch.setattr(service, "PersistentVLLMRWKVExtractor", Extractor)
    monkeypatch.setattr(service, "ThreadingHTTPServer", Server)
    monkeypatch.setattr(sys, "argv", [
        "selector-service", "--engine-root", str(tmp_path / "engine"),
        "--engine-revision", "a" * 40, "--engine-python", sys.executable,
        "--engine-source-manifest", str(manifest),
        "--engine-source-manifest-sha256", "c" * 64,
        "--model-artifact", str(tmp_path / "model"), "--model-name", "fixture",
        "--model-sha256", "b" * 64, "--decoder-manifest", str(tmp_path / "decoder.json"),
        "--decoder-sha256", "d" * 64, "--runtime-temp", str(tmp_path / "runtime"),
    ])
    assert service.main() == 0
    assert captured[0].engine_source_manifest == manifest
    assert captured[0].engine_source_manifest_sha256 == "c" * 64
    assert captured[0].max_tokens == 16384
    assert captured[0].wkv_mode == "fp32io16"
