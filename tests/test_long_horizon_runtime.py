import json
import time
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
from rwkv_lh.model import (
    LongHorizonModel,
    ModelProtocolError,
    extract_truncated_decision_object,
)
from rwkv_lh.schema import (
    GoalCriterion,
    GoalState,
    MemoryEntry,
    RunState,
    TaskAction,
    TaskNode,
    TaskStatus,
    ValidationResult,
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
    tool = next(
        item for item in harness.g1i_tool_definitions()
        if item["name"] == "inspect_custom"
    )
    assert tool["parameters"] == {
        "type": "object",
        "properties": {"value": {"description": "text", "type": "string"}},
        "required": [],
        "additionalProperties": False,
    }
    assert harness.deterministic_verification_specs(
        TaskAction("inspect_custom", {"value": "x"})
    ) is None


def test_failure_observation_cacheability_defaults_closed_and_is_not_model_input():
    definition = ActionDefinition(
        name="inspect_external",
        description="Read a changing external source.",
        read_only=True,
        side_effect=False,
        idempotent=True,
        default_timeout=5.0,
        argument_schema={},
    )

    def handler(goal, arguments):
        return ActionResult("inspect_external", True, output="same visible value")

    harness = ActionHarness(actions={"inspect_external": (definition, handler)})
    assert harness.definition("read_file").failure_observation_cacheable is True
    assert harness.definition("check_command").failure_observation_cacheable is False
    assert harness.definition("run_command").failure_observation_cacheable is False
    assert harness.definition("noop").failure_observation_cacheable is False
    assert harness.definition("inspect_external").failure_observation_cacheable is False
    assert "failure_observation_cacheable" not in harness.action_definition_contract(
        "read_file"
    )


def test_task_batch_accepts_only_minimal_causal_contract_without_filling_fields():
    payload = {
        "local_id": "observe_config",
        "title": "Observe config",
        "description": "Read the current config state",
        "dependencies": [],
        "required": True,
        "priority": 50,
        "advances_criteria": ["GC1"],
        "satisfies_criteria": [],
        "retry_policy": {"max_attempts": 2, "replan_after": 1},
    }
    with pytest.raises(ModelProtocolError, match="unknown fields"):
        LongHorizonModel._task_nodes([payload])

    minimal = {
        "local_id": "observe_config",
        "title": "Observe config",
        "description": "Read the current config state",
        "dependencies": [],
        "postcondition": "The config presence and content are observed",
    }
    task = LongHorizonModel._task_nodes([minimal])[0]
    assert task.operation_kind == "unspecified"
    assert task.expected_outcomes == ["success"]
    assert task.advances_criteria == []
    assert task.satisfies_criteria == []
    assert task.postcondition == "The config presence and content are observed"


def test_workspace_observation_snapshot_is_content_exact_and_fails_closed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        goal = make_goal(workspace)
        path = workspace / "value.txt"
        path.write_text("alpha", encoding="utf-8")
        harness = ActionHarness()

        first = harness.workspace_observation_snapshot(goal)
        second = harness.workspace_observation_snapshot(goal)
        assert first["cacheable"] is True
        assert first["digest"] == second["digest"]
        assert first["entries"] == second["entries"]

        path.write_text("bravo", encoding="utf-8")
        changed = harness.workspace_observation_snapshot(goal)
        assert changed["cacheable"] is True
        assert changed["digest"] != first["digest"]

        (workspace / "linked.txt").symlink_to(path)
        linked = harness.workspace_observation_snapshot(goal)
        assert linked["cacheable"] is False
        assert linked["digest"] == ""
        assert linked["reason"].startswith("symbolic_link_not_cacheable:")


def test_command_timeout_terminates_descendant_process_tree():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        goal = make_goal(workspace)
        harness = ActionHarness()
        assert harness._bubblewrap is not None
        child = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c',"
            "\"import time; from pathlib import Path; time.sleep(0.8); "
            "Path('descendant-survived.txt').write_text('leaked')\"]); "
            "time.sleep(10)"
        )

        result = harness.execute(
            TaskAction(
                "check_command",
                {"argv": [sys.executable, "-c", child], "timeout": 0.2},
            ),
            goal,
        )

        assert result.success is False
        assert result.error is not None
        assert result.error["type"] == "TimeoutExpired"
        time.sleep(1.0)
        assert not (workspace / "descendant-survived.txt").exists()


