from __future__ import annotations

import pytest
import torch

from rwkv_lh.exact_tool_selector.hierarchical_takeover_model_v5 import (
    BinaryTakeoverHeadNetwork,
    GATE_LABELS,
    TOOL_LABELS,
)


def test_binary_takeover_head_returns_two_complete_logits() -> None:
    model = BinaryTakeoverHeadNetwork.create().eval()
    with torch.no_grad():
        logits = model(torch.zeros((3, 2560)))
    assert tuple(logits.shape) == (3, 2)
    assert GATE_LABELS == ("NETWORK", "DEFER")
    assert TOOL_LABELS == ("web_search", "connector_lookup")


def test_binary_takeover_head_rejects_invalid_feature_shape() -> None:
    model = BinaryTakeoverHeadNetwork.create().eval()
    with pytest.raises(ValueError, match="feature shape"):
        model(torch.zeros((1, 2559)))
