"""Native worker uses the same immutable State registry as Selector and training."""
import ast
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from rwkv_lh.inference import vllm_rwkv_state_profiles_v1 as profiles


def worker_profile_namespace():
    path = Path(__file__).parents[1] / "rwkv_lh/inference/vllm_rwkv_native_worker.py"
    tree = ast.parse(path.read_text())
    types = {"RWKV7InitialStateProfile", "RWKV7InitialStateProfiles"}
    nodes = [node for node in tree.body if (
        isinstance(node, ast.ImportFrom) and node.module == profiles.__name__
        or isinstance(node, ast.ClassDef) and node.name in types
    )]
    model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "RWKV7ModelState")
    model.bases = []
    model.body = [node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == "add_request"]
    namespace = {"torch": torch, "dataclass": dataclass,
                 "RWKV7_ZERO_STATE_PROFILE": profiles.RWKV7_ZERO_STATE_PROFILE,
                 "RWKV7_STATE_PROFILE_XARG": profiles.RWKV7_STATE_PROFILE_XARG,
                 "RWKV7_STATE_PROFILE_SHA256_XARG": profiles.RWKV7_STATE_PROFILE_SHA256_XARG}
    nodes.insert(0, ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[*nodes, model], type_ignores=[])), str(path), "exec"), namespace)
    return namespace


def test_native_and_selector_share_the_actual_profile_types():
    namespace = worker_profile_namespace()
    assert namespace["RWKV7InitialStateProfile"] is profiles.RWKV7InitialStateProfile
    assert namespace["RWKV7InitialStateProfiles"] is profiles.RWKV7InitialStateProfiles


def test_native_rejects_implicit_profile_before_allocating_a_row():
    namespace = worker_profile_namespace()
    worker = namespace["RWKV7ModelState"]()
    worker.max_num_reqs = 1
    worker.req_id_to_index = {}
    worker.req_slot_owners = [None]
    worker.free_rows = {0}
    zero = profiles.RWKV7InitialStateProfiles.zero_only()
    worker.initial_state_profiles = profiles.RWKV7InitialStateProfiles(
        {"zero": zero.resolve("zero")}, "zero", requires_explicit_request_profile=True)
    request = SimpleNamespace(req_id="request-without-profile", sampling_params=SimpleNamespace(extra_args={}))
    with pytest.raises(ValueError, match="explicitly select"):
        worker.add_request(0, request)
    assert worker.free_rows == {0}
