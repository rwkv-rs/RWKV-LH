from __future__ import annotations

import json

import pytest

from rwkv_lh.model_io import ModelCommand, TOOL_CALL_JSON_CONTINUATION_ANCHOR
from rwkv_lh.goal_state_protocols import auditor_final
from rwkv_lh.goal_state_protocols import auditor_step
from rwkv_lh.goal_state_protocols import executor_args
from rwkv_lh.goal_state_protocols import finalizer_answer
from rwkv_lh.goal_state_protocols import selector_intent


def _progress() -> dict[str, object]:
    return {
        "completed_stage_count": 1,
        "action_index": 2,
        "succeeded_operations": ["read_file"],
        "failed_operations": [],
        "protocol_rejection_count": 0,
    }


def _step() -> dict[str, object]:
    return {
        "step_id": "S1",
        "objective": "Read the registered file",
        "stage": "observe",
        "depends_on": [],
        "success_evidence": ["file contents observed"],
        "obligation_ids": ["O1"],
        "read_roots": ["README.md"],
        "write_roots": [],
        "allowed_operations": ["read_file"],
        "constraints": [],
    }


def _completed_steps() -> list[dict[str, object]]:
    return [{"step_id": "S1", "evidence_refs": ["A1"]}]


def _facts() -> list[dict[str, object]]:
    return [{"fact_id": "F1", "value": "ok", "evidence_refs": ["A1"]}]


def _evidence() -> list[dict[str, object]]:
    return [{"evidence_ref": "A1", "kind": "action", "value": "ok"}]


def test_protocol_schema_identities_are_frozen_without_historical_versions() -> None:
    expected = {
        selector_intent: "selector-intent",
        executor_args: "executor-args",
        auditor_step: "auditor-step",
        finalizer_answer: "finalizer-answer",
        auditor_final: "auditor-final",
    }
    for module, stage in expected.items():
        version = "v2" if module is selector_intent else "v1"
        identity = f"rwkv-lh.g1j-per-stage-state-tuning.{stage}.{version}"
        assert module.INPUT_SCHEMA_VERSION == identity
        assert module.OUTPUT_SCHEMA_VERSION == identity
        assert all(marker not in identity for marker in (".v6", ".v7", ".v8"))


def test_selector_intent_exact_suffix_and_current_subtask_boundary() -> None:
    source = {
        "current_subtask": {
            "objective": "Read one file",
            "phase": "observe",
            "read_roots": ["README.md"],
            "write_roots": [],
            "success_evidence": ["file contents observed"],
            "constraints": [],
        },
        "eligible_labels": ["read_file"],
        "selected_operation": "read_file",
        "selection_authority": "executed_fixture",
        "selection_verifier_id": "selection-verifier-v1",
    }
    prompt = selector_intent.render_prompt(source)
    target = selector_intent.render_target(source)
    assert target == "\nSelectorIntentV2: read_file"
    assert selector_intent.parse_target(target) == "read_file"
    assert "selected_operation" not in prompt
    with pytest.raises(ValueError, match="fields/order"):
        selector_intent.validate_source(
            {**source, "progress": _progress()}
        )


def test_executor_args_round_trip_and_role_boundary() -> None:
    source = {
        "current_requirement": "Read one file",
        "selected_operation": "read_file",
        "selected_tool_contract": {
            "name": "read_file",
            "description": "Read a file",
            "parameters": {"type": "object"},
        },
        "committed_fact_refs": ["A1"],
        "executor_history": [{"event_id": "E1", "operation": "list_directory"}],
        "command": {"function": "read_file", "params": {"path": "README.md"}},
        "fixture_id": "fixture-1",
        "execution_verifier_id": "execution-verifier-v1",
    }
    prompt = executor_args.render_prompt(source)
    generation_prompt = executor_args.render_generation_prompt(source)
    target = executor_args.render_target(source)
    assert executor_args.parse_target(target).name == "read_file"
    assert "fixture_id" not in prompt
    assert generation_prompt == prompt + TOOL_CALL_JSON_CONTINUATION_ANCHOR
    with pytest.raises(ValueError, match="terminal"):
        executor_args.parse_target('{"function":"final_answer","params":{"text":"x"}}')


