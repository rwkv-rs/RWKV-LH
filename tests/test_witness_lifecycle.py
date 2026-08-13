import json
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import (
    CrossValidationDecision,
    LongHorizonModel,
    ModelInvoker,
    ModelProtocolError,
)
from rwkv_lh.proof import CriterionProofEngine
from rwkv_lh.schema import (
    ArtifactRecord,
    Attempt,
    AttemptStatus,
    GoalCriterion,
    GoalState,
    MemoryEntry,
    OBLIGATION_RUN_SCHEMA_VERSION,
    RunState,
    RunStatus,
    TaskAction,
    TaskNode,
    TaskStatus,
    ValidationSpec,
    WitnessIntentState,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.witness import (
    WitnessCatalogBuilder,
    WitnessCatalogError,
    expand_witness_bindings,
    witness_prompt_view,
    witness_source_prompt_view,
)


def witness_state(root: Path):
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    (workspace / "result.txt").write_text("good", encoding="utf-8")
    (workspace / "dependency.json").write_text(
        '{"expected":"good","items":[1,2]}', encoding="utf-8"
    )
    goal = GoalState.create(
        objective="Write good",
        original_request="Write exactly good to result.txt.",
        constraints=["Stay in workspace"],
        success_criteria=[GoalCriterion("GC1", "result.txt is exactly good")],
        workspace_root=workspace,
    )
    dependency = TaskNode(
        "T1",
        "Produce dependency",
        "Produce immutable dependency evidence",
        status=TaskStatus.COMPLETED,
        output_refs=["A1", "M-T1"],
    )
    task = TaskNode(
        "T2",
        "Observe result",
        "Observe and prove the requested result",
        dependencies=["T1"],
        satisfies_criteria=["GC1"],
        action=TaskAction("read_file", {"path": "result.txt"}),
        attempt_ids=["T2-A1"],
    )
    attempt = Attempt(
        "T2-A1",
        "T2",
        AttemptStatus.SUCCEEDED,
        action_fingerprint(task.action),
        "key",
        utc_now(),
        ended_at=utc_now(),
        tool_result={
            "action_type": "read_file",
            "success": True,
            "output": "good",
            "metadata": {},
            "artifacts": [],
            "evidence": [],
            "error": None,
        },
    )
    intent = WitnessIntentState(
        intent_id="WI-T2-GC1",
        task_id="T2",
        criterion_id="GC1",
        subject_task_id="T2",
        producer_task_id="T2",
        comparison="exact_equals",
        actual_source_kind="workspace",
        expected_source_kind="goal_literal",
        expected_goal_literal={"goal_quote": "good", "value": "good"},
    )
    state = RunState("WITNESS", goal)
    state.tasks = {"T1": dependency, "T2": task}
    state.attempts = {attempt.attempt_id: attempt}
    state.artifacts["A1"] = ArtifactRecord(
        "A1", "T1", "dependency.json", ""
    )
    state.artifacts["A1"].sha256 = __import__("hashlib").sha256(
        (workspace / "dependency.json").read_bytes()
    ).hexdigest()
    state.memory_index["M-T1"] = MemoryEntry(
        "M-T1",
        "action_result",
        "T1",
        "dependency JSON",
        '{"expected":"good","items":[1,2]}',
        ["A1"],
    )
    state.witness_intents[intent.intent_id] = intent
    return state, task, attempt, intent


def select_handle(catalog, *, source_kind, read_op, transforms, path=None):
    for handle in catalog["handles"]:
        operator = handle["operator_value"]
        if (
            handle["source_kind"] == source_kind
            and operator["read_op"] == read_op
            and operator["transforms"] == transforms
            and (path is None or operator["arguments"].get("path") == path)
        ):
            return handle
    raise AssertionError(f"missing handle: {source_kind}/{read_op}/{transforms}")


def test_witness_catalog_is_deterministic_complete_and_proof_native(tmp_path):
    state, task, attempt, intent = witness_state(tmp_path)
    engine = CriterionProofEngine(ActionHarness())
    builder = WitnessCatalogBuilder(engine)

    first = builder.build(state, task, attempt, [intent])
    second = builder.build(state, task, attempt, [intent])

    assert first == second
    assert first["complete"] is True
    assert first["catalog_digest"] == second["catalog_digest"]
    assert first["handle_count"] == len(first["handles"])
    encoded = json.dumps(first, ensure_ascii=False)
    assert "result.txt is exactly good" not in encoded
    assert "acceptance" not in encoded
    assert "reference_answer" not in encoded
    for handle in first["handles"]:
        operator = handle["operator_value"]
        pointer = operator["arguments"].get("pointer")
        assert pointer is None or pointer == "" or pointer.startswith("/")
        side = "expected" if handle["eligible_sides"] == ["expected"] else "actual"
        value, refs, _, _ = engine.resolve_operator_value(
            state,
            task,
            attempt,
            operator,
            side=side,
            claim_id="RECHECK",
        )
        assert refs
        assert handle["value_sha256"]
        assert type(value).__name__ == handle["value_type"]

    source_view = witness_source_prompt_view(first, [intent])[0]
    visible_actual_sources = {
        item["source_handle_id"] for item in source_view["actual_sources"]
    }
    expected_actual_sources = {
        item["source_handle_id"]
        for item in first["sources"]
        if item["source_kind"] == intent.actual_source_kind
        and item["owner_task_id"] == intent.producer_task_id
        and "actual" in item["eligible_sides"]
    }
    assert visible_actual_sources == expected_actual_sources

    actual = select_handle(
        first,
        source_kind="workspace",
        read_op="workspace_text",
        transforms=[],
        path="result.txt",
    )
    expected = select_handle(
        first,
        source_kind="goal_literal",
        read_op="goal_literal",
        transforms=[],
    )
    source_selections = [
        {
            "intent_id": intent.intent_id,
            "criterion_id": intent.criterion_id,
            "actual_source_handle_id": actual["source_handle_id"],
            "expected_source_handle_id": expected["source_handle_id"],
        }
    ]
    selected_view = witness_prompt_view(
        first, [intent], source_selections
    )[0]
    visible_selected_ids = {
        variant["handle_id"]
        for side in ("actual_source_groups", "expected_source_groups")
        for group in selected_view[side]
        for variant in group["variants"]
    }
    expected_selected_ids = {
        item["handle_id"]
        for item in first["handles"]
        if item["source_handle_id"]
        in {actual["source_handle_id"], expected["source_handle_id"]}
        and (
            "actual" in item["eligible_sides"]
            or "expected" in item["eligible_sides"]
        )
    }
    assert visible_selected_ids == expected_selected_ids
    bindings = [
        {
            "intent_id": intent.intent_id,
            "criterion_id": intent.criterion_id,
            "actual_handle_id": actual["handle_id"],
            "expected_handle_id": expected["handle_id"],
        }
    ]
    assertions = expand_witness_bindings(
        [intent], bindings, first, source_selections
    )
    claim = engine.evaluate_operator_assertion(
        state,
        task,
        attempt,
        assertions[0],
        claim_id="CC-WITNESS",
        rwkv_reason="selected by RWKV fixture",
    )
    assert claim.passed is True


def test_witness_binding_expander_never_tries_an_alternative(tmp_path):
    state, task, attempt, intent = witness_state(tmp_path)
    catalog = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, [intent]
    )
    actual = select_handle(
        catalog,
        source_kind="workspace",
        read_op="workspace_text",
        transforms=[],
        path="result.txt",
    )
    with pytest.raises(WitnessCatalogError, match="unknown handle"):
        expand_witness_bindings(
            [intent],
            [
                {
                    "intent_id": intent.intent_id,
                    "criterion_id": intent.criterion_id,
                    "actual_handle_id": actual["handle_id"],
                    "expected_handle_id": "WH-NOT-REAL",
                }
            ],
            catalog,
        )
    expected = select_handle(
        catalog,
        source_kind="goal_literal",
        read_op="goal_literal",
        transforms=[],
    )
    wrong_actual = select_handle(
        catalog,
        source_kind="workspace",
        read_op="workspace_text",
        transforms=[],
        path="dependency.json",
    )
    source_selections = [
        {
            "intent_id": intent.intent_id,
            "criterion_id": intent.criterion_id,
            "actual_source_handle_id": actual["source_handle_id"],
            "expected_source_handle_id": expected["source_handle_id"],
        }
    ]
    with pytest.raises(WitnessCatalogError, match="selected raw source"):
        expand_witness_bindings(
            [intent],
            [
                {
                    "intent_id": intent.intent_id,
                    "criterion_id": intent.criterion_id,
                    "actual_handle_id": wrong_actual["handle_id"],
                    "expected_handle_id": expected["handle_id"],
                }
            ],
            catalog,
            source_selections,
        )