def test_command_interface_resolves_python_alias_inside_the_same_sandbox():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        harness = ActionHarness()

        result = harness.execute(
            TaskAction(
                "check_command",
                {
                    "argv": ["python", "-c", "print('rwkv-lh-runtime-ok')"],
                    "cwd": ".",
                },
            ),
            goal,
        )

        assert result.success is True
        assert result.outcome_type == "success"
        assert result.output.strip() == "rwkv-lh-runtime-ok"
        assert result.metadata["argv"][0] == "python"
        assert Path(result.metadata["resolved_argv"][0]).resolve() == Path(
            sys.executable
        ).resolve()
        assert result.metadata["executable_resolution"] == (
            "python_alias_to_project_runtime"
        )


@pytest.mark.parametrize(
    ("error_type", "exit_code", "expected"),
    [
        ("FileNotFoundError", None, "not_found"),
        ("JSONDecodeError", None, "invalid"),
        ("FileExistsError", None, "conflict"),
        ("TimeoutExpired", None, "timeout"),
        ("CommandFailed", 2, "nonzero"),
        ("RuntimeError", None, "failed"),
    ],
)
def test_action_outcome_type_is_mechanically_derived(
    error_type,
    exit_code,
    expected,
):
    result = ActionResult(
        "fixture",
        False,
        exit_code=exit_code,
        error={"type": error_type, "message": "observed failure"},
    )
    assert result.outcome_type == expected
    assert ActionResult.from_dict(result.to_dict()).outcome_type == expected


@pytest.mark.parametrize(
    "action",
    [
        TaskAction("write_file", {"path": "x.txt", "content": "x"}),
        TaskAction("write_json", {"path": "x.json", "value": {"x": 1}}),
        TaskAction("replace_text", {"path": "x.txt", "old": "a", "new": "b"}),
        TaskAction("remove_line", {"path": "x.txt", "text": "a"}),
        TaskAction("append_file", {"path": "x.txt", "content": "a"}),
        TaskAction("delete_file", {"path": "x.txt"}),
        TaskAction("make_directory", {"path": "dir"}),
        TaskAction("copy_file", {"source": "x.txt", "destination": "y.txt"}),
        TaskAction("list_directory", {}),
        TaskAction("read_file", {"path": "x.txt"}),
        TaskAction("read_json", {"path": "x.json"}),
        TaskAction(
            "bind_evidence",
            {"path": "x.txt", "start_line": 1, "end_line": 1},
        ),
        TaskAction("check_command", {"argv": ["python", "-V"]}),
        TaskAction("run_command", {"argv": ["python", "-V"]}),
        TaskAction("noop", {}),
    ],
)
def test_builtin_actions_have_deterministic_contract_valid_verification(action):
    harness = ActionHarness()
    specs = harness.deterministic_verification_specs(action)
    assert specs
    for spec in specs:
        ValidationEngine.validate_spec_contract(spec)
    assert harness.missing_required_postconditions(
        action.action_type,
        [spec.kind for spec in specs],
    ) == []


def test_g1i_write_contract_makes_retry_semantics_explicit():
    tool = next(
        item for item in ActionHarness().g1i_tool_definitions()
        if item["name"] == "write_file"
    )
    assert tool["parameters"]["required"] == [
        "path",
        "content",
        "overwrite",
        "create_parents",
    ]
    assert tool["parameters"]["properties"]["overwrite"]["const"] is True


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


