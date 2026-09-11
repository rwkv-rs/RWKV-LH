from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from rwkv_lh.model_io import ModelCommand, TOOL_CALL_JSON_CONTINUATION_ANCHOR
from rwkv_lh.goal_state_protocols import auditor_final
from rwkv_lh.goal_state_protocols import auditor_step_v7
from rwkv_lh.goal_state_protocols import executor_args_v7
from rwkv_lh.goal_state_protocols import finalizer_answer
from rwkv_lh.goal_state_protocols import selector_intent_v7


def _selector_source() -> dict[str, object]:
    action = SimpleNamespace(
        action_type="read_json", status=SimpleNamespace(value="failed"),
        arguments={"path": "README.md"},
        result={
            "success": False, "outcome_type": "failed",
            "error": {"type": "JSONDecodeError",
                      "message": "Expecting value: line 1 column 1 (char 0)"},
        },
    )
    progress = selector_intent_v7.build_current_progress(
        assigned_actions=[action], read_roots=["README.md"], write_roots=[],
        mechanical_evidence={"missing_read_roots": ["README.md"]},
        target_descriptors=[{"path": "README.md", "target_kind": "text_file"}],
        action_observes_root=lambda *_: False, action_mutates_root=lambda *_: False,
    )
    source = selector_intent_v7.build_prompt_source(
        current_subtask={
            "objective": "Read one file", "phase": "observe",
            "read_roots": ["README.md"], "write_roots": [],
            "success_evidence": ["file contents observed"], "constraints": [],
        },
        current_progress=progress, eligible_labels=["read_file", "read_json"],
    )
    source.update(selected_operation="read_file", selection_authority="executed_fixture",
                  selection_verifier_id="selection-verifier-v1")
    return source


def _step() -> dict[str, object]:
    return {
        "step_id": "S1",
        "objective": "Read the registered file",
        "phase": "observe",
        "stage": 1,
        "depends_on": [],
        "success_evidence": ["file contents observed"],
        "obligation_ids": ["O1"],
        "read_roots": ["README.md"],
        "write_roots": [],
        "allowed_operations": ["read_file"],
        "constraints": [],
    }


def _execution_state(*, assigned_actions=()) -> dict[str, object]:
    return executor_args_v7.build_execution_state(
        active_step_id="S1", active_step_revision=1,
        declared_phase="observe", effective_phase="observe",
        assigned_actions=assigned_actions,
        mechanical_evidence={"missing_read_roots": ["README.md"]},
        target_contract=_typed_target_contract(),
    )


def _executor_source(*, assigned_actions=()) -> dict[str, object]:
    return executor_args_v7.build_source(
        immutable_goal="Read the requested document without modifying it",
        current_requirement="Read one file",
        execution_state=_execution_state(assigned_actions=assigned_actions),
        selected_operation="read_file",
        selected_tool_contract={
            "name": "read_file", "description": "Read a file",
            "parameters": {"type": "object"},
        },
        committed_fact_refs=["A1"],
        executor_history=[{"event_id": "E1", "operation": "read_file"}],
        command={"function": "read_file", "params": {"path": "README.md"}},
        fixture_id="fixture-observation-1",
        execution_verifier_id="execution-verifier-v1",
    )


def test_retired_executor_protocol_modules_are_removed() -> None:
    import importlib.util

    for module in ("executor_args", "executor_args_v3"):
        assert importlib.util.find_spec(f"rwkv_lh.goal_state_protocols.{module}") is None


def test_executor_execution_state_builder_projects_durable_actions() -> None:
    action = SimpleNamespace(
        action_id="A1", action_type="read_file", status=SimpleNamespace(value="failed"),
        arguments={"path": "."}, result={"success": False, "outcome_type": "failure"},
        error={"type": "HarnessError", "message": "read_file requires a regular file"},
        outcome_type="failure",
    )
    state = executor_args_v7.build_execution_state(
        active_step_id="S1", active_step_revision=1, declared_phase="observe",
        effective_phase="observe", assigned_actions=[action],
        mechanical_evidence={"missing_read_roots": ["README.md"]},
        target_contract=_typed_target_contract(),
    )
    assert state["assigned_action_count"] == 1
    assert state["failed_action_count"] == 1
    assert state["last_action"]["result_progress"]["error_message"] == (
        "read_file requires a regular file"
    )
    assert state["feedback"] is None
    action.status = SimpleNamespace(value="running")
    with pytest.raises(ValueError, match="running action"):
        executor_args_v7.build_execution_state(
            active_step_id="S1", active_step_revision=1, declared_phase="observe",
            effective_phase="observe", assigned_actions=[action],
            mechanical_evidence={}, target_contract=_typed_target_contract(),
        )


