from __future__ import annotations

import json

import pytest

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_ABSTAIN_LABEL,
    NETWORK_EXACT_TOOL_LABELS,
    NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2,
    NetworkExactToolSelection,
    NetworkSelectorInput,
    NetworkSelectorProgress,
    network_selector_tool_menu,
)


def test_network_selector_v2_has_25_schema_free_classes() -> None:
    menu = network_selector_tool_menu()

    assert len(menu) == 25
    assert tuple(item["name"] for item in menu) == NETWORK_EXACT_TOOL_LABELS
    assert menu[-1]["name"] == NETWORK_ABSTAIN_LABEL
    assert {"web_search", "connector_lookup", "calculator", "date_diff", "current_time"} <= {
        item["name"] for item in menu
    }
    rendered = json.dumps(menu, ensure_ascii=False)
    assert '"parameters"' not in rendered
    assert '"required"' not in rendered


def test_network_selector_v2_excludes_executor_state_and_results() -> None:
    value = NetworkSelectorInput.create(
        task_request="Find the latest release for owner/repository.",
        stage_objective="Read the exact structured repository release record.",
        stage_role="observe",
        progress=NetworkSelectorProgress(
            action_index=1,
            succeeded_operations=("web_search",),
        ),
    )

    assert '"task_request"' not in value.render_step()
    assert '"progress"' not in value.render_bootstrap()
    assert '"arguments"' not in value.render()
    assert '"result"' not in value.render()
    assert '"reasoning"' not in value.render()
    assert '"parameters"' not in value.render()


def test_network_selector_v2_rejects_schema_leak() -> None:
    menu = list(network_selector_tool_menu())
    menu[0] = {**menu[0], "parameters": {"path": "string"}}

    with pytest.raises(ValueError, match="only name and description"):
        NetworkSelectorInput(
            task_request="Inspect the project.",
            stage_objective="List the project root.",
            stage_role="observe",
            progress=NetworkSelectorProgress(),
            menu=tuple(menu),
        )


def test_network_selector_v2_preserves_all_raw_logits() -> None:
    logits = [float(index) / 100 for index in range(25)]
    selected = NETWORK_EXACT_TOOL_LABELS.index("connector_lookup")
    logits[selected] = 4.0
    value = NetworkExactToolSelection(
        selection_id="SEL-V2-1",
        trace_id="TRACE-1",
        selected_operation="connector_lookup",
        logits=tuple(logits),
        temperature=0.75,
        input_digest="1" * 64,
        menu_digest="2" * 64,
        selector_checkpoint_id="SCP-1",
        selector_state_ref="STATE-1",
        selector_state_digest="3" * 64,
        selector_parent_state_digest="",
        token_position=99,
        model="rwkv7-g1i-2.9b-20260805-ctx16384",
        model_sha256="4" * 64,
        head_sha256="5" * 64,
        profile_id="selector-base-v2",
        profile_sha256="6" * 64,
    )

    raw = value.raw_record()
    assert raw["class_order"] == list(NETWORK_EXACT_TOOL_LABELS)
    assert raw["logits"] == logits
    assert raw["selected_operation"] == "connector_lookup"
    assert raw["postprocessed"] is False
    assert raw["generated_text"] is False
    assert NetworkExactToolSelection.from_dict(raw) == value


def test_network_selector_v3_selects_raw_argmax_only_inside_eligibility_domain() -> None:
    logits = [float(index) / 100 for index in range(25)]
    logits[NETWORK_EXACT_TOOL_LABELS.index("run_command")] = 10.0
    logits[NETWORK_EXACT_TOOL_LABELS.index("write_file")] = 9.0
    eligible = ("write_file", "final_answer", "ABSTAIN")
    value = NetworkExactToolSelection(
        selection_id="SEL-V3-MASK",
        trace_id="TRACE-V3-MASK",
        selected_operation="write_file",
        logits=tuple(logits),
        temperature=0.75,
        input_digest="1" * 64,
        menu_digest="2" * 64,
        selector_checkpoint_id="SCP-V3",
        selector_state_ref="STATE-V3",
        selector_state_digest="3" * 64,
        selector_parent_state_digest="",
        token_position=99,
        model="rwkv7-g1i-2.9b-20260805-ctx16384",
        model_sha256="4" * 64,
        head_sha256="5" * 64,
        profile_id="selector-base-v3",
        profile_sha256="6" * 64,
        eligible_labels=eligible,
    )

    raw = value.raw_record()
    assert raw["logits"][NETWORK_EXACT_TOOL_LABELS.index("run_command")] == 10.0
    assert raw["eligible_labels"] == list(eligible)
    assert raw["selected_operation"] == "write_file"
    assert raw["selection_rule"] == "eligible_raw_logit_argmax"
    assert raw["postprocessed"] is False
    assert NetworkExactToolSelection.from_dict(raw) == value


def test_network_selector_v2_record_remains_backward_readable() -> None:
    logits = [float(index) / 100 for index in range(25)]
    logits[NETWORK_EXACT_TOOL_LABELS.index("read_file")] = 10.0
    raw = {
        "schema_version": NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2,
        "selection_id": "SEL-OLD-V2",
        "trace_id": "TRACE-OLD-V2",
        "selected_operation": "read_file",
        "logits": logits,
        "temperature": 1.0,
        "input_digest": "1" * 64,
        "menu_digest": "2" * 64,
        "selector_checkpoint_id": "SCP-OLD",
        "selector_state_ref": "STATE-OLD",
        "selector_state_digest": "3" * 64,
        "selector_parent_state_digest": "",
        "token_position": 10,
        "model": "rwkv7-g1i-2.9b-old",
        "model_sha256": "4" * 64,
        "head_sha256": "5" * 64,
        "profile_id": "selector-old-v2",
        "profile_sha256": "6" * 64,
    }

    restored = NetworkExactToolSelection.from_dict(raw)

    assert restored.schema_version == NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2
    assert restored.eligible_labels == NETWORK_EXACT_TOOL_LABELS
    assert restored.selected_operation == "read_file"