def test_list_directory_observes_empty_and_recursive_workspace_metadata():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "workspace"
        goal = make_goal(root)
        harness = ActionHarness()

        empty = harness.execute(TaskAction("list_directory", {}), goal)
        assert empty.success is True
        assert json.loads(empty.output)["entries"] == []

        (root / "nested").mkdir()
        (root / "nested" / "input.txt").write_text("visible", encoding="utf-8")
        recursive = harness.execute(
            TaskAction(
                "list_directory",
                {"path": ".", "recursive": True, "max_entries": 10},
            ),
            goal,
        )
        assert recursive.success is True
        assert json.loads(recursive.output)["entries"] == [
            {"path": "nested", "type": "directory"},
            {"path": "nested/input.txt", "size_bytes": 7, "type": "file"},
        ]
        assert harness.definition("list_directory").read_only is True


def test_list_directory_cursor_pages_cover_each_entry_once_in_stable_order():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "workspace"
        goal = make_goal(root)
        for index in range(11):
            (root / f"module_{index:02d}.py").write_text(
                f"VALUE = {index}\n",
                encoding="utf-8",
            )
        harness = ActionHarness()
        observed = []
        cursor = ""
        while True:
            arguments = {"path": ".", "recursive": True, "max_entries": 3}
            if cursor:
                arguments["start_after"] = cursor
            result = harness.execute(TaskAction("list_directory", arguments), goal)
            assert result.success is True
            payload = json.loads(result.output)
            observed.extend(item["path"] for item in payload["entries"])
            if not payload["truncated"]:
                assert payload["next_cursor"] == ""
                break
            cursor = payload["next_cursor"]
            assert cursor == payload["entries"][-1]["path"]

        assert observed == [f"module_{index:02d}.py" for index in range(11)]
        assert len(observed) == len(set(observed))


def test_read_file_cursor_pages_reconstruct_large_utf8_text_exactly():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "workspace"
        goal = make_goal(root)
        content = "".join(f"line-{index:05d}: 数据\n" for index in range(3000))
        (root / "large.py").write_text(content, encoding="utf-8")
        harness = ActionHarness()
        observed = []
        start = 0
        while True:
            result = harness.execute(
                TaskAction(
                    "read_file",
                    {"path": "large.py", "start_char": start, "max_chars": 4096},
                ),
                goal,
            )
            assert result.success is True
            observed.append(result.output)
            assert result.metadata["start_char"] == start
            if result.metadata["complete"]:
                assert result.metadata["next_start_char"] is None
                break
            start = result.metadata["next_start_char"]
            assert start == result.metadata["end_char"]

        assert "".join(observed) == content


def test_only_length_truncated_terminal_decision_reason_is_recoverable():
    recovered = extract_truncated_decision_object(
        '"schema_version":"long-horizon.failure-analysis.v1",'
        '"decision":"replan","reason":"Repeated but already decisive'
    )
    assert recovered == {
        "schema_version": "long-horizon.failure-analysis.v1",
        "decision": "replan",
        "reason": "Repeated but already decisive",
    }
    with pytest.raises(ModelProtocolError, match="reason is complete"):
        extract_truncated_decision_object(
            '"schema_version":"long-horizon.failure-analysis.v1",'
            '"decision":"replan","reason":"complete" trailing'
        )


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
    with pytest.raises(HarnessError, match="must be workspace-relative"):
        harness.validate_action_contract(
            TaskAction(
                "run_command",
                {"argv": ["python", "-V"], "cwd": "/tmp/workspace"},
            )
        )
    with pytest.raises(HarnessError, match="preserve idempotent retry"):
        harness.validate_action_contract(
            TaskAction(
                "write_file",
                {"path": "result.txt", "content": "ok", "overwrite": False},
            )
        )


@pytest.mark.parametrize("count", [-1, 0, True, "2"])
def test_round38_replace_text_rejects_invalid_count_without_coercion(count):
    harness = ActionHarness()
    with pytest.raises(HarnessError, match="count must be a positive integer"):
        harness.validate_action_contract(
            TaskAction(
                "replace_text",
                {
                    "path": "service.conf",
                    "old": "protocol=v1",
                    "new": "protocol=v2",
                    "count": count,
                },
            )
        )


