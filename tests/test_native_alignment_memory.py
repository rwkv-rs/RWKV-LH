"""Numerical admission must compare every logit without a full-size difference buffer."""
import pytest
import torch
from rwkv_lh import statetune_core


def test_alignment_difference_covers_tail_and_bounds_temporary_tensors(monkeypatch):
    left = torch.zeros(1, 193, 32)
    right = left.clone()
    right[0, -1, -1] = 0.125
    original_sub = torch.Tensor.__sub__
    sizes = []

    def limited_sub(a, b):
        sizes.append(a.numel())
        assert a.numel() <= 64 * 32, 'full-logit difference buffer exceeds audit memory bound'
        return original_sub(a, b)

    monkeypatch.setattr(torch.Tensor, '__sub__', limited_sub)
    assert statetune_core.max_logit_difference(left, right) == 0.125
    assert sizes and sum(sizes) == left.numel()
    assert torch.count_nonzero(left) == 0
    assert right[0, -1, -1] == 0.125


def test_alignment_difference_rejects_nonfinite_tail():
    left = torch.zeros(1, 129, 4)
    right = left.clone()
    assert statetune_core.max_logit_difference(left, right) == 0.0
    right[0, -1, -1] = float('nan')
    with pytest.raises(ValueError, match='finiteness'):
        statetune_core.max_logit_difference(left, right)
