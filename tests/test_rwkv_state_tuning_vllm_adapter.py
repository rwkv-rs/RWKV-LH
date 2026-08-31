from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = (
    ROOT
    / "data"
    / "experiments"
    / "RWKV_ACTION_STATE_TUNING_ROUND1_2K_V1_20260826"
    / "rwkv_state_tuning_adapter_sitecustomize.py"
)


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing adapter function: {name}")


def test_vllm_adapter_preserves_rwkv_peft_vk_orientation() -> None:
    """Protect the kernel-proven PEFT [V,K] -> vLLM [V,K] contract."""

    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"), filename=str(ADAPTER))
    loader = _function(tree, "_load_initial_wkv_state")
    orientation_changers = {
        node.func.attr
        for node in ast.walk(loader)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"transpose", "permute", "swapaxes", "swapdims", "mT"}
    }
    assert not orientation_changers

    orientation_attestations = [
        keyword.value.value
        for node in ast.walk(loader)
        if isinstance(node, ast.Call)
        for keyword in node.keywords
        if keyword.arg == "state_orientation"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    ]
    assert orientation_attestations == ["rwkv_peft_parameter_v_k_direct"]


def test_vllm_adapter_initializes_real_dummy_and_reset_rows_from_same_state() -> None:
    tree = ast.parse(ADAPTER.read_text(encoding="utf-8"), filename=str(ADAPTER))
    functions = {
        name: ast.unparse(_function(tree, name))
        for name in ("_stateful_zero_row", "_stateful_new_dummy", "_stateful_reset")
    }
    assert "self.wkv_state[:, row].copy_(initial)" in functions["_stateful_zero_row"]
    assert "initial[:, None].expand" in functions["_stateful_new_dummy"]
    assert "initial[:, None].expand" in functions["_stateful_reset"]