def test_rwkv_witness_validation_selects_only_explicit_handle_ids(tmp_path):
    state, task, attempt, intent = witness_state(tmp_path)
    catalog = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, [intent]
    )
    actual = select_handle(
        catalog,
        source_kind="workspace",
        read_op="workspace_text",
        transforms=[],
        path="result.txt",
    )
    expected = select_handle(
        catalog,
        source_kind="goal_literal",
        read_op="goal_literal",
        transforms=[],
    )
    source_payload = {
        "schema_version": "long-horizon.witness-source-validation.v1",
        "decision": "pass",
        "reason": "the selected witnesses are exact and independent",
        "source_selections": [
            {
                "intent_id": intent.intent_id,
                "criterion_id": intent.criterion_id,
                "actual_source_handle_id": actual["source_handle_id"],
                "expected_source_handle_id": expected["source_handle_id"],
            }
        ],
    }
    binding_payload = {
        "schema_version": "long-horizon.witness-handle-binding.v1",
        "witness_bindings": [
            {
                "intent_id": intent.intent_id,
                "criterion_id": intent.criterion_id,
                "actual_handle_id": actual["handle_id"],
                "expected_handle_id": expected["handle_id"],
            }
        ],
    }

    class Client:
        def __init__(self):
            self.prompts = []
            self.outputs = [source_payload, binding_payload]

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.prompts.append(prompt)
            return type(
                "Response", (), {"content": json.dumps(self.outputs.pop(0))}
            )()

    client = Client()
    decision = LongHorizonModel(ModelInvoker(client=client)).cross_validate(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result=attempt.tool_result,
        validation_results=[],
        witness_intents=[intent],
        witness_catalog=catalog,
        binding_feedback=[],
    )

    assert decision.passed is True
    assert decision.witness_bindings == binding_payload["witness_bindings"]
    assert decision.witness_source_selections == source_payload[
        "source_selections"
    ]
    assert decision.criterion_assertions[0]["actual"] == actual["operator_value"]
    assert decision.criterion_assertions[0]["expected"] == expected["operator_value"]
    assert len(client.prompts) == 2
    assert actual["source_handle_id"] in client.prompts[0]
    assert expected["source_handle_id"] in client.prompts[0]
    assert actual["handle_id"] in client.prompts[1]
    assert expected["handle_id"] in client.prompts[1]


