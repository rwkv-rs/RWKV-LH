from __future__ import annotations

from scripts.evaluate_rwkv_state_boundary_dataset import contrast_rates


def test_contrast_rates_require_four_correct_rows_per_group() -> None:
    rows = [
        {"contrast_group": "A", "operation_correct": True},
        {"contrast_group": "A", "operation_correct": True},
        {"contrast_group": "A", "operation_correct": True},
        {"contrast_group": "A", "operation_correct": True},
        {"contrast_group": "B", "operation_correct": True},
        {"contrast_group": "B", "operation_correct": False},
        {"contrast_group": "B", "operation_correct": True},
        {"contrast_group": "B", "operation_correct": True},
    ]

    assert contrast_rates(rows) == {
        "groups_seen": 2,
        "complete_groups": 2,
        "groups_with_unexpected_size": 0,
        "operation_consistent_groups": 1,
        "operation_consistency_rate": 0.5,
    }


def test_contrast_rates_report_incomplete_groups() -> None:
    result = contrast_rates(
        [{"contrast_group": "A", "operation_correct": True}] * 3
    )

    assert result["complete_groups"] == 0
    assert result["groups_with_unexpected_size"] == 1
    assert result["operation_consistency_rate"] == 0.0
