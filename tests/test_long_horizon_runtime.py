import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from rwkv_lh.harness import (
    ActionDefinition,
    ActionHarness,
    ActionResult,
    HarnessError,
)
from rwkv_lh.memory import ContextBundle, MemoryBudgets, WorkingMemoryBuilder
from rwkv_lh.model import LongHorizonModel
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
from rwkv_lh.runtime.settings import get_runtime_settings
from rwkv_lh.token_budget import get_token_count
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


def test_workspace_manifest_is_metadata_only_and_skips_local_caches():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "workspace"
        goal = make_goal(root)
        (root / "input.txt").write_text("visible content", encoding="utf-8")
        (root / ".git").mkdir()
        (root / ".git" / "secret.txt").write_text("ignored", encoding="utf-8")
        manifest = ActionHarness().workspace_manifest(goal)
        assert [item["path"] for item in manifest["entries"]] == ["input.txt"]
        assert "content" not in manifest["entries"][0]
        assert len(manifest["entries"][0]["sha256"]) == 64


def test_structured_action_contract_rejects_missing_and_unknown_arguments():
    harness = ActionHarness()
    with pytest.raises(HarnessError, match="missing required arguments"):
        harness.validate_action_contract(
            TaskAction("write_file", {"path": "result.txt"})
        )
    with pytest.raises(HarnessError, match="unknown arguments"):
        harness.validate_action_contract(
            TaskAction(
                "write_file",
                {"path": "result.txt", "content": "ok", "body": "wrong"},
            )
        )


def test_structured_verifier_contract_rejects_parameter_alias_hallucination():
    with pytest.raises(ValueError, match="missing required parameters"):
        ValidationEngine.validate_spec_contract(
            ValidationSpec(
                "file_contains",
                {"path": "result.txt", "content": "verified"},
            )
        )
    ValidationEngine.validate_spec_contract(
        ValidationSpec(
            "file_contains",
            {"path": "result.txt", "text": "verified"},
        )
    )
    # Extra verifier metadata is read-only and cannot alter verifier semantics.
    ValidationEngine.validate_spec_contract(
        ValidationSpec("action_succeeded", {"action_id": "T1"})
    )


def test_plan_contract_accepts_delayed_model_action():
    task = TaskNode(
        "T1",
        "Modify after inspection",
        "Select the concrete edit only after a dependency is read",
        action=TaskAction("model_action", {}),
        completion_criteria=[
            ValidationSpec("file_contains", {"path": "result.txt", "text": "verified"})
        ],
    )
    LongHorizonModel(action_contract="{}")._validate_task_contracts([task])


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


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_command_sandbox_prevents_writes_outside_workspace():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        goal = make_goal(root / "workspace")
        result = ActionHarness().execute(
            TaskAction(
                "run_command",
                {
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('../escape.txt').write_text('bad')",
                    ]
                },
            ),
            goal,
        )
        assert result.success is False
        assert result.metadata["sandboxed"] is True
        assert not (root / "escape.txt").exists()


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_command_sandbox_cannot_read_hidden_files_outside_workspace():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        goal = make_goal(root / "workspace")
        hidden = root / "hidden_acceptance.json"
        hidden.write_text('{"answer":"must stay hidden"}', encoding="utf-8")
        result = ActionHarness().execute(
            TaskAction(
                "check_command",
                {
                    "argv": [
                        sys.executable,
                        "-c",
                        f"from pathlib import Path; print(Path({str(hidden)!r}).read_text())",
                    ]
                },
            ),
            goal,
        )
        assert result.success is False
        assert "must stay hidden" not in result.output


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


def test_read_json_is_a_real_structured_observation_action():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        path = Path(goal.workspace_root) / "value.json"
        path.write_text('{"z": 2, "a": 1}\n', encoding="utf-8")
        harness = ActionHarness()
        action = TaskAction("read_json", {"path": "value.json"})
        harness.validate_action_contract(action)
        result = harness.execute(action, goal)
        assert result.success is True
        assert json.loads(result.output) == {"a": 1, "z": 2}
        assert result.metadata["json_type"] == "dict"


def test_remove_line_is_idempotent_and_replace_text_requires_only_file_survival():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        path = Path(goal.workspace_root) / "settings.txt"
        path.write_text("enabled=true\ndeprecated=true\nmode=safe\n", encoding="utf-8")
        harness = ActionHarness()
        assert harness.definition("replace_text").required_postconditions == (
            "file_exists",
        )
        action = TaskAction(
            "remove_line",
            {"path": "settings.txt", "text": "deprecated=true"},
        )
        first = harness.execute(action, goal)
        second = harness.execute(action, goal)
        assert first.success is True
        assert second.success is True
        assert path.read_text(encoding="utf-8") == "enabled=true\nmode=safe\n"
        assert second.output == "line already absent"


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


def test_request_specific_context_projection_preserves_goal_and_prompt_template():
    context = ContextBundle(
        goal="IMMUTABLE GOAL\nkeep-this-goal",
        task="ACTIVE TASK\nkeep-this-task",
        dependencies=["dependency observation" * 100],
        evidence=["general evidence" * 20_000],
        failure="latest failure",
    )
    prompt = LongHorizonModel._json_prompt_with_context(
        "FIXED PREFIX\n__RWKV_LH_BOUNDED_CONTEXT__\nFIXED SUFFIX",
        context,
        5000,
    )
    runtime = get_runtime_settings()
    assert "FIXED PREFIX" in prompt and "FIXED SUFFIX" in prompt
    assert "keep-this-goal" in prompt and "keep-this-task" in prompt
    assert get_token_count(prompt) <= runtime.max_prompt_tokens(5000)
    assert "general evidence" not in prompt


def test_temperature_policy_only_escalates_exploration():
    policy = TemperaturePolicy()
    strict = policy.decide("evidence_extract", same_failure_count=4)
    first_replan = policy.decide("replan", generation=1)
    repeated_replan = policy.decide("replan", generation=4, same_failure_count=3)
    reset_replan = policy.decide("replan", generation=4, same_failure_count=3, new_evidence=True)
    failure_analysis = policy.decide("failure_analysis", same_failure_count=4)
    assert strict.temperature == 0.02
    assert first_replan.temperature == 0.28
    assert repeated_replan.temperature == 0.52
    assert reset_replan.temperature == 0.28
    assert failure_analysis.temperature == 0.10