def test_unknown_rwkv_handle_is_rejected_without_candidate_selection(tmp_path):
    state, task, attempt, intent = witness_state(tmp_path)
    catalog = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, [intent]
    )
    actual_source_id = next(
        item["source_handle_id"]
        for item in catalog["sources"]
        if item["source_kind"] == "workspace"
        and item["locator"].get("path") == "result.txt"
    )
    expected_source_id = next(
        item["source_handle_id"]
        for item in catalog["sources"]
        if item["source_kind"] == "goal_literal"
    )
    source_payload = {
        "schema_version": "long-horizon.witness-source-validation.v1",
        "decision": "pass",
        "reason": "invented handles",
        "source_selections": [
            {
                "intent_id": intent.intent_id,
                "criterion_id": intent.criterion_id,
                "actual_source_handle_id": actual_source_id,
                "expected_source_handle_id": expected_source_id,
            }
        ],
    }
    binding_payload = {
        "schema_version": "long-horizon.witness-handle-binding.v1",
        "witness_bindings": [
            {
                "intent_id": intent.intent_id,
                "criterion_id": intent.criterion_id,
                "actual_handle_id": "WH-INVENTED-ACTUAL",
                "expected_handle_id": "WH-INVENTED-EXPECTED",
            }
        ],
    }

    class Client:
        def __init__(self):
            self.outputs = [source_payload, binding_payload, binding_payload]

        def text_completion(self, prompt, max_tokens=768, stop=None):
            return type(
                "Response", (), {"content": json.dumps(self.outputs.pop(0))}
            )()

    model = LongHorizonModel(ModelInvoker(client=Client()))
    with pytest.raises(ModelProtocolError, match="unknown handle"):
        model.cross_validate(
            state,
            task,
            WorkingMemoryBuilder().build_task_validation(state, task),
            lambda *_args: None,
            action_result=attempt.tool_result,
            validation_results=[],
            witness_intents=[intent],
            witness_catalog=catalog,
            binding_feedback=[],
        )


