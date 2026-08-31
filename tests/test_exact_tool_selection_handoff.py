from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from rwkv_lh.exact_tool_selector.protocol import (
    EXACT_TOOL_LABELS,
    ExactToolSelection,
)
from rwkv_lh.schema import (
    CausalEventDraft,
    GoalState,
    ModelCheckpoint,
    ModelLaneKind,
    RunState,
    ToolSelectionRecord,
    ToolSelectionStatus,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _checkpoints() -> tuple[ModelCheckpoint, ModelCheckpoint]:
    selector = ModelCheckpoint(
        checkpoint_id="SCP-0001",
        lane_id="LANE:SELECTOR",
        lane_kind=ModelLaneKind.SELECTOR,
        parent_checkpoint_id=None,
        model="rwkv7-g1i-2.9b-20260805-ctx16384",
        transport="native_rwkv",
        transcript="selector bootstrap\nselector step",
        transcript_digest=_digest("selector bootstrap\nselector step"),
        token_count=7,
        native_state_ref="STATE-0001",
        native_state_digest="3" * 64,
        native_state_metadata={
            "model_sha256": "4" * 64,
            "head_sha256": "5" * 64,
            "token_position": 128,
        },
        state_profile_id="selector-base-v1",
        state_profile_sha256="6" * 64,
    )
    executor = ModelCheckpoint(
        checkpoint_id="ECP-0001",
        lane_id="LANE:ACTION",
        lane_kind=ModelLaneKind.ACTION,
        parent_checkpoint_id=None,
        model="rwkv7-g1i-13.3b-20260805-ctx16384",
        transport="prompt_replay",
        transcript="executor prompt",
        transcript_digest=_digest("executor prompt"),
        token_count=3,
        native_state_metadata={"model_sha256": "8" * 64},
        state_profile_id="executor-base-v1",
        state_profile_sha256="9" * 64,
    )
    return selector, executor


def _selection_record(
    selector: ModelCheckpoint,
    executor: ModelCheckpoint,
    *,
    selection_id: str = "SEL-0001",
) -> ToolSelectionRecord:
    logits = [float(index) / 100.0 for index in range(len(EXACT_TOOL_LABELS))]
    logits[EXACT_TOOL_LABELS.index("read_file")] = 3.0
    raw = ExactToolSelection(
        selection_id=selection_id,
        trace_id="TRACE-0001",
        selected_operation="read_file",
        logits=tuple(logits),
        temperature=0.8,
        input_digest="1" * 64,
        menu_digest="2" * 64,
        selector_checkpoint_id=selector.checkpoint_id,
        selector_state_ref=str(selector.native_state_ref),
        selector_state_digest=str(selector.native_state_digest),
        selector_parent_state_digest="",
        token_position=128,
        model=selector.model,
        model_sha256="4" * 64,
        head_sha256="5" * 64,
        profile_id=selector.state_profile_id,
        profile_sha256=selector.state_profile_sha256,
    )
    return ToolSelectionRecord(
        selection_id=selection_id,
        status=ToolSelectionStatus.COMMITTED,
        selected_operation=raw.selected_operation,
        selector_checkpoint_id=selector.checkpoint_id,
        selector_state_ref=str(selector.native_state_ref),
        selector_state_digest=str(selector.native_state_digest),
        selector_parent_state_digest="",
        executor_parent_checkpoint_id=executor.checkpoint_id,
        executor_parent_digest=executor.transcript_digest,
        input_projection_digest=raw.input_digest,
        menu_digest=raw.menu_digest,
        tool_definition_digest="7" * 64,
        selector_model=selector.model,
        selector_model_sha256="4" * 64,
        selector_head_sha256="5" * 64,
        selector_profile_id=selector.state_profile_id,
        selector_profile_sha256=selector.state_profile_sha256,
        executor_model=executor.model,
        executor_model_sha256="8" * 64,
        executor_profile_id=executor.state_profile_id,
        executor_profile_sha256=executor.state_profile_sha256,
        raw_selection=raw.raw_record(),
    )


def _new_run(tmp_path: Path) -> tuple[LongHorizonStore, RunState]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=20)
    state = store.create_run(
        GoalState.create(
            request="Read note.txt and report its exact contents.",
            constraints=[],
            workspace_root=workspace,
        ),
        run_id="HANDOFF-TEST",
    )
    selector, executor = _checkpoints()
    state.model_states[selector.checkpoint_id] = selector
    state.model_states[executor.checkpoint_id] = executor
    state.set_lane_head("selector", selector.checkpoint_id)
    state.set_lane_head("executor", executor.checkpoint_id)
    return store, state


def test_selection_is_durable_before_executor_and_consumed_once(
    tmp_path: Path,
) -> None:
    store, state = _new_run(tmp_path)
    selector = state.model_states[state.lane_head("selector")]
    executor = state.model_states[state.lane_head("executor")]
    selection = _selection_record(selector, executor)

    state = store.save(
        state,
        causal_event=CausalEventDraft.create(
            "exact_tool_selection_committed",
            {"selection_id": selection.selection_id, "selection": selection.to_dict()},
            subject_id=selection.selection_id,
        ),
    )

    recovered = store.load(state.run_id)
    assert recovered.pending_selection_id == selection.selection_id
    assert recovered.tool_selections[selection.selection_id] == selection
    consumed = replace(
        selection,
        status=ToolSelectionStatus.CONSUMED,
        consumed_decision_id="D-EXECUTOR-0001",
        consumed_at=utc_now(),
    )
    recovered = store.save(
        recovered,
        causal_event=CausalEventDraft.create(
            "exact_tool_selection_consumed",
            {"selection_id": consumed.selection_id, "selection": consumed.to_dict()},
            subject_id=consumed.selection_id,
        ),
    )

    assert recovered.pending_selection_id == ""
    assert recovered.tool_selections[selection.selection_id] == consumed


def test_unconsumed_selection_cannot_be_silently_replaced(tmp_path: Path) -> None:
    store, state = _new_run(tmp_path)
    selector = state.model_states[state.lane_head("selector")]
    executor = state.model_states[state.lane_head("executor")]
    first = _selection_record(selector, executor)
    state = store.save(
        state,
        causal_event=CausalEventDraft.create(
            "exact_tool_selection_committed",
            {"selection_id": first.selection_id, "selection": first.to_dict()},
            subject_id=first.selection_id,
        ),
    )
    second = _selection_record(selector, executor, selection_id="SEL-0002")

    with pytest.raises(ValueError, match="cannot replace an unconsumed selection"):
        store.save(
            state,
            causal_event=CausalEventDraft.create(
                "exact_tool_selection_committed",
                {"selection_id": second.selection_id, "selection": second.to_dict()},
                subject_id=second.selection_id,
            ),
        )
