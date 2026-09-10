"""Reconstruction must use the complete production registry without executing tools."""
from pathlib import Path

import requests

from rwkv_lh import role_trace_inputs
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.retrieval.runtime import RetrievalRuntimeConfig, build_product_harness
from rwkv_lh.retrieval.policy import NetworkPolicyMode


def test_trace_reconstruction_has_the_same_complete_tool_definitions_without_io(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("definition reconstruction attempted I/O")
    monkeypatch.setattr(requests.Session, "send", forbidden)
    production = build_product_harness(config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE),
        snapshot_root=tmp_path / "snapshots", stable_network_menu=True)
    expected = production.g1i_tool_definitions(NETWORK_EXACT_TOOL_LABELS)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    reconstructed = role_trace_inputs._reconstruction_harness()
    assert reconstructed.g1i_tool_definitions(NETWORK_EXACT_TOOL_LABELS) == expected
    assert len(expected) == len(NETWORK_EXACT_TOOL_LABELS)