def test_witness_state_and_attempt_catalog_digest_round_trip(tmp_path):
    state, _, attempt, intent = witness_state(tmp_path)
    attempt.witness_catalog_digest = "catalog-digest"
    intent.catalog_digest = "catalog-digest"
    intent.current_binding = {"actual_handle_id": "WH-0001"}
    intent.binding_history = [{"round": 1, "proof_passed": False}]

    restored = RunState.from_dict(state.to_dict())

    assert restored.attempts[attempt.attempt_id].witness_catalog_digest == (
        "catalog-digest"
    )
    restored_intent = restored.witness_intents[intent.intent_id]
    assert restored_intent.catalog_digest == "catalog-digest"
    assert restored_intent.current_binding["actual_handle_id"] == "WH-0001"
    assert restored_intent.binding_history[0]["round"] == 1


def test_round11_v5_state_migrates_without_inventing_witness_intents(tmp_path):
    state, _, _, _ = witness_state(tmp_path)
    payload = state.to_dict()
    payload["schema_version"] = OBLIGATION_RUN_SCHEMA_VERSION
    payload.pop("witness_intents")
    for attempt in payload["attempts"].values():
        attempt.pop("witness_catalog_digest")

    restored = RunState.from_dict(payload)

    assert restored.witness_intents == {}
    assert all(
        attempt.witness_catalog_digest == ""
        for attempt in restored.attempts.values()
    )


def test_same_attempt_catalog_digest_change_fails_closed(tmp_path):
    state, task, attempt, intent = witness_state(tmp_path)
    store = LongHorizonStore(tmp_path / "store")
    controller = LongHorizonController(store)
    first = controller.witness_catalog.build(state, task, attempt, [intent])
    attempt.witness_catalog_digest = first["catalog_digest"]
    (Path(state.goal.workspace_root) / "result.txt").write_text(
        "changed", encoding="utf-8"
    )

    with pytest.raises(WitnessCatalogError, match="digest changed"):
        controller._build_task_witness_catalog(
            state,
            task,
            attempt,
            [intent],
            allow_intent_revision_change=False,
        )


def test_rwkv_precommits_witness_intent_before_action_result(tmp_path):
    state, task, _, _ = witness_state(tmp_path)
    payload = {
        "schema_version": "long-horizon.witness-intents.v1",
        "witness_intents": [
            {
                "criterion_id": "GC1",
                "subject_task_id": "T2",
                "producer_task_id": "T2",
                "comparison": "exact_equals",
                "actual_source_kind": "workspace",
                "expected_source_kind": "goal_literal",
                "expected_goal_literal": {"goal_quote": "good", "value": "good"},
            }
        ],
    }

    class Client:
        def __init__(self):
            self.prompts = []

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.prompts.append(prompt)
            return type("Response", (), {"content": json.dumps(payload)})()

    client = Client()
    model = LongHorizonModel(ModelInvoker(client=client))
    intents = model.prepare_witness_intents(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
    )

    assert len(intents) == 1
    assert intents[0].actual_source_kind == "workspace"
    assert intents[0].expected_goal_literal["value"] == "good"
    assert "Precommit the evidence intent" in client.prompts[0]
    assert "OBSERVED ACTION RESULT" not in client.prompts[0]


def test_rwkv_v6_progressively_selects_goal_literal_after_action(tmp_path):
    state, task, attempt, _ = witness_state(tmp_path)
    builder = WitnessCatalogBuilder(CriterionProofEngine())
    discovery = builder.build(state, task, attempt, [])
    actual_source = next(
        item
        for item in discovery["sources"]
        if item["source_kind"] == "workspace"
        and "workspace_text" in item["read_ops"]
        and item.get("locator", {}).get("path") == "result.txt"
    )
    payload = {
        "schema_version": "long-horizon.witness-binding.v1",
        "decision": "pass",
        "witness_selections": [
            {
                "criterion_id": "GC1",
                "actual_source_handle_id": actual_source["source_handle_id"],
                "expected_goal_quote": "good",
                "expected_goal_value": "good",
            }
        ],
    }

    class Client:
        def __init__(self):
            self.prompts = []

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.prompts.append(prompt)
            if "long-horizon.witness-mode.v1" in prompt:
                return type(
                    "Response",
                    (),
                    {
                        "content": json.dumps(
                            {
                                "schema_version": "long-horizon.witness-mode.v1",
                                "decision": "goal_literal",
                            }
                        )
                    },
                )()
            return type("Response", (), {"content": json.dumps(payload)})()

    client = Client()
    proposal = LongHorizonModel(ModelInvoker(client=client)).select_witness_sources(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result=attempt.tool_result,
        validation_results=[],
        witness_catalog=discovery,
    )

    assert proposal.decision == "pass"
    assert proposal.intents[0].producer_task_id == task.task_id
    assert proposal.intents[0].actual_source_kind == "workspace"
    assert proposal.intents[0].expected_source_kind == "goal_literal"
    assert proposal.reason == ""
    assert proposal.reason_provided is False
    assert proposal.selection_notes == {
        "GC1": {"provided": False, "value": None}
    }
    assert "OBSERVED ACTION RESULT" in client.prompts[0]
    assert "COMPLETE RAW SOURCE CATALOG" in client.prompts[0]
    assert "expected_source_handle_id" not in client.prompts[1]
    final_catalog = builder.build(state, task, attempt, proposal.intents)
    assert actual_source["source_handle_id"] in {
        item["source_handle_id"] for item in final_catalog["sources"]
    }


