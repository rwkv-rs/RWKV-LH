"""Native restart identity binds verified source contents, beyond dtype/profile."""
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from rwkv_lh.inference.native_source_identity import verify_native_source_identity
from test_native_persistent_store import worker_module
from test_native_state_service import (
    service_module as service_module,  # noqa: PLC0414
)


@pytest.mark.parametrize("field", ["engine_manifest_sha256", "project_manifest_sha256"])
def test_same_profile_different_source_cannot_restore_state(tmp_path, field):
    worker, namespace = worker_module(tmp_path, 0)
    worker._native_source_identity = {
        "engine_manifest_sha256": "a" * 64,
        "project_manifest_sha256": "b" * 64,
    }
    snapshot = namespace["RWKV7PrefixStateSnapshot"](
        torch.ones(1, 2, 4), torch.ones(1, 1, 4, 4), 0)
    entry = namespace["RWKV7NativeStateEntry"](
        "WKV-" + "1" * 32, "a" * 64, "b" * 64, "zero", "0" * 64, 10, snapshot)
    worker.native_state_cache.put(entry)
    exported = worker.export_native_state(
        state_ref=entry.state_ref, store_key=entry.state_digest, worker_rank=0)
    worker._native_source_identity[field] = "c" * 64
    with pytest.raises(ValueError, match="execution identity"):
        worker.import_native_state(**{key: exported[key] for key in (
            "state_ref", "state_digest", "cache_binding_digest", "state_profile_id",
            "state_profile_sha256", "pending_token_id", "processed_token_count",
            "store_key", "worker_rank")})


def test_native_startup_without_source_manifests_is_not_ready(tmp_path, monkeypatch, service_module):
    for key in ("RWKV_NATIVE_ENGINE_SOURCE_MANIFEST", "RWKV_NATIVE_ENGINE_SOURCE_MANIFEST_SHA256",
                "RWKV_NATIVE_PROJECT_SOURCE_MANIFEST", "RWKV_NATIVE_PROJECT_SOURCE_MANIFEST_SHA256"):
        monkeypatch.delenv(key, raising=False)
    class Engine:
        model_config = SimpleNamespace(served_model_name="mechanism")
        renderer = SimpleNamespace(get_tokenizer=lambda: SimpleNamespace(vocab_size=100))
        async def collective_rpc(self, *args, **kwargs):
            return [{"state_format_version": service_module.STATE_FORMAT_VERSION,
                     "store_configured": True, "store_persistent": True}]
    service = service_module.RWKVNativeStateService(
        Engine(), SimpleNamespace(rwkv_native_request_journal=tmp_path / "journal.db"))
    asyncio.run(service.initialize())
    assert not service.ready
    assert "source" in service.error.lower()


@pytest.fixture
def sealed_sources(tmp_path, monkeypatch):
    files, manifests = {}, {}
    for scope in ("engine", "project"):
        root = tmp_path / scope
        root.mkdir()
        source = root / "module.py"
        source.write_text("# frozen mechanism module\n")
        manifest = tmp_path / f"{scope}-manifest.json"
        value = {"schema_version": f"rwkv-lh.uploaded-{scope}-source-manifest.v1",
                 f"{scope}_root": str(root), "source_root": ".",
                 "files": [{"path": "module.py", "bytes": source.stat().st_size,
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}]}
        if scope == "engine":
            value["engine_revision"] = "a" * 40
        manifest.write_text(json.dumps(value))
        monkeypatch.setenv(f"RWKV_NATIVE_{scope.upper()}_SOURCE_MANIFEST", str(manifest))
        monkeypatch.setenv(f"RWKV_NATIVE_{scope.upper()}_SOURCE_MANIFEST_SHA256",
                           hashlib.sha256(manifest.read_bytes()).hexdigest())
        files[scope], manifests[scope] = source, manifest
    def verify(**_kwargs):
        return verify_native_source_identity(engine_file=files["engine"], project_file=files["project"])
    return files, manifests, verify


@pytest.mark.parametrize("mutation", ["none", "engine_bytes", "project_bytes",
                                      "engine_manifest", "project_manifest", "worker_identity"])
