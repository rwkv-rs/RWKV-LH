from __future__ import annotations

from scripts.evaluate_executor_state_tuning_v2_dev import (
    evaluation_cluster,
    final_required_facts,
)


def test_multistage_evaluator_uses_declared_family_without_inference() -> None:
    assert (
        evaluation_cluster(
            {
                "critical_multistage_family": "observe_multiple_inputs_before_write",
                "source_kind": "synthetic_multistage_request_last",
            }
        )
        == "observe_multiple_inputs_before_write"
    )
    assert (
        evaluation_cluster({"source_kind": "synthetic_multistage_request_last"})
        == "synthetic_multistage_request_last"
    )


def test_multistage_final_answer_does_not_invent_hidden_required_facts() -> None:
    rows = [
        {
            "sample_id": "EXEG3-DEV-FINAL-000",
            "selected_operation": "final_answer",
            "target": '{"function":"final_answer","params":{"text":"done"}}',
        }
    ]
    assert final_required_facts(rows) == {}