def test_rwkv_v6_progressively_selects_catalog_source_without_literal(tmp_path):
    state, task, attempt, _ = witness_state(tmp_path)
    discovery = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, []
    )
    actual_source = next(
        item
        for item in discovery["sources"]
        if item["source_kind"] == "workspace"
        and "workspace_text" in item["read_ops"]
        and item.get("locator", {}).get("path") == "result.txt"
    )
    expected_source = next(
        item
        for item in discovery["sources"]
        if "expected" in item.get("eligible_sides", [])
    )
    payload = {
        "schema_version": "long-horizon.witness-binding.v1",
        "decision": "pass",
        "witness_selections": [
            {
                "criterion_id": "GC1",
                "actual_source_handle_id": actual_source["source_handle_id"],
                "expected_source_handle_id": expected_source["source_handle_id"],
            }
        ],
    }

    class Client:
        def __init__(self):
            self.prompts = []

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.prompts.append(prompt)
            if "long-horizon.witness-mode.v1" in prompt:
                return type(
                    "Response",
                    (),
                    {
                        "content": json.dumps(
                            {
                                "schema_version": "long-horizon.witness-mode.v1",
                                "decision": "catalog_source",
                            }
                        )
                    },
                )()
            return type("Response", (), {"content": json.dumps(payload)})()

    client = Client()
    proposal = LongHorizonModel(ModelInvoker(client=client)).select_witness_sources(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result=attempt.tool_result,
        validation_results=[],
        witness_catalog=discovery,
    )

    assert proposal.intents[0].expected_source_kind == expected_source["source_kind"]
    assert proposal.intents[0].expected_goal_literal == {}
    assert "expected_goal_quote" not in client.prompts[1]
    assert proposal.source_selections[0]["expected_source_handle_id"] == expected_source[
        "source_handle_id"
    ]


def test_rwkv_v6_mode_replan_does_not_request_binding(tmp_path):
    state, task, attempt, _ = witness_state(tmp_path)
    discovery = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, []
    )

    class Client:
        def __init__(self):
            self.calls = 0

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.calls += 1
            return type(
                "Response",
                (),
                {
                    "content": json.dumps(
                        {
                            "schema_version": "long-horizon.witness-mode.v1",
                            "decision": "replan",
                        }
                    )
                },
            )()

    client = Client()
    proposal = LongHorizonModel(ModelInvoker(client=client)).select_witness_sources(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result=attempt.tool_result,
        validation_results=[],
        witness_catalog=discovery,
    )

    assert proposal.decision == "replan"
    assert proposal.intents == []
    assert client.calls == 1


def test_rwkv_v6_rejects_mode_extra_fields_before_binding(tmp_path):
    state, task, attempt, _ = witness_state(tmp_path)
    discovery = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, []
    )

    class Client:
        def text_completion(self, prompt, max_tokens=768, stop=None):
            return type(
                "Response",
                (),
                {
                    "content": json.dumps(
                        {
                            "schema_version": "long-horizon.witness-mode.v1",
                            "decision": "catalog_source",
                            "expected_source_handle_id": "WS-UNKNOWN",
                        }
                    )
                },
            )()

    with pytest.raises(
        ModelProtocolError,
        match="witness mode requires exactly schema_version and decision",
    ):
        LongHorizonModel(ModelInvoker(client=Client())).select_witness_sources(
            state,
            task,
            WorkingMemoryBuilder().build_task_validation(state, task),
            lambda *_args: None,
            action_result=attempt.tool_result,
            validation_results=[],
            witness_catalog=discovery,
        )