def _typed_target_contract() -> dict[str, object]:
    return executor_args_v7.build_target_contract(
        phase="observe", roots=["README.md"],
        target_descriptors=[
            {
                "path": "README.md",
                "type": "file",
                "target_kind": "text_file",
                "exists": True,
                "size_bytes": 128,
            }
        ],
        operations=("read_file",),
    )


def _completed_steps() -> list[dict[str, object]]:
    return [{"step_id": "S1", "evidence_refs": ["A1"]}]


def _facts() -> list[dict[str, object]]:
    return [{"fact_id": "F1", "value": "ok", "evidence_refs": ["A1"]}]


def _evidence() -> list[dict[str, object]]:
    return [{"evidence_ref": "A1", "kind": "action", "value": "ok"}]


def test_protocol_schema_identities_are_frozen_without_historical_versions() -> None:
    import importlib
    from pathlib import Path

    modules = {}
    directory = Path(executor_args_v7.__file__).parent
    for path in directory.glob("*.py"):
        if path.name == "__init__.py":
            continue
        module = importlib.import_module(f"rwkv_lh.goal_state_protocols.{path.stem}")
        if hasattr(module, "INPUT_SCHEMA_VERSION"):
            modules[module] = path.stem
    expected = {
        selector_intent_v7: ("selector-intent", "v7"),
        executor_args_v7: ("executor-args", "v7"),
        auditor_step_v7: ("auditor-step", "v7"),
        finalizer_answer: ("finalizer-answer", "v3"),
        auditor_final: ("auditor-final", "v5"),
    }
    assert set(modules) == set(expected)
    for module, (stage, version) in expected.items():
        identity = f"rwkv-lh.g1j-per-stage-state-tuning.{stage}.{version}"
        assert module.INPUT_SCHEMA_VERSION == identity
        assert module.OUTPUT_SCHEMA_VERSION == identity
        assert callable(module.build_prompt_source)
        assert callable(module.render_prompt)
        assert all(marker not in identity for marker in (".v8", ".v999"))


@pytest.mark.parametrize("final_candidate", [False, True])
def test_auditor_wire_definition_does_not_cap_evidence_or_gaps(final_candidate: bool) -> None:
    from rwkv_lh.model import LongHorizonModel
    properties = LongHorizonModel._goal_audit_definition(final_candidate)["parameters"]["properties"]
    assert "maxItems" not in properties["evidence_refs"]
    assert "maxItems" not in properties["gaps"]


def test_selector_intent_v7_exact_suffix_and_failure_aware_progress() -> None:
    source = _selector_source()
    prompt = selector_intent_v7.render_prompt(source)
    target = selector_intent_v7.render_target(source)
    assert target == "\nSelectorIntentV7: read_file"
    assert selector_intent_v7.parse_target(target) == "read_file"
    assert prompt.startswith("SelectorIntentPromptV7: ")
    assert "selected_operation" not in prompt
    assert '"error_type":"JSONDecodeError"' in prompt
    assert '"target_kind":"text_file"' in prompt
    with pytest.raises(ValueError, match="fields/order"):
        selector_intent_v7.validate_source({**source, "unexpected_field": "unexpected"})
    # A succeeded action cannot carry an error and a failed one must.
    bad = json.loads(json.dumps(source))
    bad["current_progress"]["last_action"]["status"] = "succeeded"
    with pytest.raises(ValueError, match="cannot carry an error"):
        selector_intent_v7.validate_source(bad)
    legacy = json.loads(json.dumps(source))
    legacy["current_progress"].pop("workspace_targets")
    with pytest.raises(ValueError, match="fields/order"):
        selector_intent_v7.validate_source(legacy)


