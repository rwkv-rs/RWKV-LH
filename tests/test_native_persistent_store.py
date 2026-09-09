"""Exercise the frozen worker's real disk export/import methods on CPU."""
import ast
import asyncio
import os
import re
import stat
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import torch
from rwkv_lh.runtime.native_state import NATIVE_STATE_LIFECYCLE_VERSION

from test_native_state_service import (
    service_module as service_module,  # noqa: PLC0414
)


def worker_module(tmp_path, capacity):
    path = Path(__file__).parents[1] / "rwkv_lh/inference/vllm_rwkv_native_worker.py"
    tree = ast.parse(path.read_text())
    names = {"RWKV7PrefixStateSnapshot", "RWKV7NativeStateEntry", "RWKV7NativeStateCache"}
    selected = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in names]
    model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RWKV7ModelState")
    methods = {"_require_native_cache", "native_state_capabilities", "_native_store_path",
               "export_native_state", "import_native_state", "_validate_native_snapshot", "_trim_native_store",
               "_native_execution_identity", "_sync_native_directory", "_ensure_native_store_directory",
               "delete_native_state_export"}
    methods.add("_initialize_native_source_identity")
    model.bases = []
    model.body = [node for node in model.body if isinstance(node, ast.FunctionDef) and node.name in methods]
    selected.append(model)
    selected[:0] = [node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "RWKV7_NATIVE_EXECUTION_IDENTITY_VERSION"
                            for target in node.targets)]
    namespace = {"__name__": __name__, "__file__": str(path), "torch": torch, "Path": Path, "os": os, "dataclass": dataclass,
                 "Any": Any, "OrderedDict": OrderedDict,
                 "RWKV7_NATIVE_STATE_FORMAT": "rwkv7-native-state-cache.v1",
                 "NATIVE_STATE_LIFECYCLE_VERSION": NATIVE_STATE_LIFECYCLE_VERSION,
                 "_SHA256_PATTERN": re.compile("^[0-9a-f]{64}$"),
                 "_NATIVE_STATE_REF_PATTERN": re.compile("^WKV-[0-9a-f]{32}$"),
                 "envs": SimpleNamespace(VLLM_RWKV7_NATIVE_STATE_DIR=str(tmp_path),
                                          VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY=capacity)}
    code = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *selected], type_ignores=[])
    exec(compile(ast.fix_missing_locations(code), str(path), "exec"), namespace)
    worker = namespace["RWKV7ModelState"]()
    worker.device = torch.device("cpu")
    worker.shift_state = torch.zeros(1, 2, 1, 4)
    worker.wkv_state = torch.zeros(1, 1, 1, 4, 4)
    worker.native_state_cache = namespace["RWKV7NativeStateCache"](8)
    worker._prefix_identity_fields = {}
    worker._native_source_identity = {"engine_manifest_sha256": "a" * 64,
                                      "project_manifest_sha256": "b" * 64}
    worker.model = SimpleNamespace(allow_fp16_accumulation=False)
    return worker, namespace


@pytest.mark.parametrize("capacity, expected", [(0, 65), (64, 64)])
def test_disk_state_retention_and_oldest_import(tmp_path, capacity, expected):
    worker, namespace = worker_module(tmp_path, capacity)
    first = None
    for index in range(65):
        snapshot = namespace["RWKV7PrefixStateSnapshot"](torch.full((1, 2, 4), float(index)),
                                                        torch.full((1, 1, 4, 4), float(index)), index)
        entry = namespace["RWKV7NativeStateEntry"]("WKV-"+f"{index:032x}", f"{index:064x}",
            "a"*64, "zero", "0"*64, 10, snapshot)
        worker.native_state_cache.put(entry)
        exported = worker.export_native_state(state_ref=entry.state_ref, store_key=entry.state_digest, worker_rank=0)
        if first is None:
            first = exported
    assert len(list((tmp_path / "rank-0").glob("*.pt"))) == expected
    assert worker.native_state_capabilities()["store_persistent"] is (capacity == 0)
    if capacity == 0:
        restored = worker.import_native_state(**{key: first[key] for key in (
            "state_ref", "state_digest", "cache_binding_digest", "state_profile_id", "state_profile_sha256",
            "pending_token_id", "processed_token_count", "store_key", "worker_rank")})
        assert restored["processed_token_count"] == 0
        assert torch.equal(worker.native_state_cache.get(first["state_ref"]).snapshot.wkv_state,
                           torch.zeros(1, 1, 4, 4))


def test_negative_disk_capacity_rejected(tmp_path):
    worker, _ = worker_module(tmp_path, -1)
    with pytest.raises(ValueError, match="nonnegative"):
        worker._trim_native_store(tmp_path)