def test_rwkv_v6_rejects_other_branch_fields_without_dropping_them(tmp_path):
    state, task, attempt, _ = witness_state(tmp_path)
    discovery = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, []
    )
    actual_source = next(
        item
        for item in discovery["sources"]
        if item["source_kind"] == "workspace"
        and "workspace_text" in item["read_ops"]
        and item.get("locator", {}).get("path") == "result.txt"
    )
    expected_source = next(
        item
        for item in discovery["sources"]
        if "expected" in item.get("eligible_sides", [])
    )
    payload = {
        "schema_version": "long-horizon.witness-binding.v1",
        "decision": "pass",
        "witness_selections": [
            {
                "criterion_id": "GC1",
                "actual_source_handle_id": actual_source["source_handle_id"],
                "expected_source_handle_id": expected_source["source_handle_id"],
                "expected_goal_quote": "good",
                "expected_goal_value": "good",
            }
        ],
    }

    class Client:
        def text_completion(self, prompt, max_tokens=768, stop=None):
            if "long-horizon.witness-mode.v1" in prompt:
                return type(
                    "Response",
                    (),
                    {
                        "content": json.dumps(
                            {
                                "schema_version": "long-horizon.witness-mode.v1",
                                "decision": "catalog_source",
                            }
                        )
                    },
                )()
            return type("Response", (), {"content": json.dumps(payload)})()

    with pytest.raises(
        ModelProtocolError,
        match="catalog_source witness binding requires exactly",
    ):
        LongHorizonModel(ModelInvoker(client=Client())).select_witness_sources(
            state,
            task,
            WorkingMemoryBuilder().build_task_validation(state, task),
            lambda *_args: None,
            action_result=attempt.tool_result,
            validation_results=[],
            witness_catalog=discovery,
        )


@pytest.mark.parametrize(
    ("selection", "message"),
    [
        (
            {
                "criterion_id": "GC1",
                "actual_source_handle_id": "WS-UNKNOWN",
                "expected_mode": "goal_literal",
                "expected_goal_quote": "good",
                "expected_goal_value": "good",
            },
            "catalog_source witness binding requires exactly",
        ),
        (
            {
                "criterion_id": "GC1",
                "actual_source_handle_id": "WS-UNKNOWN",
                "expected": {"kind": "catalog_source", "source_handle_id": "WS-UNKNOWN"},
            },
            "catalog_source witness binding requires exactly",
        ),
    ],
)
def test_rwkv_v6_rejects_old_binding_shapes(
    tmp_path, selection, message
):
    state, task, attempt, _ = witness_state(tmp_path)
    discovery = WitnessCatalogBuilder(CriterionProofEngine()).build(
        state, task, attempt, []
    )
    selection = dict(selection)
    selection["actual_source_handle_id"] = next(
        item["source_handle_id"]
        for item in discovery["sources"]
        if item["source_kind"] == "workspace"
        and "workspace_text" in item["read_ops"]
        and item.get("locator", {}).get("path") == "result.txt"
    )
    payload = {
        "schema_version": "long-horizon.witness-binding.v1",
        "decision": "pass",
        "witness_selections": [selection],
    }

    class Client:
        def text_completion(self, prompt, max_tokens=768, stop=None):
            if "long-horizon.witness-mode.v1" in prompt:
                return type(
                    "Response",
                    (),
                    {
                        "content": json.dumps(
                            {
                                "schema_version": "long-horizon.witness-mode.v1",
                                "decision": "catalog_source",
                            }
                        )
                    },
                )()
            return type("Response", (), {"content": json.dumps(payload)})()

    with pytest.raises(ModelProtocolError, match=message):
        LongHorizonModel(ModelInvoker(client=Client())).select_witness_sources(
            state,
            task,
            WorkingMemoryBuilder().build_task_validation(state, task),
            lambda *_args: None,
            action_result=attempt.tool_result,
            validation_results=[],
            witness_catalog=discovery,
        )


class CountingHarness(ActionHarness):
    def __init__(self):
        super().__init__()
        self.execute_count = 0

    def execute(self, action, goal):
        self.execute_count += 1
        return super().execute(action, goal)