def test_selector_intent_v7_build_current_progress_is_the_only_constructor() -> None:
    class _Status:
        def __init__(self, value: str) -> None:
            self.value = value

    class _Action:
        def __init__(self, action_type, status, arguments, result) -> None:
            self.action_type = action_type
            self.status = _Status(status)
            self.arguments = arguments
            self.result = result

    failed = _Action(
        "read_json",
        "failed",
        {"path": "app.py", "start": 0, "nested": {"a": 1}},
        {
            "success": False,
            "error": {"type": "NotJSON", "message": "x" * 500},
            "outcome_type": "failed",
            "metadata": {"target_kind": "text_file", "secret": "drop me"},
        },
    )
    progress = selector_intent_v7.build_current_progress(
        assigned_actions=[failed],
        read_roots=["app.py"],
        write_roots=[],
        mechanical_evidence={
            "missing_read_roots": ["app.py"],
            "missing_write_roots": [],
            "completion_preconditions_satisfied": False,
        },
        target_descriptors=[{"path": "app.py", "target_kind": "text_file", "exists": True}],
        action_observes_root=lambda action, root: False,
        action_mutates_root=lambda action, root: False,
    )
    last = progress["last_action"]
    assert last["arguments"] == {"path": "app.py", "start": "0", "nested": "<object:1 keys>"}
    assert last["error_type"] == "NotJSON"
    assert len(last["error_message"]) == selector_intent_v7.MAX_ERROR_MESSAGE_CHARS
    assert last["result_metadata"] == {"outcome_type": "failed", "target_kind": "text_file"}
    assert progress["workspace_targets"] == [{"path": "app.py", "target_kind": "text_file"}]
    assert progress["failed_action_count"] == 1
    assert tuple(progress) == selector_intent_v7.PROGRESS_FIELDS


def test_executor_args_v7_round_trip_binds_typed_targets_and_failure_fact() -> None:
    action = SimpleNamespace(
        action_id="A1", action_type="read_file", status=SimpleNamespace(value="failed"),
        arguments={"path": "."}, result={"success": False, "outcome_type": "failure"},
        error={"type": "HarnessError", "message": "read_file requires a regular file"},
    )
    source = _executor_source(assigned_actions=[action])
    prompt = executor_args_v7.render_prompt(source)
    target = executor_args_v7.render_target(source)

    assert prompt.startswith(executor_args_v7.PROMPT_PREFIX)
    assert executor_args_v7.parse_target(target).arguments == {"path": "README.md"}
    payload = json.loads(prompt.removeprefix(executor_args_v7.PROMPT_PREFIX))
    assert payload["execution_state"]["target_contract"] == _typed_target_contract()
    assert payload["execution_state"]["last_action"]["result_progress"]["error_message"] == (
        "read_file requires a regular file"
    )
    source["execution_state"]["target_contract"]["argument_targets_by_operation"]["read_file"]["path"]["compatible_paths"] = ["missing.txt"]
    with pytest.raises(ValueError, match="typed descriptor"):
        executor_args_v7.validate_source(source)


def test_executor_args_v7_binds_exact_observation_authority() -> None:
    source = _executor_source()
    prompt = executor_args_v7.render_prompt(source)
    assert prompt.startswith(executor_args_v7.PROMPT_PREFIX)
    payload = json.loads(prompt.removeprefix(executor_args_v7.PROMPT_PREFIX))
    assert payload["observation_binding"]["summary_fact_authority"] is False
    assert payload["observation_binding"]["projection_version"] == (
        "typed-lineage-observation-funnel.v1"
    )
    assert executor_args_v7.parse_target(
        executor_args_v7.render_target(source)
    ).arguments == {"path": "README.md"}

    source["observation_binding"]["fact_action_ids"] = []
    with pytest.raises(ValueError, match="exactly match"):
        executor_args_v7.validate_source(source)