@pytest.mark.parametrize("fail_sync", [None, "file", "directory"])
def test_export_durable_before_receipt_and_sync_failure_is_not_success(tmp_path, monkeypatch, fail_sync):
    worker, namespace = worker_module(tmp_path, 0)
    (tmp_path / "rank-0").mkdir()
    snapshot = namespace["RWKV7PrefixStateSnapshot"](torch.ones(1, 2, 4), torch.ones(1, 1, 4, 4), 0)
    entry = namespace["RWKV7NativeStateEntry"]("WKV-"+"1"*32, "a"*64, "b"*64, "zero", "0"*64, 10, snapshot)
    worker.native_state_cache.put(entry)
    events = []
    real_sync, real_replace = os.fsync, os.replace
    def sync(fd):
        kind = "directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
        events.append(kind)
        if kind == fail_sync:
            raise OSError("injected durable storage failure")
        return real_sync(fd)
    def replace(source, target):
        events.append("publish")
        return real_replace(source, target)
    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "replace", replace)
    call = lambda: worker.export_native_state(state_ref=entry.state_ref, store_key=entry.state_digest, worker_rank=0)
    if fail_sync:
        with pytest.raises(OSError, match="durable storage failure"):
            call()
        if fail_sync == "file":
            assert "publish" not in events
            assert not list((tmp_path / "rank-0").glob("*.pt"))
            # A failed private staging file must not prevent a later export
            # after the storage device recovers.
            fail_sync = None
            assert call()["store_key"] == entry.state_digest
    else:
        result = call()
        assert events.index("file") < events.index("publish")
        assert "directory" in events[events.index("publish") + 1:]
        assert result["store_key"] == entry.state_digest


def test_new_native_store_directories_are_synced_to_existing_ancestor(tmp_path, monkeypatch):
    root = tmp_path / "new-parent" / "store"
    worker, _ = worker_module(root, 0)
    synced = set()
    real_sync = os.fsync
    def sync(fd):
        identity = os.fstat(fd)
        if stat.S_ISDIR(identity.st_mode):
            synced.add((identity.st_dev, identity.st_ino))
        return real_sync(fd)
    monkeypatch.setattr(os, "fsync", sync)
    worker._native_store_path("a" * 64, 0)
    for directory in (tmp_path, tmp_path / "new-parent", root):
        identity = directory.stat()
        assert (identity.st_dev, identity.st_ino) in synced


@pytest.mark.parametrize("mutation", ["missing_identity", "other_profile", "wrong_tensor_dtype"])
def test_import_rejects_execution_mismatch_before_tensor_conversion(tmp_path, monkeypatch, mutation):
    worker, namespace = worker_module(tmp_path, 0)
    snapshot = namespace["RWKV7PrefixStateSnapshot"](torch.zeros(1, 2, 4), torch.zeros(1, 1, 4, 4), 0)
    entry = namespace["RWKV7NativeStateEntry"]("WKV-"+"1"*32, "a"*64, "b"*64, "zero", "0"*64, 10, snapshot)
    worker.native_state_cache.put(entry)
    exported = worker.export_native_state(state_ref=entry.state_ref, store_key=entry.state_digest, worker_rank=0)
    path = tmp_path / "rank-0" / (entry.state_digest+".pt")
    payload = torch.load(path, weights_only=True)
    if mutation == "missing_identity":
        payload.pop("execution_identity", None)
    elif mutation == "other_profile":
        worker._prefix_identity_fields["wkv_mode"] = "fp32io16"
    else:
        payload["wkv_state"] = payload["wkv_state"].double()
    torch.save(payload, path)
    def prohibit_conversion(*args, **kwargs):
        raise AssertionError("conversion occurred before execution identity rejection")
    monkeypatch.setattr(torch.Tensor, "to", prohibit_conversion)
    with pytest.raises(ValueError, match="execution|dtype"):
        worker.import_native_state(**{key: exported[key] for key in (
            "state_ref", "state_digest", "cache_binding_digest", "state_profile_id", "state_profile_sha256",
            "pending_token_id", "processed_token_count", "store_key", "worker_rank")})


@pytest.mark.parametrize("persistent", [False, True])
def test_journal_requires_worker_persistent_store(tmp_path, service_module, persistent, monkeypatch):
    identity = {"identity_sha256": "c" * 64}
    monkeypatch.setattr(service_module, "verify_native_source_identity", lambda **kwargs: identity)
    class Engine:
        model_config = SimpleNamespace(served_model_name="mechanism")
        renderer = SimpleNamespace(get_tokenizer=lambda: SimpleNamespace(vocab_size=100))
        async def collective_rpc(self, *args, **kwargs):
            return [{"state_format_version": service_module.STATE_FORMAT_VERSION,
                     "store_configured": True, "store_persistent": persistent,
                     "state_lifecycle_protocol": NATIVE_STATE_LIFECYCLE_VERSION,
                     "source_identity": identity}]
    service = service_module.RWKVNativeStateService(Engine(), SimpleNamespace(rwkv_native_request_journal=tmp_path / "journal.db"))
    asyncio.run(service.initialize())
    assert service.ready is persistent
    if not persistent:
        assert "persistent" in service.error