class LocalWitnessRevisionModel:
    def __init__(self):
        self.precommit_calls = 0
        self.cross_calls = 0
        self.final_calls = 0

    def prepare_witness_intents(
        self,
        state,
        task,
        context,
        persist,
        *,
        previous_intents=None,
        proof_feedback=None,
    ):
        self.precommit_calls += 1
        return [
            WitnessIntentState(
                intent_id=f"WI-{task.task_id}-GC1",
                task_id=task.task_id,
                criterion_id="GC1",
                subject_task_id=task.task_id,
                producer_task_id=task.task_id,
                comparison="exact_equals",
                actual_source_kind="workspace",
                expected_source_kind="goal_literal",
                expected_goal_literal={"goal_quote": "good", "value": "good"},
            )
        ]

    def cross_validate(
        self,
        state,
        task,
        context,
        persist,
        *,
        action_result=None,
        validation_results=None,
        witness_intents=None,
        witness_catalog=None,
        binding_feedback=None,
    ):
        self.cross_calls += 1
        transforms = [{"transform_op": "count"}] if self.cross_calls == 1 else []
        actual = select_handle(
            witness_catalog,
            source_kind="workspace",
            read_op="workspace_text",
            transforms=transforms,
            path="result.txt",
        )
        expected = select_handle(
            witness_catalog,
            source_kind="goal_literal",
            read_op="goal_literal",
            transforms=[],
        )
        intent = witness_intents[0]
        bindings = [
            {
                "intent_id": intent.intent_id,
                "criterion_id": intent.criterion_id,
                "actual_handle_id": actual["handle_id"],
                "expected_handle_id": expected["handle_id"],
            }
        ]
        assertions = expand_witness_bindings(
            witness_intents, bindings, witness_catalog
        )
        return CrossValidationDecision(
            passed=True,
            reason="RWKV fixture selects handles",
            criterion_assertions=assertions,
            criterion_assertion_intents=[item.to_dict() for item in witness_intents],
            witness_bindings=bindings,
            witness_decision="pass",
        )

    def final_answer(self, state, context, persist):
        self.final_calls += 1
        return "verified final"


class ActionThenIntentModel(LocalWitnessRevisionModel):
    def __init__(self):
        super().__init__()
        self.action_seen_at_precommit = ""

    def propose_action(self, state, task, context, action_contract, persist):
        return TaskAction(
            "write_file", {"path": "result.txt", "content": "good"}
        )

    def prepare_witness_intents(self, state, task, context, persist, **kwargs):
        self.action_seen_at_precommit = task.action.action_type
        return super().prepare_witness_intents(
            state, task, context, persist, **kwargs
        )