def test_round38_replace_text_direct_execute_does_not_reinterpret_invalid_count():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        goal = make_goal(root)
        path = root / "service.conf"
        original = "protocol=v1\nprotocol=v1\n"
        path.write_text(original, encoding="utf-8")
        harness = ActionHarness()

        invalid = harness.execute(
            TaskAction(
                "replace_text",
                {
                    "path": "service.conf",
                    "old": "protocol=v1",
                    "new": "protocol=v2",
                    "count": -1,
                },
            ),
            goal,
        )

        assert invalid.success is False
        assert invalid.error["type"] == "HarnessError"
        assert path.read_text(encoding="utf-8") == original

        valid = TaskAction(
            "replace_text",
            {
                "path": "service.conf",
                "old": "protocol=v1",
                "new": "protocol=v2",
                "count": 2,
            },
        )
        harness.validate_action_contract(valid)
        result = harness.execute(valid, goal)
        assert result.success is True
        assert path.read_text(encoding="utf-8") == "protocol=v2\nprotocol=v2\n"


def test_round38_replace_text_g1i_schema_declares_positive_minimum():
    definition = next(
        item
        for item in ActionHarness().g1i_tool_definitions()
        if item["name"] == "replace_text"
    )

    assert definition["parameters"]["properties"]["count"] == {
        "type": "integer",
        "minimum": 1,
        "description": "positive replacement count",
    }


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


def test_rwkv_write_file_verification_design_requires_exact_content():
    harness = ActionHarness()
    assert harness.verification_design_required_postconditions("write_file") == (
        "file_exists",
        "file_content",
    )
    assert harness.missing_verification_design_postconditions(
        "write_file",
        ["file_exists"],
    ) == ["file_content"]
    assert harness.missing_verification_design_postconditions(
        "write_file",
        ["file_content"],
    ) == []


def test_model_cross_check_receives_all_deterministic_verifier_results():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        task = TaskNode(
            "T1",
            "Observe workspace",
            "List the workspace",
            completion_criteria=[
                ValidationSpec("model_cross_check", {}, True),
                ValidationSpec("action_succeeded", {}, True),
            ],
        )
        observed = []

        def cross_check(active_task, action_result, spec, prior_results):
            observed.extend(prior_results)
            return ValidationResult(
                "model_cross_check",
                True,
                spec.required,
                "deterministic evidence supplied",
                {},
            )

        summary = ValidationEngine().validate(
            task,
            ActionResult("list_directory", True, output="{}"),
            goal,
            cross_check=cross_check,
        )
        assert summary.passed is True
        assert [item.kind for item in observed] == ["action_succeeded"]
        assert [item.kind for item in summary.results] == [
            "action_succeeded",
            "model_cross_check",
        ]


def test_working_memory_selects_dependencies_and_excludes_noise():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory) / "workspace")
        state = RunState("LH-MEMORY", goal)
        state.tasks["T1"] = TaskNode(
            "T1",
            "Prepare",
            "Prepare dependency",
            status=TaskStatus.COMPLETED,
            subject_key="release/report",
            member_key="source",
            phase_key="observe",
            effect_targets=["source.txt"],
            postcondition="source is observed",
            outcome_type="success",
            output_refs=["M-DEP"],
        )
        state.tasks["T2"] = TaskNode(
            "T2",
            "Build report",
            "Use release evidence",
            dependencies=["T1"],
            dependency_outcomes={"T1": ["success"]},
            subject_key="release/report",
            member_key="report",
            phase_key="produce",
            effect_targets=["report.txt"],
            postcondition="report is produced",
        )
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
        causal = json.loads(bundle.causal_state)
        assert causal["direct_dependencies"][0]["outcome_type"] == "success"
        assert causal["direct_dependencies"][0][
            "allowed_outcomes_for_active_task"
        ] == ["success"]


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
    obligation = policy.decide("goal_obligation_planning")
    obligation_replan = policy.decide("goal_obligation_replan")
    assert strict.temperature == 0.02
    assert first_replan.temperature == 0.28
    assert repeated_replan.temperature == 0.52
    assert reset_replan.temperature == 0.28
    assert failure_analysis.temperature == 0.10
    assert obligation.temperature == 0.18
    assert obligation_replan.temperature == 0.18