def test_step_auditor_round_trip_and_no_final_verdict() -> None:
    source = {
        "boundary": "observation_complete",
        "active_step": _step(),
        "available_evidence_refs": ["A1"],
        "evidence_records": _evidence(),
        "decision": {
            "verdict": "continue",
            "step_id": "S1",
            "step_complete": True,
            "evidence_refs": ["A1"],
            "gaps": [],
            "reason": "Evidence satisfies the step.",
        },
        "completion_verifier_id": "completion-verifier-v1",
    }
    prompt = auditor_step.render_prompt(source)
    target = auditor_step.render_target(source)
    assert auditor_step.parse_target(target).arguments["verdict"] == "continue"
    assert "completion_verifier_id" not in prompt
    step_question = json.loads(
        prompt.removeprefix("AuditorStepPromptV1: ")
    )["current_question"]
    assert "exactly these six fields" in step_question
    assert "evidence_refs and gaps arrays" in step_question
    with pytest.raises(ValueError, match="one of"):
        auditor_step.parse_target(
            ModelCommand(
                "audit_decision",
                {
                    "verdict": "ready_for_final",
                    "step_id": "",
                    "step_complete": False,
                    "evidence_refs": ["A1"],
                    "gaps": [],
                    "reason": "done",
                },
            ).canonical
        )


def test_finalizer_round_trip_has_no_completion_authority() -> None:
    source = {
        "immutable_goal": "Report the observed value",
        "completed_steps": _completed_steps(),
        "committed_facts": _facts(),
        "evidence_records": _evidence(),
        "format_contract": {
            "format_id": "plain-v1",
            "language": "en",
            "required_sections": [],
        },
        "final_text": "The observed value is ok.",
        "fact_verifier_id": "fact-verifier-v1",
    }
    prompt = finalizer_answer.render_prompt(source)
    target = finalizer_answer.render_target(source)
    assert finalizer_answer.parse_target(target).arguments == {
        "text": "The observed value is ok."
    }
    assert "fact_verifier_id" not in prompt
    assert "COMPLETED" not in prompt


def test_final_auditor_round_trip_and_repair_semantics() -> None:
    source = {
        "immutable_goal": "Report the observed value",
        "completed_steps": _completed_steps(),
        "committed_facts": _facts(),
        "available_evidence_refs": ["A1"],
        "evidence_records": _evidence(),
        "final_candidate": {
            "function": "final_answer",
            "params": {"text": "The observed value is ok."},
        },
        "decision": {
            "verdict": "ready_for_final",
            "step_id": "",
            "step_complete": False,
            "evidence_refs": ["A1"],
            "gaps": [],
            "reason": "All committed facts are covered.",
        },
        "final_verifier_id": "final-verifier-v1",
    }
    prompt = auditor_final.render_prompt(source)
    target = auditor_final.render_target(source)
    assert auditor_final.parse_target(target).arguments["verdict"] == "ready_for_final"
    assert "final_verifier_id" not in prompt
    prompt_payload = json.loads(prompt.removeprefix("AuditorFinalPromptV1: "))
    question = prompt_payload["current_question"]
    assert "exactly these six fields" in question
    assert "evidence_refs and gaps arrays" in question
    assert "ready_for_final only" in question
    invalid = dict(source)
    invalid["decision"] = {
        **source["decision"],
        "verdict": "repair",
        "gaps": [],
    }
    with pytest.raises(ValueError, match="non-empty gaps"):
        auditor_final.validate_source(invalid)


def test_source_field_order_is_part_of_every_protocol() -> None:
    source = {
        "stage_role": "tool_intent",
        "stage_objective": "Read one file",
        "progress": _progress(),
        "eligible_labels": ["read_file"],
        "selected_operation": "read_file",
        "selection_authority": "executed_fixture",
        "selection_verifier_id": "selection-verifier-v1",
    }
    with pytest.raises(ValueError, match="fields/order"):
        selector_intent.validate_source(source)