def test_controller_prepares_legacy_intent_only_after_action_execution(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    store = LongHorizonStore(tmp_path / "state")
    goal = GoalState.create(
        objective="Write good",
        original_request="Write exactly good to result.txt.",
        constraints=["Stay in workspace"],
        success_criteria=[GoalCriterion("GC1", "result.txt is exactly good")],
        workspace_root=workspace,
    )
    state = store.create_run(goal, "WITNESS-ACTION-THEN-INTENT")
    state.tasks = {
        "T1": TaskNode(
            "T1",
            "Write result",
            "Select, execute, and prove the write",
            satisfies_criteria=["GC1"],
            action=TaskAction("model_action", {}),
            completion_criteria=[
                ValidationSpec(
                    "file_content",
                    {"path": "result.txt", "expected_content": "good"},
                )
            ],
        )
    }
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")
    model = ActionThenIntentModel()

    result = LongHorizonController(store, model=model).run(state.run_id)

    assert result.state.status == RunStatus.COMPLETED
    assert model.action_seen_at_precommit == "write_file"
    event_types = [item["type"] for item in store.event_records(state.run_id)]
    assert event_types.index("action_selected") < event_types.index(
        "attempt_started"
    ) < event_types.index("action_returned") < event_types.index(
        "legacy_witness_intents_prepared_after_action"
    )


def test_controller_rebinds_witness_without_reexecuting_successful_action(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    store = LongHorizonStore(tmp_path / "state")
    goal = GoalState.create(
        objective="Write good",
        original_request="Write exactly good to result.txt.",
        constraints=["Stay in workspace"],
        success_criteria=[GoalCriterion("GC1", "result.txt is exactly good")],
        workspace_root=workspace,
    )
    state = store.create_run(goal, "WITNESS-LOCAL-REVISION")
    task = TaskNode(
        "T1",
        "Write result",
        "Write and prove the exact result",
        satisfies_criteria=["GC1"],
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
        completion_criteria=[
            ValidationSpec(
                "file_content",
                {"path": "result.txt", "expected_content": "good"},
            )
        ],
    )
    state.tasks = {task.task_id: task}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")
    harness = CountingHarness()
    model = LocalWitnessRevisionModel()

    result = LongHorizonController(
        store,
        model=model,
        harness=harness,
    ).run(state.run_id)

    assert result.state.status == RunStatus.COMPLETED
    assert harness.execute_count == 1
    assert model.precommit_calls == 1
    assert model.cross_calls == 2
    assert model.final_calls == 1
    intent = result.state.witness_intents["WI-T1-GC1"]
    assert [item["proof_passed"] for item in intent.binding_history] == [
        False,
        True,
    ]
    assert intent.status == "verified"
    claims = list(result.state.criterion_claims.values())
    assert len(claims) == 2
    assert claims[0].passed is False
    assert claims[1].passed is True
    events = store.event_records(state.run_id)
    revision = next(
        item for item in events if item["type"] == "witness_binding_revision_requested"
    )
    assert revision["data"]["action_reexecuted"] is False


class ExplicitIntentRevisionModel(LocalWitnessRevisionModel):
    def prepare_witness_intents(
        self,
        state,
        task,
        context,
        persist,
        *,
        previous_intents=None,
        proof_feedback=None,
    ):
        self.precommit_calls += 1
        prior = previous_intents[0] if previous_intents else None
        return [
            WitnessIntentState(
                intent_id=f"WI-{task.task_id}-GC1",
                task_id=task.task_id,
                criterion_id="GC1",
                subject_task_id=task.task_id,
                producer_task_id=task.task_id,
                comparison="exact_equals",
                actual_source_kind=("workspace" if prior else "action_output"),
                expected_source_kind="goal_literal",
                expected_goal_literal={"goal_quote": "good", "value": "good"},
                revision=(prior.revision + 1 if prior else 0),
            )
        ]

    def cross_validate(
        self,
        state,
        task,
        context,
        persist,
        *,
        action_result=None,
        validation_results=None,
        witness_intents=None,
        witness_catalog=None,
        binding_feedback=None,
    ):
        if witness_intents[0].actual_source_kind == "action_output":
            self.cross_calls += 1
            return CrossValidationDecision(
                passed=False,
                reason="The precommitted actual source kind is wrong",
                criterion_assertions=[],
                criterion_assertion_intents=[
                    item.to_dict() for item in witness_intents
                ],
                witness_decision="revise_intent",
            )
        return super().cross_validate(
            state,
            task,
            context,
            persist,
            action_result=action_result,
            validation_results=validation_results,
            witness_intents=witness_intents,
            witness_catalog=witness_catalog,
            binding_feedback=binding_feedback,
        )


def test_controller_applies_explicit_rwkv_intent_revision_without_action_retry(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)
    store = LongHorizonStore(tmp_path / "state")
    goal = GoalState.create(
        objective="Write good",
        original_request="Write exactly good to result.txt.",
        constraints=["Stay in workspace"],
        success_criteria=[GoalCriterion("GC1", "result.txt is exactly good")],
        workspace_root=workspace,
    )
    state = store.create_run(goal, "WITNESS-INTENT-REVISION")
    task = TaskNode(
        "T1",
        "Write result",
        "Write and prove the exact result",
        satisfies_criteria=["GC1"],
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
        completion_criteria=[
            ValidationSpec(
                "file_content",
                {"path": "result.txt", "expected_content": "good"},
            )
        ],
    )
    state.tasks = {"T1": task}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")
    model = ExplicitIntentRevisionModel()
    harness = CountingHarness()

    result = LongHorizonController(
        store, model=model, harness=harness
    ).run(state.run_id)

    assert result.state.status == RunStatus.COMPLETED
    assert harness.execute_count == 1
    assert model.precommit_calls == 2
    assert model.cross_calls == 2
    intent = result.state.witness_intents["WI-T1-GC1"]
    assert intent.revision == 1
    assert intent.actual_source_kind == "workspace"
    assert len(intent.binding_history) == 2
    events = store.event_records(state.run_id)
    revised = next(item for item in events if item["type"] == "witness_intents_revised")
    assert revised["data"]["action_reexecuted"] is False