def test_native_startup_and_attestation_require_matching_actual_sources(
    tmp_path, monkeypatch, service_module, sealed_sources, mutation,
):
    files, manifests, verify = sealed_sources
    identity = verify()
    worker_identity = dict(identity)
    if mutation.endswith("_bytes"):
        files[mutation.split("_")[0]].write_text("changed implementation\n")
    elif mutation.endswith("_manifest"):
        target = manifests[mutation.split("_")[0]]
        target.write_bytes(target.read_bytes() + b"\n")
    elif mutation == "worker_identity":
        worker_identity["engine_manifest_sha256"] = "c" * 64
    monkeypatch.setattr(service_module, "verify_native_source_identity", verify)
    class Engine:
        model_config = SimpleNamespace(served_model_name="mechanism")
        renderer = SimpleNamespace(get_tokenizer=lambda: SimpleNamespace(vocab_size=100))
        async def collective_rpc(self, *args, **kwargs):
            return [{"state_format_version": service_module.STATE_FORMAT_VERSION,
                     "store_configured": True, "store_persistent": True,
                     "state_lifecycle_protocol": service_module.NATIVE_STATE_LIFECYCLE_VERSION,
                     "source_identity": worker_identity}]
    service = service_module.RWKVNativeStateService(
        Engine(), SimpleNamespace(rwkv_native_request_journal=tmp_path / "journal.db"))
    asyncio.run(service.initialize())
    assert service.ready is (mutation == "none")
    if mutation == "none":
        assert service.server_build == "mechanism-engine+native." + identity["identity_sha256"]
        assert service.capabilities()["server_build"] == service.server_build
    else:
        assert "source" in service.error.lower()


def test_loaded_modules_must_belong_to_verified_source_tree(sealed_sources):
    files, _, _ = sealed_sources
    with pytest.raises(RuntimeError, match="loaded module"):
        verify_native_source_identity(engine_file=Path(__file__), project_file=files["project"])


def test_native_disabled_worker_does_not_require_source_configuration(tmp_path, monkeypatch):
    worker, _ = worker_module(tmp_path, 0)
    worker.native_state_cache = None
    def forbidden(**_kwargs):
        raise AssertionError("Native-disabled worker requested source configuration")
    monkeypatch.setattr("rwkv_lh.inference.native_source_identity.verify_native_source_identity", forbidden)
    worker._initialize_native_source_identity()
    assert worker._native_source_identity == {}


def test_project_worker_verifies_loaded_engine_and_own_project_source(tmp_path, monkeypatch):
    worker, namespace = worker_module(tmp_path, 0)
    engine_file = str(tmp_path / "uploaded_engine/vllm/__init__.py")
    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(__file__=engine_file))
    calls = []
    def verify(**kwargs):
        calls.append(kwargs)
        return {"identity_sha256": "c" * 64}
    monkeypatch.setattr("rwkv_lh.inference.native_source_identity.verify_native_source_identity", verify)
    worker._initialize_native_source_identity()
    assert calls == [{"engine_file": engine_file, "project_file": namespace["__file__"]}]
    assert worker._native_source_identity == {"identity_sha256": "c" * 64}


def test_native_enabled_worker_fails_when_source_configuration_is_missing(tmp_path, monkeypatch):
    worker, _ = worker_module(tmp_path, 0)
    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(__file__=str(tmp_path / "vllm/__init__.py")))
    monkeypatch.delenv("RWKV_NATIVE_ENGINE_SOURCE_MANIFEST", raising=False)
    with pytest.raises(RuntimeError, match="Native source configuration"):
        worker._initialize_native_source_identity()


@pytest.mark.parametrize("missing", ["ENGINE_SOURCE_MANIFEST", "ENGINE_SOURCE_MANIFEST_SHA256",
                                     "PROJECT_SOURCE_MANIFEST", "PROJECT_SOURCE_MANIFEST_SHA256"])
def test_each_native_source_configuration_field_is_required(sealed_sources, monkeypatch, missing):
    _, _, verify = sealed_sources
    monkeypatch.delenv("RWKV_NATIVE_" + missing)
    with pytest.raises(RuntimeError, match="Native source configuration"):
        verify()


def test_same_verified_source_identity_restores_after_worker_restart(tmp_path, sealed_sources):
    _, _, verify = sealed_sources
    worker, namespace = worker_module(tmp_path / "store", 0)
    worker._native_source_identity = verify()
    snapshot = namespace["RWKV7PrefixStateSnapshot"](
        torch.ones(1, 2, 4), torch.full((1, 1, 4, 4), 7.0), 2)
    entry = namespace["RWKV7NativeStateEntry"](
        "WKV-" + "1" * 32, "a" * 64, "b" * 64, "zero", "0" * 64, 10, snapshot)
    worker.native_state_cache.put(entry)
    exported = worker.export_native_state(state_ref=entry.state_ref, store_key=entry.state_digest, worker_rank=0)
    restarted, _ = worker_module(tmp_path / "store", 0)
    restarted._native_source_identity = verify()
    restarted.import_native_state(**{key: exported[key] for key in (
        "state_ref", "state_digest", "cache_binding_digest", "state_profile_id", "state_profile_sha256",
        "pending_token_id", "processed_token_count", "store_key", "worker_rank")})
    assert torch.equal(restarted.native_state_cache.get(entry.state_ref).snapshot.wkv_state,
                       snapshot.wkv_state)
