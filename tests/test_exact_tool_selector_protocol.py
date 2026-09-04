from __future__ import annotations

import json

import pytest

from rwkv_lh.exact_tool_selector.protocol import (
    ABSTAIN_LABEL,
    EXACT_TOOL_LABELS,
    SELECTOR_OUTPUT_SCHEMA_VERSION,
    ExactToolSelection,
    SelectorInput,
    SelectorProgress,
    selector_tool_menu,
)


def test_selector_menu_is_exactly_20_schema_free_classes() -> None:
    menu = selector_tool_menu()

    assert len(menu) == 20
    assert tuple(item["name"] for item in menu) == EXACT_TOOL_LABELS
    assert menu[-1]["name"] == ABSTAIN_LABEL
    assert all(set(item) == {"name", "description"} for item in menu)
    serialized = json.dumps(menu, ensure_ascii=False)
    assert '"parameters"' not in serialized
    assert '"required"' not in serialized


def test_selector_input_excludes_executor_only_fields() -> None:
    selector_input = SelectorInput.create(
        task_request="Update config.json and verify it.",
        stage_objective="Observe the current JSON object.",
        stage_role="work",
        progress=SelectorProgress(
            completed_stage_count=1,
            action_index=2,
            succeeded_operations=("list_directory",),
            failed_operations=("read_file",),
            protocol_rejection_count=1,
        ),
    )

    payload = selector_input.to_dict()
    rendered = selector_input.render()
    assert payload["menu_digest"] == selector_input.menu_digest
    assert "Task state" not in selector_input.render_step()
    assert '"task_request"' not in selector_input.render_step()
    assert '"progress"' not in selector_input.render_bootstrap()
    assert rendered == (
        selector_input.render_bootstrap() + "\n" + selector_input.render_step()
    )
    assert '"parameters"' not in rendered
    assert '"arguments"' not in rendered
    assert '"result"' not in rendered
    assert '"reasoning"' not in rendered


def test_selector_input_rejects_menu_schema_leak() -> None:
    menu = list(selector_tool_menu())
    menu[0] = {**menu[0], "parameters": "not allowed"}

    with pytest.raises(ValueError, match="only name and description"):
        SelectorInput(
            task_request="Inspect files.",
            stage_objective="List the workspace.",
            stage_role="work",
            progress=SelectorProgress(),
            menu=tuple(menu),
        )


def test_selector_progress_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="unknown operations"):
        SelectorProgress(succeeded_operations=("shell_exec",))


def test_selector_progress_rejects_duplicate_operation_kinds() -> None:
    with pytest.raises(ValueError, match="succeeded operations must be unique"):
        SelectorProgress(succeeded_operations=("read_file", "read_file"))

    with pytest.raises(ValueError, match="failed operations must be unique"):
        SelectorProgress(failed_operations=("read_file", "read_file"))


def _selection(*, selected_operation: str = "read_file") -> ExactToolSelection:
    logits = [float(index) / 100.0 for index in range(len(EXACT_TOOL_LABELS))]
    logits[EXACT_TOOL_LABELS.index("read_file")] = 3.0
    return ExactToolSelection(
        selection_id="SEL-0001",
        trace_id="TRACE-0001",
        selected_operation=selected_operation,
        logits=tuple(logits),
        temperature=0.8,
        input_digest="1" * 64,
        menu_digest="2" * 64,
        selector_checkpoint_id="SCP-0001",
        selector_state_ref="STATE-0001",
        selector_state_digest="3" * 64,
        selector_parent_state_digest="",
        token_position=128,
        model="rwkv7-g1i-2.9b-20260805-ctx16384",
        model_sha256="4" * 64,
        head_sha256="5" * 64,
        profile_id="selector-base-v1",
        profile_sha256="6" * 64,
    )


def test_exact_tool_selection_retains_complete_raw_logits() -> None:
    selection = _selection()
    record = selection.raw_record()

    assert record["schema_version"] == SELECTOR_OUTPUT_SCHEMA_VERSION
    assert record["class_order"] == list(EXACT_TOOL_LABELS)
    assert record["logits"] == list(selection.logits)
    assert record["logits_sha256"] == selection.logits_sha256
    assert record["selected_operation"] == "read_file"
    assert record["postprocessed"] is False
    assert record["generated_text"] is False
    assert 0.0 < record["confidence"] < 1.0


def test_exact_tool_selection_rejects_label_different_from_raw_argmax() -> None:
    with pytest.raises(ValueError, match="raw-logit argmax"):
        _selection(selected_operation="write_file")


def test_exact_tool_selection_round_trip() -> None:
    selection = _selection()

    assert ExactToolSelection.from_dict(selection.raw_record()) == selection
