from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.harness import ActionHarness, HarnessError
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.observation_funnel import (
    OBSERVATION_PROJECTION_VERSION,
    ObservationProjectionError,
    REGISTERED_OPERATIONS,
    compact_action_result_projection,
    project_action_result,
)
from rwkv_lh.schema import TaskAction


def _goal(workspace: Path):
    return LongHorizonModel.create_literal_goal(
        "Repair exact_target without changing neighboring code.",
        str(workspace),
    )


def _execute(
    harness: ActionHarness,
    workspace: Path,
    operation: str,
    arguments: dict,
):
    result = harness.execute(TaskAction(operation, arguments), _goal(workspace))
    assert result.success, result.error
    return result


def test_read_file_projection_keeps_task_relevant_code_byte_exact(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = (
        "# 头部：保持不变\n"
        + "padding = 0\n" * 900
        + "def exact_target(value):\n    return value + 1  # 精确修改点\n"
        + "padding = 2\n" * 900
        + "# TAIL-CANARY\n"
    )
    path = workspace / "module.py"
    path.write_text(source, encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    result = _execute(
        harness,
        workspace,
        "read_file",
        {"path": "module.py", "max_tokens": 8192},
    )

    projected = project_action_result(
        result.to_dict(),
        operation="read_file",
        arguments={"path": "module.py"},
        focus_text="Fix exact_target and preserve neighboring code",
        max_exact_chars=1800,
    )

    observation = projected["observation"]
    assert observation["projection_version"] == OBSERVATION_PROJECTION_VERSION
    assert observation["projection_complete"] is False
    assert observation["source_chunk_integrity_valid"] is True
    spans = observation["exact_spans"]
    assert any("def exact_target" in span["content"] for span in spans)
    source_bytes = source.encode("utf-8")
    for span in spans:
        exact = source_bytes[span["start_byte"] : span["end_byte"]]
        assert exact.decode("utf-8") == span["content"]
        assert hashlib.sha256(exact).hexdigest() == span["content_sha256"]
        assert span["snapshot_sha256"] == hashlib.sha256(source_bytes).hexdigest()
        assert span["parent_chunk_sha256"] == hashlib.sha256(
            result.output.encode("utf-8")
        ).hexdigest()


def test_read_file_projection_rejects_false_chunk_identity(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "a.py").write_text("value = 1\n", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    result = _execute(harness, workspace, "read_file", {"path": "a.py"})
    value = result.to_dict()
    value["metadata"]["chunk"]["chunk_sha256"] = "0" * 64

    with pytest.raises(
        ObservationProjectionError,
        match="do not match chunk_sha256",
    ):
        project_action_result(value, operation="read_file")


def test_read_json_projection_separates_canonical_span_and_file_base_identity(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = '{\n  "preserve": true,\n  "mode": "old"\n}\n'
    (workspace / "config.json").write_text(source, encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    result = _execute(harness, workspace, "read_json", {"path": "config.json"})
    projected = project_action_result(result.to_dict(), operation="read_json")
    observation = projected["observation"]

    assert observation["source_chunk"]["source_ref"] == "config.json#canonical-json"
    assert observation["source_artifact"] == {
        "path": "config.json",
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "size_bytes": len(source.encode("utf-8")),
        "media_type": "application/json",
        "fact_authority": "harness_file_artifact_identity",
    }
    assert observation["exact_spans"][0]["content"] == '{"mode":"old","preserve":true}'
    assert (
        observation["exact_spans"][0]["snapshot_sha256"]
        != observation["source_artifact"]["sha256"]
    )


def test_invalid_json_is_successful_exact_negative_parse_evidence(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = '{"valid": true,\n "broken": ]}\n'
    (workspace / "candidate.json").write_text(source, encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)

    result = _execute(
        harness,
        workspace,
        "read_json",
        {"path": "candidate.json"},
    )
    diagnostic = json.loads(result.output)
    artifact = result.artifacts[0]

    assert result.outcome_type == "success"
    assert result.metadata["valid_json"] is False
    assert result.metadata["parse_outcome_complete"] is True
    assert diagnostic["valid_json"] is False
    assert diagnostic["source_sha256"] == hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()
    assert artifact.sha256 == diagnostic["source_sha256"]
    assert diagnostic["parse_error"] == {
        "byte_offset": 27,
        "character_offset": 27,
        "column": 12,
        "line": 2,
        "message": "Expecting value",
        "source_span": {
            "column_in_span": 12,
            "content": ' "broken": ]}',
            "content_sha256": hashlib.sha256(
                b' "broken": ]}'
            ).hexdigest(),
            "end_byte": 29,
            "line": 2,
            "start_byte": 16,
        },
        "type": "JSONDecodeError",
    }

    projected = project_action_result(
        result.to_dict(),
        operation="read_json",
        arguments={"path": "candidate.json"},
    )
    assert projected["success"] is True
    assert projected["metadata"]["valid_json"] is False
    assert projected["metadata"]["parse_outcome_complete"] is True
    assert projected["metadata"]["parse_error"] == diagnostic["parse_error"]
    assert projected["observation"]["source_artifact"]["sha256"] == diagnostic[
        "source_sha256"
    ]
    assert json.loads(projected["observation"]["exact_spans"][0]["content"])[
        "valid_json"
    ] is False


def test_compact_projection_keeps_negative_json_fact_and_exact_lineage(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = '{"value":'
    (workspace / "primary.json").write_text(source, encoding="utf-8")
    result = _execute(
        ActionHarness(sandbox_commands=False),
        workspace,
        "read_json",
        {"path": "primary.json"},
    )
    projected = project_action_result(
        result.to_dict(),
        operation="read_json",
        arguments={"path": "primary.json"},
        focus_text="Use backup.json when primary.json is not readable JSON",
        max_exact_chars=1200,
    )

    compact = compact_action_result_projection(
        projected,
        budget=2400,
        focus_text="Use backup.json when primary.json is not readable JSON",
    )
    encoded = json.dumps(
        compact,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert len(encoded) <= 2400
    assert compact["metadata"]["valid_json"] is False
    assert compact["metadata"]["parse_outcome_complete"] is True
    assert compact["metadata"]["parse_error"]["source_span"]["content"] == source
    assert compact["source_artifact"]["sha256"] == hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()
    assert compact["fact_authority"] == "literal_fields_and_exact_spans_only"
    for span in compact.get("exact_spans", []):
        content = span["content"].encode("utf-8")
        assert span["end_byte"] - span["start_byte"] == len(content)
        assert span["content_sha256"] == hashlib.sha256(content).hexdigest()


def test_compact_projection_never_slices_a_code_span_without_rehashing(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = "padding = 0\n" * 500 + "def exact_target():\n    return 7\n" + "tail = 1\n" * 500
    (workspace / "module.py").write_text(source, encoding="utf-8")
    result = _execute(
        ActionHarness(sandbox_commands=False),
        workspace,
        "read_file",
        {"path": "module.py", "max_tokens": 8192},
    )
    projected = project_action_result(
        result.to_dict(),
        operation="read_file",
        arguments={"path": "module.py"},
        focus_text="inspect exact_target",
        max_exact_chars=1800,
    )

    compact = compact_action_result_projection(
        projected,
        budget=1600,
        focus_text="inspect exact_target",
    )

    assert len(
        json.dumps(
            compact,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ) <= 1600
    assert compact["exact_spans"]
    assert any("exact_target" in span["content"] for span in compact["exact_spans"])
    source_bytes = source.encode("utf-8")
    for span in compact["exact_spans"]:
        exact = source_bytes[span["start_byte"] : span["end_byte"]]
        assert exact.decode("utf-8") == span["content"]
        assert hashlib.sha256(exact).hexdigest() == span["content_sha256"]


@pytest.mark.parametrize(
    ("operation", "filename", "source", "operation_arguments"),
    (
        (
            "replace_text",
            "module.py",
            "def exact_target():\n    return 'old'\n",
            {"old": "return 'old'", "new": "return 'new'", "count": 1},
        ),
        (
            "remove_line",
            "settings.env",
            "KEEP=true\nREMOVE_EXACTLY=true\nTAIL=true\n",
            {"text": "REMOVE_EXACTLY=true", "all": False},
        ),
        (
            "patch_json",
            "config.json",
            '{"mode":"old","preserve":true}\n',
            {"updates": {"mode": "new"}},
        ),
    ),
)
def test_read_modify_write_requires_the_exact_current_base_snapshot(
    tmp_path: Path,
    operation: str,
    filename: str,
    source: str,
    operation_arguments: dict,
) -> None:
    workspace = tmp_path / operation
    workspace.mkdir()
    path = workspace / filename
    path.write_text(source, encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    base_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    arguments = {
        "path": filename,
        **operation_arguments,
        "base_sha256": base_sha256,
    }

    with pytest.raises(HarnessError, match="missing required arguments"):
        harness.normalize_action(
            TaskAction(
                operation,
                {key: value for key, value in arguments.items() if key != "base_sha256"},
            )
        )

    changed = source + "# concurrent revision\n"
    path.write_text(changed, encoding="utf-8")
    stale = harness.execute(TaskAction(operation, arguments), _goal(workspace))
    assert stale.success is False
    assert stale.error is not None
    assert stale.error["type"] == "HarnessError"
    assert "stale source snapshot" in stale.error["message"]
    assert path.read_text(encoding="utf-8") == changed

    path.write_text(source, encoding="utf-8")
    committed = harness.execute(TaskAction(operation, arguments), _goal(workspace))
    assert committed.success is True
    assert committed.metadata["base_snapshot_sha256"] == base_sha256
    assert committed.metadata["snapshot_transition_verified"] is True
    assert committed.artifacts[0].sha256 == committed.metadata["result_snapshot_sha256"]
    projected = project_action_result(
        committed.to_dict(),
        operation=operation,
        arguments=arguments,
        focus_text="Verify the exact source-snapshot transition.",
    )
    assert projected["metadata"]["base_snapshot_sha256"] == base_sha256
    assert projected["metadata"]["result_snapshot_sha256"] == committed.artifacts[0].sha256
    assert projected["metadata"]["snapshot_transition_verified"] is True


def test_search_text_locators_recover_the_exact_unicode_source_bytes(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = "前缀🙂 value = 1\n目标 exact_target = value + 1\n"
    path = workspace / "unicode.py"
    path.write_text(source, encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    result = _execute(
        harness,
        workspace,
        "search_text",
        {
            "pattern": "exact_target",
            "path": "unicode.py",
            "mode": "literal",
            "max_tokens": 4096,
        },
    )

    payload = json.loads(result.output)
    match = payload["matches"][0]
    source_bytes = source.encode("utf-8")
    exact_line = source_bytes[
        match["line_text_start_byte"] : match["line_text_end_byte"]
    ]
    assert exact_line.decode("utf-8") == match["line_text"]
    assert hashlib.sha256(exact_line).hexdigest() == match["line_text_sha256"]
    assert payload["source_snapshots"]["unicode.py"] == hashlib.sha256(
        source_bytes
    ).hexdigest()

    projected = project_action_result(
        result.to_dict(),
        operation="search_text",
        arguments={"pattern": "exact_target", "path": "unicode.py"},
        structured_budget=4096,
    )
    projected_match = projected["structured_output"]["matches"][0]
    assert projected_match["source_span_id"].startswith("OBS-SPAN-")
    assert projected_match["source_snapshot_sha256"] == hashlib.sha256(
        source_bytes
    ).hexdigest()
    assert projected_match["line_text"] == exact_line.decode("utf-8")
    assert projected_match["fact_authority"] == "exact_utf8_source_line"


def test_list_directory_projection_cursor_does_not_skip_hidden_items(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for index in range(80):
        (workspace / f"item-{index:03d}.txt").write_text(str(index), encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    arguments = {
        "path": ".",
        "recursive": False,
        "max_entries": 100,
        "max_tokens": 8192,
    }
    result = _execute(harness, workspace, "list_directory", arguments)
    source = json.loads(result.output)
    projected = project_action_result(
        result.to_dict(),
        operation="list_directory",
        arguments=arguments,
        structured_budget=1200,
    )
    packet = projected["structured_output"]
    retained = packet["entries"]

    assert 0 < len(retained) < len(source["entries"])
    assert packet["entry_count"] == len(retained)
    assert packet["next_cursor"] == retained[-1]["path"]
    assert projected["observation"]["projection_complete"] is False
    resumed = _execute(
        harness,
        workspace,
        "list_directory",
        projected["observation"]["resume_arguments"],
    )
    resumed_entries = json.loads(resumed.output)["entries"]
    assert resumed_entries[0] == source["entries"][len(retained)]


def test_search_projection_cursor_does_not_skip_hidden_matches(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "many.py").write_text(
        "".join(f"exact_target_{index:03d} = {index}\n" for index in range(40)),
        encoding="utf-8",
    )
    harness = ActionHarness(sandbox_commands=False)
    arguments = {
        "pattern": "exact_target_",
        "path": "many.py",
        "mode": "literal",
        "max_results": 100,
        "max_tokens": 8192,
    }
    result = _execute(harness, workspace, "search_text", arguments)
    source = json.loads(result.output)
    projected = project_action_result(
        result.to_dict(),
        operation="search_text",
        arguments=arguments,
        structured_budget=3600,
    )
    packet = projected["structured_output"]
    retained = packet["matches"]

    assert 0 < len(retained) < len(source["matches"])
    assert packet["match_count"] == len(retained)
    resumed = _execute(
        harness,
        workspace,
        "search_text",
        {
            **arguments,
            **projected["observation"]["resume_arguments"],
        },
    )
    resumed_match = json.loads(resumed.output)["matches"][0]
    expected = source["matches"][len(retained)]
    assert (
        resumed_match["path"],
        resumed_match["line_number"],
        resumed_match["column"],
        resumed_match["end_column"],
    ) == (
        expected["path"],
        expected["line_number"],
        expected["column"],
        expected["end_column"],
    )


def test_command_projection_separates_streams_and_keeps_tail_exact(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    result = _execute(
        harness,
        workspace,
        "check_command",
        {
            "argv": [
                "python",
                "-c",
                (
                    "import sys; print('OUT-' + 'x'*3000); "
                    "sys.stderr.write('ERR-' + 'y'*3000 + '-TAIL-FAILURE\\n')"
                ),
            ],
            "expected_exit_code": 0,
        },
    )
    projected = project_action_result(
        result.to_dict(),
        operation="check_command",
        focus_text="TAIL-FAILURE",
        max_exact_chars=1000,
    )
    streams = {item["stream"]: item for item in projected["command_streams"]}

    assert set(streams) == {"stdout", "stderr"}
    assert any(
        "TAIL-FAILURE" in span["content"]
        for span in streams["stderr"]["exact_spans"]
    )
    for stream in streams.values():
        for span in stream["exact_spans"]:
            content = span["content"].encode("utf-8")
            assert hashlib.sha256(content).hexdigest() == span["content_sha256"]


def test_external_projection_promotes_relevant_late_source_with_exact_bytes() -> None:
    records = []
    for index in range(1, 6):
        text = (
            "Python Packaging User Guide official documentation URL"
            if index == 5
            else f"unrelated result {index}"
        )
        prefix = "前缀🙂 " if index == 5 else ""
        snapshot = prefix + text
        start_char = len(prefix)
        start_byte = len(prefix.encode("utf-8"))
        records.append(
            {
                "evidence_record_id": f"E-{index}",
                "source_object": {
                    "source_object_id": f"source:{index}",
                    "source_object_type": "public_web_page",
                },
                "snapshot_digest": hashlib.sha256(
                    snapshot.encode("utf-8")
                ).hexdigest(),
                "url": (
                    "https://packaging.python.org/"
                    if index == 5
                    else f"https://example.test/{index}"
                ),
                "title": text,
                "structured_fields": {},
                "exact_spans": [
                    {
                        "span_id": f"SPAN-{index}",
                        "text": text,
                        "locator": {
                            "start_char": start_char,
                            "end_char": start_char + len(text),
                            "start_byte": start_byte,
                            "end_byte": start_byte + len(text.encode("utf-8")),
                        },
                    }
                ],
            }
        )
    result = {
        "action_type": "web_search",
        "success": True,
        "outcome_type": "success",
        "output": "durable envelope",
        "evidence": records,
        "metadata": {
            "external_evidence": {
                "route_id": "ROUTE-1",
                "request_digest": "request-1",
                "status": "evidence_committed",
            }
        },
    }

    projected = project_action_result(
        result,
        operation="web_search",
        arguments={
            "query": "Python Packaging User Guide official documentation URL"
        },
        evidence_source_limit=2,
        evidence_span_chars=512,
    )

    assert projected["evidence_source_index"][0]["source_object_id"] == "source:5"
    assert projected["evidence"][0]["url"] == "https://packaging.python.org/"
    span = projected["evidence"][0]["exact_spans"][0]
    assert span["byte_locator_verified"] is True
    assert span["projection"]["document_start_byte"] == len("前缀🙂 ".encode("utf-8"))
    assert span["text"] == "Python Packaging User Guide official documentation URL"


def test_all_23_registered_operations_have_a_typed_adapter() -> None:
    short = {"success": True, "outcome_type": "success", "output": "ok"}
    for operation in sorted(REGISTERED_OPERATIONS):
        if operation in {"read_file", "read_json", "bind_evidence"}:
            # Missing local lineage is still represented exactly, but production
            # read_file/read_json results additionally carry a verified chunk.
            result = {**short, "action_type": operation}
        elif operation == "list_directory":
            result = {
                **short,
                "action_type": operation,
                "output": json.dumps(
                    {
                        "path": ".",
                        "recursive": False,
                        "entries": [],
                        "entry_count": 0,
                        "truncated": False,
                        "complete": True,
                        "next_cursor": "",
                    }
                ),
            }
        elif operation == "search_text":
            result = {
                **short,
                "action_type": operation,
                "output": json.dumps(
                    {
                        "schema_version": "rwkv-lh.search-text-result.v1",
                        "path": ".",
                        "pattern": "x",
                        "mode": "literal",
                        "case_sensitive": True,
                        "recursive": True,
                        "matches": [],
                        "source_snapshots": {},
                        "match_count": 0,
                        "files_considered": 0,
                        "files_searched": 0,
                        "skipped_file_count": 0,
                        "skipped_files": [],
                        "excluded_directory_count": 0,
                        "excluded_directories": [],
                        "truncated": False,
                        "complete": True,
                        "next_cursor": "",
                    }
                ),
            }
        else:
            result = {**short, "action_type": operation}
        projected = project_action_result(result, operation=operation)
        assert projected["observation"]["adapter_registered"] is True
        assert projected["observation"]["adapter"]


@pytest.mark.parametrize(
    ("operation", "filename", "source", "applied", "operation_arguments"),
    (
        (
            "replace_text",
            "settings.conf",
            "mode=old\nkeep=1\n",
            "mode=new\nkeep=1\n",
            {"old": "mode=old", "new": "mode=new"},
        ),
        (
            "remove_line",
            "notes.txt",
            "keep\nDROP_ME\n",
            "keep\n",
            {"text": "DROP_ME"},
        ),
        (
            "patch_json",
            "config.json",
            '{"mode":"old","preserve":true}\n',
            '{\n  "mode": "new",\n  "preserve": true\n}\n',
            {"updates": {"mode": "new"}},
        ),
    ),
)
def test_read_modify_write_replay_converges_after_the_edit_already_landed(
    tmp_path: Path,
    operation: str,
    filename: str,
    source: str,
    applied: str,
    operation_arguments: dict,
) -> None:
    workspace = tmp_path / operation
    workspace.mkdir()
    path = workspace / filename
    # The first execution landed but the action record was never finished, so
    # crash-resume replays the same arguments against the already-edited file.
    path.write_text(applied, encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    arguments = {
        "path": filename,
        **operation_arguments,
        "base_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
    }
    replay = harness.execute(TaskAction(operation, arguments), _goal(workspace))
    assert replay.success is True
    assert replay.metadata["converged_without_write"] is True
    assert path.read_text(encoding="utf-8") == applied

    # A genuinely divergent file (edit not present) still fails as stale.
    path.write_text(source + "# concurrent revision\n", encoding="utf-8")
    stale = harness.execute(TaskAction(operation, arguments), _goal(workspace))
    assert stale.success is False
    assert "stale source snapshot" in stale.error["message"]


def test_workspace_snapshot_ignores_tool_byproducts_and_records_symlinks(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "ws"
    (workspace / "src").mkdir(parents=True)
    (workspace / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    goal = _goal(workspace)
    before = harness.workspace_observation_snapshot(goal)
    assert before["cacheable"] is True

    # Running python/pytest creates caches; they must not change the snapshot.
    (workspace / "src" / "__pycache__").mkdir()
    (workspace / "src" / "__pycache__" / "app.cpython-311.pyc").write_bytes(b"x")
    (workspace / ".pytest_cache").mkdir()
    (workspace / ".pytest_cache" / "v").write_text("1", encoding="utf-8")
    after = harness.workspace_observation_snapshot(goal)
    assert after["cacheable"] is True
    assert after["digest"] == before["digest"]

    # A symlink is recorded by identity instead of making the snapshot unusable.
    (workspace / "link.txt").symlink_to("src/app.py")
    linked = harness.workspace_observation_snapshot(goal)
    assert linked["cacheable"] is True
    assert {"path": "link.txt", "type": "symlink", "target": "src/app.py"} in (
        linked["entries"]
    )
    assert linked["digest"] != before["digest"]
