import json
import sys
import tempfile
from pathlib import Path

from rwkv_lh.harness import ActionDefinition, ActionHarness, ActionResult
from rwkv_lh.memory import MemoryBudgets, WorkingMemoryBuilder
from rwkv_lh.schema import (
    GoalCriterion,
    GoalState,
    MemoryEntry,
    RunState,
    TaskAction,
    TaskNode,
    ValidationSpec,
)
from rwkv_lh.temp_policy import TemperaturePolicy
from rwkv_lh.validation import ValidationEngine


def test_harness_extension_is_explicit_and_has_recovery_metadata():
    definition = ActionDefinition(
        name="inspect_custom",
        description="Return a deterministic custom observation.",
        read_only=True,
        side_effect=False,
        idempotent=True,
        default_timeout=5.0,
        argument_schema={"value": "text"},
    )

    def handler(goal, arguments):
        return ActionResult("inspect_custom", True, output=str(arguments["value"]))

    harness = ActionHarness(actions={"inspect_custom": (definition, handler)})
    assert harness.definition("inspect_custom") == definition
    assert '"inspect_custom"' in harness.action_contract()


def make_goal(root: Path) -> GoalState:
    root.mkdir(parents=True, exist_ok=True)
    return GoalState.create(
        objective="Complete a scoped task",
        original_request="Complete a scoped task and verify it",
        constraints=["Stay inside the workspace"],
        success_criteria=[GoalCriterion("GC1", "Required tasks are verified")],
        workspace_root=root,
    )


def test_harness_writes_and_validates_real_file():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        harness = ActionHarness()
        task = TaskNode(
            "T1",
            "Write artifact",
            "Write the required content",
            action=TaskAction("write_file", {"path": "artifact.txt", "content": "verified"}),
            completion_criteria=[ValidationSpec("file_contains", {"path": "artifact.txt", "text": "verified"})],
        )
        result = harness.execute(task.action, goal)
        validation = ValidationEngine(harness).validate(task, result, goal)
        assert result.success is True
        assert validation.required_passed is True
        assert (Path(goal.workspace_root) / "artifact.txt").read_text() == "verified"


def test_harness_rejects_workspace_escape():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        result = ActionHarness().execute(
            TaskAction("write_file", {"path": "../escaped.txt", "content": "bad"}),
            goal,
        )
        assert result.success is False
        assert result.error["type"] == "ScopeViolation"
        assert not (Path(directory) / "escaped.txt").exists()


def test_command_uses_argv_and_validator_exit_code():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        task = TaskNode(
            "T1",
            "Run checker",
            "Execute an argv command",
            action=TaskAction(
                "run_command",
                {"argv": [sys.executable, "-c", "print('ok')"]},
            ),
            completion_criteria=[ValidationSpec("command_exit_code", {"expected": 0})],
        )
        result = ActionHarness().execute(task.action, goal)
        summary = ValidationEngine().validate(task, result, goal)
        assert result.output.strip() == "ok"
        assert summary.passed is True


def test_json_field_validation_reads_disk_state():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        task = TaskNode(
            "T1",
            "Write config",
            "Write structured configuration",
            action=TaskAction("write_json", {"path": "config.json", "value": {"feature": {"enabled": True}}}),
            completion_criteria=[
                ValidationSpec(
                    "json_field_equals",
                    {"path": "config.json", "field": "feature.enabled", "expected": True},
                )
            ],
        )
        result = ActionHarness().execute(task.action, goal)
        assert ValidationEngine().validate(task, result, goal).passed is True
        assert json.loads((Path(goal.workspace_root) / "config.json").read_text())["feature"]["enabled"] is True


def test_working_memory_selects_dependencies_and_excludes_noise():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        state = RunState("LH-MEMORY", goal)
        state.tasks["T1"] = TaskNode("T1", "Prepare", "Prepare dependency")
        state.tasks["T2"] = TaskNode("T2", "Build report", "Use release evidence", dependencies=["T1"])
        state.memory_index = {
            "M-DEP": MemoryEntry("M-DEP", "result", "T1", "dependency result", "use this"),
            "M-EVIDENCE": MemoryEntry(
                "M-EVIDENCE", "evidence", "OTHER", "release evidence", "bound fact", evidence_refs=["S1#L2"], tags=["release"]
            ),
            "M-NOISE": MemoryEntry("M-NOISE", "result", "NOISE", "noise", "x" * 20_000),
        }
        bundle = WorkingMemoryBuilder(MemoryBudgets(total_input=1200)).build(
            state,
            state.tasks["T2"],
            action_contract="write_file",
        )
        assert "M-DEP" in bundle.selected_memory_ids
        assert "M-EVIDENCE" in bundle.selected_memory_ids
        assert "M-NOISE" in bundle.excluded_memory_ids
        assert bundle.total_tokens <= 1200


def test_temperature_policy_only_escalates_exploration():
    policy = TemperaturePolicy()
    strict = policy.decide("evidence_extract", same_failure_count=4)
    first_replan = policy.decide("replan", generation=1)
    repeated_replan = policy.decide("replan", generation=4, same_failure_count=3)
    reset_replan = policy.decide("replan", generation=4, same_failure_count=3, new_evidence=True)
    assert strict.temperature == 0.02
    assert first_replan.temperature == 0.28
    assert repeated_replan.temperature == 0.52
    assert reset_replan.temperature == 0.52
