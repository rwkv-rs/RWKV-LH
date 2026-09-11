from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from rwkv_lh.goal_state_protocols import executor_args_v7
from rwkv_lh.executor_provenance import (
    ExecutorProvenanceError,
    validate_executor_argument_provenance,
)
from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.schema import GoalState, TaskAction


def _goal(workspace: Path) -> GoalState:
    return GoalState.create(
        request="Use exact observed bytes.",
        constraints=("workspace only",),
        workspace_root=workspace,
    )


def _execute(
    harness: ActionHarness,
    goal: GoalState,
    operation: str,
    arguments: dict,
    *,
    require_success: bool = True,
) -> ActionResult:
    normalized = harness.normalize_action(TaskAction(operation, arguments))
    result = harness.execute(normalized, goal)
    if require_success:
        assert result.success, result.error
    return result


def _fact(
    action_id: str,
    operation: str,
    arguments: dict,
    result: ActionResult,
    *,
    focus: str,
) -> dict:
    return {
        "action_id": action_id,
        "operation": operation,
        "arguments": arguments,
        "result": LongHorizonModel._project_action_result(
            result.to_dict(),
            operation=operation,
            arguments=arguments,
            focus_text=focus,
        ),
    }


def _artifact_sha256(result: ActionResult, path: str) -> str:
    return next(item.sha256 for item in result.artifacts if item.path == path)