@pytest.mark.parametrize("retired", ["v2", "v3", "v4", "v5", "v6", "v999"])
def test_executor_generation_boundary_rejects_retired_protocols(retired: str) -> None:
    from rwkv_lh.model_io import ModelIOError, validate_independent_executor_generation_input

    source = _executor_source()
    current = executor_args_v7.render_generation_prompt(source)
    validate_independent_executor_generation_input(current, source["current_requirement"])
    old_input = current.replace(
        executor_args_v7.PROMPT_PREFIX, f"ExecutorArgsPrompt{retired.upper()}: "
    ).replace(executor_args_v7.INPUT_SCHEMA_VERSION,
              executor_args_v7.INPUT_SCHEMA_VERSION.rsplit(".", 1)[0] + "." + retired)
    with pytest.raises(ModelIOError, match="retired|current Executor-Args input protocol"):
        validate_independent_executor_generation_input(old_input, source["current_requirement"])


def test_executor_generation_boundary_validates_the_complete_shared_contract() -> None:
    from rwkv_lh.model_io import ModelIOError, validate_independent_executor_generation_input

    source = _executor_source()
    current = executor_args_v7.render_generation_prompt(source)
    invalid = current.replace('"summary_fact_authority":false', '"summary_fact_authority":true')
    with pytest.raises(ModelIOError, match="factual authority"):
        validate_independent_executor_generation_input(invalid, source["current_requirement"])


def test_executor_current_input_can_quote_a_historical_marker_as_data() -> None:
    from rwkv_lh.model_io import validate_independent_executor_generation_input

    source = _executor_source()
    source["current_requirement"] = "Explain the text ExecutorArgsPromptV3: as file data."
    prompt = executor_args_v7.render_generation_prompt(source)
    validate_independent_executor_generation_input(prompt, source["current_requirement"])


@pytest.mark.parametrize("quoted_content", ["marker", "fake_object", "complete_frame"])
def test_executor_current_frame_can_quote_its_own_prefix_as_data(quoted_content: str) -> None:
    from rwkv_lh.model_io import validate_independent_executor_generation_input

    source = _executor_source()
    quoted = executor_args_v7.PROMPT_PREFIX
    if quoted_content == "fake_object":
        quoted += json.dumps({"schema_version": "example", "role": "executor_args"})
    elif quoted_content == "complete_frame":
        quoted = executor_args_v7.render_generation_prompt(source)
    source["current_requirement"] = "Explain this literal text:\n\n" + quoted
    source["executor_history"].append({"observation": quoted})
    prompt = executor_args_v7.render_generation_prompt(source)

    validate_independent_executor_generation_input(prompt, source["current_requirement"])


def test_executor_framing_selects_the_final_complete_retry_input() -> None:
    from rwkv_lh.model_io import validate_independent_executor_generation_input

    source = _executor_source()
    prior = executor_args_v7.render_generation_prompt(source)
    prior += executor_args_v7.render_target(source)
    source["current_requirement"] = "Read again and explain " + executor_args_v7.PROMPT_PREFIX
    current = executor_args_v7.render_generation_prompt(source)
    validate_independent_executor_generation_input(
        prior + "\n\n" + current, source["current_requirement"],
    )


@pytest.mark.parametrize("version", ["v3", "v999"])
def test_executor_framing_rejects_an_actual_noncurrent_trailing_frame(version: str) -> None:
    from rwkv_lh.model_io import ModelIOError, validate_independent_executor_generation_input

    source = _executor_source()
    current = executor_args_v7.render_generation_prompt(source)
    trailing = current.replace(
        executor_args_v7.PROMPT_PREFIX, f"ExecutorArgsPrompt{version.upper()}: ",
    ).replace(
        executor_args_v7.INPUT_SCHEMA_VERSION,
        executor_args_v7.INPUT_SCHEMA_VERSION.rsplit(".", 1)[0] + "." + version,
    )
    with pytest.raises(ModelIOError):
        validate_independent_executor_generation_input(
            current + "\n\n" + trailing, source["current_requirement"],
        )


