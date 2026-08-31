from __future__ import annotations

import pytest
import torch

from rwkv_lh.exact_tool_selector.objective_gate_model_v6 import (
    GATE_LABELS,
    ObjectiveGateNetwork,
)


@pytest.mark.parametrize("input_dim", [2560, 5120])
def test_objective_gate_network_returns_two_raw_logits(input_dim: int) -> None:
    model = ObjectiveGateNetwork.create(input_dim).eval()
    with torch.no_grad():
        logits = model(torch.zeros((2, input_dim)))
    assert tuple(logits.shape) == (2, 2)
    assert GATE_LABELS == ("NETWORK", "DEFER")


def test_objective_gate_network_rejects_unknown_feature_width() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        ObjectiveGateNetwork.create(3000)