def test_replace_text_is_bound_to_exact_snapshot_and_byte_range(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "src/pricing.py"
    source = "def total(x):\n    return x + legacy_fee\n"
    (workspace / "src").mkdir()
    (workspace / path).write_text(source, encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    read_arguments = {"path": path, "max_tokens": 4096}
    result = _execute(harness, goal, "read_file", read_arguments)
    base_sha256 = _artifact_sha256(result, path)
    old = "    return x + legacy_fee"

    report = validate_executor_argument_provenance(
        "replace_text",
        {
            "path": path,
            "old": old,
            "new": "    return x * rate",
            "base_sha256": base_sha256,
        },
        current_requirement=(
            "Replace the current return with exactly `    return x * rate`."
        ),
        fact_records=[
            _fact(
                "A00001",
                "read_file",
                read_arguments,
                result,
                focus="current return",
            )
        ],
    )

    by_pointer = {item["argument_pointer"]: item for item in report["bindings"]}
    assert set(by_pointer) == {"/path", "/base_sha256", "/old", "/new"}
    assert by_pointer["/new"]["authority"] == "literal_current_requirement"
    locator = by_pointer["/old"]["locator"]
    exact = source.encode("utf-8")[locator["start_byte"] : locator["end_byte"]]
    assert exact.decode("utf-8") == old
    assert locator["snapshot_sha256"] == hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()
    assert locator["content_sha256"] == hashlib.sha256(
        old.encode("utf-8")
    ).hexdigest()


def test_rmw_rejects_stale_or_summary_only_source_literal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "settings.env"
    old = "REMOVE_THIS=true"
    (workspace / path).write_text(f"KEEP=true\n{old}\n", encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    read_arguments = {"path": path}
    result = _execute(harness, goal, "read_file", read_arguments)
    fact = _fact(
        "A00001",
        "read_file",
        read_arguments,
        result,
        focus=old,
    )

    with pytest.raises(ExecutorProvenanceError, match="base_sha256"):
        validate_executor_argument_provenance(
            "remove_line",
            {"path": path, "text": old, "base_sha256": "0" * 64},
            current_requirement="Remove the deprecated line.",
            fact_records=[fact],
        )

    fact["result"]["observation"]["exact_spans"] = []
    fact["result"]["error"] = {"message": f"summary says {old}"}
    with pytest.raises(ExecutorProvenanceError, match="exact fragment"):
        validate_executor_argument_provenance(
            "remove_line",
            {
                "path": path,
                "text": old,
                "base_sha256": _artifact_sha256(result, path),
            },
            current_requirement="Remove the deprecated line.",
            fact_records=[fact],
        )


def test_fact_and_span_identities_must_remain_exact(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "module.py"
    (workspace / path).write_text("VALUE = 'old'\n", encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    read_arguments = {"path": path}
    result = _execute(harness, goal, "read_file", read_arguments)
    fact = _fact("A00011", "read_file", read_arguments, result, focus="VALUE")
    arguments = {
        "path": path,
        "old": "VALUE = 'old'",
        "new": "VALUE = 'new'",
        "base_sha256": _artifact_sha256(result, path),
    }

    conflicting = dict(fact)
    conflicting["result"] = dict(fact["result"])
    conflicting["result"]["action_type"] = "read_json"
    with pytest.raises(ExecutorProvenanceError, match="conflicting operation"):
        validate_executor_argument_provenance(
            "replace_text",
            arguments,
            current_requirement="Replace the value.",
            fact_records=[conflicting],
        )

    forged = dict(fact)
    forged["result"] = dict(fact["result"])
    forged_observation = dict(fact["result"]["observation"])
    forged_spans = [dict(item) for item in forged_observation["exact_spans"]]
    forged_spans[0]["span_id"] = "forged-span"
    forged_observation["exact_spans"] = forged_spans
    forged["result"]["observation"] = forged_observation
    with pytest.raises(ExecutorProvenanceError, match="invalid span ID"):
        validate_executor_argument_provenance(
            "replace_text",
            arguments,
            current_requirement="Replace the value.",
            fact_records=[forged],
        )


def test_text_rmw_cannot_use_canonical_json_as_raw_file_bytes(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "config.json"
    (workspace / path).write_text(
        '{\n  "mode": "legacy"\n}\n', encoding="utf-8"
    )
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    read_arguments = {"path": path}
    result = _execute(harness, goal, "read_json", read_arguments)
    fact = _fact("A00012", "read_json", read_arguments, result, focus="mode")

    with pytest.raises(ExecutorProvenanceError, match="base_sha256"):
        validate_executor_argument_provenance(
            "replace_text",
            {
                "path": path,
                "old": '"mode":"legacy"',
                "new": '"mode":"stable"',
                "base_sha256": _artifact_sha256(result, path),
            },
            current_requirement="Change mode to stable.",
            fact_records=[fact],
        )

def test_patch_json_key_must_be_a_literal_canonical_json_key(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "channels.json"
    (workspace / path).write_text(
        '{"outer":{"release_green_channel":"active"},'
        '"release_blue_channel":"active","preserve":true}\n',
        encoding="utf-8",
    )
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    read_arguments = {"path": path, "max_tokens": 4096}
    result = _execute(harness, goal, "read_json", read_arguments)
    fact = _fact(
        "A00002",
        "read_json",
        read_arguments,
        result,
        focus="active channel",
    )

    report = validate_executor_argument_provenance(
        "patch_json",
        {
            "path": path,
            "updates": {"release_blue_channel": "stable"},
            "base_sha256": _artifact_sha256(result, path),
        },
        current_requirement="Set the active channel to stable.",
        fact_records=[fact],
    )
    assert any(
        item["argument_pointer"] == "/updates/release_blue_channel#key"
        and item["authority"] == "exact_canonical_json_key"
        for item in report["bindings"]
    )

    with pytest.raises(ExecutorProvenanceError, match="top-level key"):
        validate_executor_argument_provenance(
            "patch_json",
            {
                "path": path,
                "updates": {"release_green_channel": "stable"},
                "base_sha256": _artifact_sha256(result, path),
            },
            current_requirement="Set the active channel to stable.",
            fact_records=[fact],
        )


def test_harness_rejects_ambiguous_single_text_mutations(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "duplicate.py"
    source = "return value\nkeep = 1\nreturn value\n"
    target = workspace / path
    target.write_text(source, encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    base_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()

    replace_result = _execute(
        harness,
        goal,
        "replace_text",
        {
            "path": path,
            "old": "return value",
            "new": "return updated",
            "base_sha256": base_sha256,
            "all": False,
            "count": 1,
        },
        require_success=False,
    )
    assert not replace_result.success
    assert "ambiguous" in str(replace_result.error)
    assert target.read_text(encoding="utf-8") == source

    remove_result = _execute(
        harness,
        goal,
        "remove_line",
        {
            "path": path,
            "text": "return value",
            "base_sha256": base_sha256,
            "all": False,
        },
        require_success=False,
    )
    assert not remove_result.success
    assert "ambiguous" in str(remove_result.error)
    assert target.read_text(encoding="utf-8") == source


def test_read_continuation_must_equal_same_source_next_start_byte(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "events.log"
    (workspace / path).write_text(
        "".join(f"event {index:04d} payload payload payload\n" for index in range(900)),
        encoding="utf-8",
    )
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    read_arguments = {"path": path, "start_byte": 0, "max_tokens": 256}
    result = _execute(harness, goal, "read_file", read_arguments)
    cursor = result.metadata["next_start_byte"]
    fact = _fact(
        "A00003",
        "read_file",
        read_arguments,
        result,
        focus="continue",
    )

    report = validate_executor_argument_provenance(
        "read_file",
        {"path": path, "start_byte": cursor, "max_tokens": 256},
        current_requirement="Continue the same file.",
        fact_records=[fact],
    )
    assert report["bindings"][0]["argument_pointer"] == "/start_byte"

    with pytest.raises(ExecutorProvenanceError, match="next_start_byte"):
        validate_executor_argument_provenance(
            "read_file",
            {"path": path, "start_byte": cursor + 1, "max_tokens": 256},
            current_requirement="Continue the same file.",
            fact_records=[fact],
        )


def test_search_result_path_requires_verified_source_line_identity(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    selected_path = "services/alpha.py"
    (workspace / "services").mkdir(parents=True)
    (workspace / selected_path).write_text(
        "SERVICE_ENTRY = 'selected'\n", encoding="utf-8"
    )
    (workspace / "services/omega.py").write_text("OTHER = 1\n", encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    search_arguments = {
        "pattern": "SERVICE_ENTRY",
        "path": "services",
        "mode": "literal",
    }
    result = _execute(harness, goal, "search_text", search_arguments)
    fact = _fact(
        "A00004",
        "search_text",
        search_arguments,
        result,
        focus="SERVICE_ENTRY",
    )

    report = validate_executor_argument_provenance(
        "read_file",
        {"path": selected_path, "start_byte": 0},
        current_requirement="Read the file identified by the preceding search.",
        fact_records=[fact],
    )
    path_binding = next(
        item for item in report["bindings"] if item["argument_pointer"] == "/path"
    )
    assert path_binding["locator"]["source_span_id"].startswith("OBS-SPAN-")

    with pytest.raises(ExecutorProvenanceError, match="bound discovery"):
        validate_executor_argument_provenance(
            "read_file",
            {"path": "services/invented.py", "start_byte": 0},
            current_requirement="Read the file identified by the preceding search.",
            fact_records=[fact],
        )


def test_search_snapshot_authorizes_exact_text_rmw_without_redundant_read(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = "service.conf"
    source = "name=edge\nprotocol=v1\nfallback_protocol=v1\nprotocol=v1\n"
    (workspace / path).write_text(source, encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    search_arguments = {
        "pattern": "protocol=v1",
        "path": path,
        "mode": "literal",
    }
    result = _execute(harness, goal, "search_text", search_arguments)
    fact = _fact(
        "A00040",
        "search_text",
        search_arguments,
        result,
        focus="replace protocol=v1",
    )
    base_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()

    report = validate_executor_argument_provenance(
        "replace_text",
        {
            "path": path,
            "old": "protocol=v1",
            "new": "protocol=v2",
            "base_sha256": base_sha256,
            "all": True,
        },
        current_requirement="Replace every protocol=v1 with protocol=v2.",
        fact_records=[fact],
    )

    by_pointer = {item["argument_pointer"]: item for item in report["bindings"]}
    assert by_pointer["/base_sha256"]["authority"] == (
        "harness_search_source_snapshot_identity"
    )
    assert by_pointer["/old"]["locator"]["source_ref"] == path
    assert by_pointer["/old"]["locator"]["snapshot_sha256"] == base_sha256
    with pytest.raises(ExecutorProvenanceError, match="exact fragment"):
        validate_executor_argument_provenance(
            "replace_text",
            {
                "path": path,
                "old": "name=edge",
                "new": "name=core",
                "base_sha256": base_sha256,
            },
            current_requirement="Change the service name.",
            fact_records=[fact],
        )


def test_controller_target_contract_authorizes_direct_root_after_other_discovery(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "left.txt").write_text("alpha\n", encoding="utf-8")
    (workspace / "merged.txt").write_text("gamma\n", encoding="utf-8")
    goal = _goal(workspace)
    harness = ActionHarness(sandbox_commands=False)
    search_arguments = {
        "pattern": "gamma",
        "path": "merged.txt",
        "mode": "literal",
    }
    search_result = _execute(harness, goal, "search_text", search_arguments)
    fact = _fact(
        "A00041",
        "search_text",
        search_arguments,
        search_result,
        focus="verify merged output",
    )
    descriptor = harness.workspace_target_descriptor(goal, "left.txt")
    execution_state = executor_args_v7.build_execution_state(
        active_step_id="S1", active_step_revision=1,
        declared_phase="observe", effective_phase="observe", assigned_actions=(),
        mechanical_evidence={"missing_read_roots": ["left.txt"]},
        target_contract=executor_args_v7.build_target_contract(
            phase="observe", roots=["left.txt"], target_descriptors=[descriptor],
            operations=("file_digest",),
        ),
    )

    report = validate_executor_argument_provenance(
        "file_digest",
        {"path": "left.txt"},
        current_requirement="Verify the declared source root.",
        fact_records=[fact],
        execution_state=execution_state,
    )

    assert report["bindings"] == [
        {
            "argument_pointer": "/path",
            "argument_value_sha256": report["bindings"][0][
                "argument_value_sha256"
            ],
            "authority": "controller_harness_target_contract",
            "locator": report["bindings"][0]["locator"],
        }
    ]
    assert report["bindings"][0]["locator"]["descriptor"]["path"] == "left.txt"


def test_command_repair_uses_exact_stderr_not_error_summary() -> None:
    config = "configs/release-blue.toml"
    output = f"REQUIRED_CONFIG={config}\n"
    result = ActionResult(
        "check_command",
        False,
        output=output,
        exit_code=2,
        metadata={
            "command_streams": {
                "stdout": {
                    "start_byte": 0,
                    "end_byte": 0,
                    "bytes": 0,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                },
                "stderr": {
                    "start_byte": 0,
                    "end_byte": len(output.encode("utf-8")),
                    "bytes": len(output.encode("utf-8")),
                    "sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                },
            }
        },
        error={"type": "CommandFailed", "message": "exit code 2"},
    )
    prior_arguments = {"argv": ["python", "checks/verify.py"]}
    fact = _fact(
        "A00005",
        "check_command",
        prior_arguments,
        result,
        focus="REQUIRED_CONFIG",
    )

    report = validate_executor_argument_provenance(
        "check_command",
        {"argv": ["python", "checks/verify.py", config]},
        current_requirement="Copy the exact REQUIRED_CONFIG value from stderr.",
        fact_records=[fact],
    )
    assert report["bindings"][0]["authority"] == "exact_command_stream"

    fact["result"]["command_streams"] = []
    fact["result"]["error"] = {"message": f"summary says {config}"}
    with pytest.raises(ExecutorProvenanceError, match="exact stderr/stdout"):
        validate_executor_argument_provenance(
            "check_command",
            {"argv": ["python", "checks/verify.py", config]},
            current_requirement="Copy the exact REQUIRED_CONFIG value from stderr.",
            fact_records=[fact],
        )