def test_step_auditor_round_trip_and_catalog_binding() -> None:
    step = _step()
    evidence = _evidence()
    catalog = auditor_step_v7.build_gap_catalog(step, evidence)
    source = auditor_step_v7.build_prompt_source(
        immutable_goal="Read the requested document without modifying it",
        boundary="observation_complete", active_step=step,
        available_evidence_refs=["A1"], evidence_records=evidence,
    )
    source.update(
        decision={
            "verdict": "continue", "step_id": "S1", "step_complete": True,
            "evidence_refs": ["A1"], "gaps": [], "reason": "The requested file contents are present in A1.",
        },
        completion_verifier_id="completion-verifier-v1",
    )
    prompt = auditor_step_v7.render_prompt(source)
    target = auditor_step_v7.render_target(source)

    assert prompt.startswith("AuditorStepPromptV7: ")
    assert auditor_step_v7.parse_target(target).arguments["verdict"] == "continue"
    payload = json.loads(prompt.removeprefix("AuditorStepPromptV7: "))
    assert payload["gap_catalog"] == catalog

    repair = {
        **source,
        "decision": {
            "verdict": "repair",
            "step_id": "S1",
            "step_complete": False,
            "evidence_refs": ["A1"],
            "gaps": [catalog[0]["code"]],
            "reason": "The current step still lacks the required evidence.",
        },
    }
    auditor_step_v7.validate_source(repair)
    with pytest.raises(ValueError, match="gap_catalog"):
        auditor_step_v7.validate_source(
            {
                **repair,
                "decision": {**repair["decision"], "gaps": ["invented-gap"]},
            }
        )
    with pytest.raises(ValueError, match="non-empty"):
        auditor_step_v7.parse_target(
            ModelCommand(
                "audit_decision",
                {**repair["decision"], "reason": ""},
            ).canonical
        )


def test_finalizer_round_trip_has_no_completion_authority() -> None:
    source = finalizer_answer.build_prompt_source(
        immutable_goal="Report the observed value", completed_steps=_completed_steps(),
        committed_facts=_facts(), evidence_records=_evidence(),
        format_contract={"format_id": "plain-v1", "language": "en", "required_sections": []},
    )
    source.update(final_text="The observed value is ok.", fact_verifier_id="fact-verifier-v1")
    prompt = finalizer_answer.render_prompt(source)
    target = finalizer_answer.render_target(source)
    assert finalizer_answer.parse_target(target).arguments == {
        "text": "The observed value is ok."
    }
    assert "fact_verifier_id" not in prompt
    assert "COMPLETED" not in prompt


def test_final_auditor_round_trip_and_repair_semantics() -> None:
    source = auditor_final.build_prompt_source(
        immutable_goal="Report the observed value", completed_steps=_completed_steps(),
        available_evidence_refs=["A1"], evidence_records=_evidence(),
        final_candidate={
            "function": "final_answer", "params": {"text": "The observed value is ok."},
        },
    )
    source.update(
        decision={
            "verdict": "ready_for_final", "step_id": "", "step_complete": False,
            "evidence_refs": ["A1"], "gaps": [], "reason": "The answer agrees with the observed value in A1.",
        },
        final_verifier_id="final-verifier-v1",
    )
    prompt = auditor_final.render_prompt(source)
    target = auditor_final.render_target(source)
    assert auditor_final.parse_target(target).arguments["verdict"] == "ready_for_final"
    assert "final_verifier_id" not in prompt
    prompt_payload = json.loads(prompt.removeprefix(auditor_final.PROMPT_PREFIX))
    question = prompt_payload["current_question"]
    assert "exactly these six fields" in question
    assert "evidence_refs and gaps arrays" in question
    assert "ready_for_final only" in question
    assert "step_id is always the empty string" in question
    invalid = dict(source)
    invalid["decision"] = {
        **source["decision"],
        "verdict": "repair",
        "gaps": [],
    }
    with pytest.raises(ValueError, match="non-empty gaps"):
        auditor_final.validate_source(invalid)


def test_source_field_order_is_part_of_every_protocol() -> None:
    source = dict(reversed(tuple(_selector_source().items())))
    with pytest.raises(ValueError, match="fields/order"):
        selector_intent_v7.validate_source(source)
