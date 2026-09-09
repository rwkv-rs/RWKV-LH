from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.benchmark_verifier import run_isolated_verifier
from rwkv_lh.ultradata import audit_trajectory, compile_code_task, read_frozen_range


def code_record():
    # Small verifier fixture only; never a role training sample.
    return {"uuid": "fixture", "query": "Read two integers and print their sum.", "source": "test fixture",
            "domain": "Code", "ground_truth": {"call_type": "std", "fn_name": None,
            "inputs": ["2 3\n", "-1 1\n"], "outputs": ["5\n", "0\n"]}}


def test_private_tests_are_not_in_visible_task_and_use_existing_verifier(tmp_path):
    task, acceptance = compile_code_task(code_record())
    assert "ground_truth" not in json.dumps(task)
    assert "outputs" not in json.dumps(task)
    assert task["workspace_files"] == []
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("print(sum(map(int,input().split())))\n")
    result = run_isolated_verifier(acceptance, workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result
    assert result.metadata["workspace_mount"] == "read_only_snapshot"
    (workspace / "main.py").write_text("print(5)\n")
    assert not run_isolated_verifier(acceptance, workspace, [], {}, private_root=tmp_path / "private").passed


@pytest.mark.parametrize("mode", ["empty", "mismatched", "conflicting", "non_string", "function"])
def test_invalid_or_ambiguous_code_targets_rejected(mode):
    row = code_record()
    truth = row["ground_truth"]
    if mode == "empty":
        truth.update(inputs=[], outputs=[])
    elif mode == "mismatched":
        truth["outputs"].pop()
    elif mode == "conflicting":
        truth["inputs"][1] = truth["inputs"][0]
    elif mode == "non_string":
        truth["outputs"][0] = 5
    else:
        truth["call_type"] = "function"
    with pytest.raises(ValueError):
        compile_code_task(row)


def test_untrusted_query_is_data_not_verifier_code():
    row = code_record()
    row["query"] = "'''\nraise RuntimeError('injected')\n#"
    row["ground_truth"]["outputs"][0] = row["query"]
    _, acceptance = compile_code_task(row)
    program = acceptance["checks"][0]["program"]
    compile(program, "private verifier", "exec")
    assert hashlib.sha256(program.encode()).hexdigest() == acceptance["checks"][0]["program_sha256"]


def test_mask_and_incomplete_calls_are_not_success_labels():
    row = {"uuid": "external", "tools": [{"type": "function", "function": {"name": "read_file"}}],
           "messages": [{"role": "user", "content": "Inspect the file"},
                        {"role": "assistant", "loss": False, "tool_calls": [
                            {"function": {"name": "read_file", "arguments": '{"path":"a"}'}}]}]}
    audit = audit_trajectory(row)
    assert audit["masked_assistant_turns"] == 1
    assert audit["pending_calls"] == 1
    assert audit["terminal_kind"] == "pending_tool"
    assert audit["role_training_eligible"] is False
    assert audit["independently_verified_success"] is None


def test_unknown_tool_and_orphan_results_require_review():
    row = {"uuid": "external", "tools": [], "messages": [
        {"role": "tool", "content": "orphan"},
        {"role": "assistant", "tool_calls": [{"function": {"name": "missing", "arguments": "{}"}}]},
        {"role": "tool", "content": "ok"}, {"role": "assistant", "content": "done"}]}
    audit = audit_trajectory(row)
    assert audit["orphan_results"] == 1
    assert audit["undefined_tool_calls"] == ["missing"]
    assert audit["independently_verified_success"] is None


def test_pinned_prefix_integrity_and_partial_final_line(tmp_path):
    path = tmp_path / "rows.prefix"
    raw = b'{"uuid":"a"}\n{"uuid":"unfinished"'
    path.write_bytes(raw)
    records, metadata = read_frozen_range(path, hashlib.sha256(raw).hexdigest())
    assert [x["row"]["uuid"] for x in records] == ["a"]
    assert records[0]["line_number"] == 1
    assert metadata["trailing_bytes"] > 0
    path.write_bytes(raw + b"bad")
    with pytest.raises(ValueError, match="SHA"):
        read_frozen_range(path, hashlib.sha256(raw).hexdigest())


def test_complete_malformed_row_is_not_silently_discarded(tmp_path):
    path = tmp_path / "rows.prefix"
    raw = b'{"uuid":"a"}\n{"uuid":"b","uuid":"c"}\n'
    path.write_bytes(raw)
    records, metadata = read_frozen_range(path, hashlib.sha256(raw).hexdigest())
    assert len(records) == 2
    assert "duplicate" in records[1]["error"]
    assert metadata["invalid_rows"] == 1


@pytest.mark.parametrize("program", [
    "print(' 5')\n",
    "while True: pass\n",
    "import os; os.write(1,b'x'*2000000)\n",
])
def test_verifier_rejects_private_access_wrong_whitespace_timeout_and_output_flood(tmp_path, program):
    _, acceptance = compile_code_task(code_record(), case_timeout=0.5)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text(program)
    result = run_isolated_verifier(acceptance, workspace, [], {}, private_root=tmp_path / "private")
    assert not result.passed


def test_correct_candidate_cannot_read_private_grader_or_modify_snapshot(tmp_path):
    _, acceptance = compile_code_task(code_record())
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text(
        "from pathlib import Path\n"
        "assert not Path('/opt/verifier/programs').exists()\n"
        "assert not Path('/home/chase/GitHub/RWKV-LH').exists()\n"
        "try:\n    Path('forbidden_write').write_text('x')\n"
        "except OSError:\n    pass\n"
        "else:\n    raise AssertionError('workspace writable')\n"
        "print(sum(map(int,input().split())))\n"
    )
    result = run_isolated_verifier(acceptance, workspace, [], {}, private_root=tmp_path / "private")
    assert result.passed, result
    assert not (workspace / "forbidden_write").exists()


def test_preparation_accounts_for_all_rows_and_preserves_fixed_selection(tmp_path):
    from scripts.prepare_ultradata_pilot import prepare
    first = code_record()
    second = {**code_record(), "uuid": "second"}
    third = {**code_record(), "uuid": "third", "query": "Return the sum of input integers as a decimal number."}
    raw = b"\n".join(json.dumps(x).encode() for x in (first, second, third)) + b'\n{"truncated"'
    source = tmp_path / "source.prefix"
    source.write_bytes(raw)
    manifest = tmp_path / "fetch.json"
    manifest.write_text(json.dumps({"source_run":"test_fixture", "sources":[{
        "group":"rl_code", "repository":"test/fixture", "revision":"a"*40, "path":"source.jsonl",
        "local_path":str(source), "sha256":hashlib.sha256(raw).hexdigest()}]}))
    output = tmp_path / "bundle"
    root = Path(__file__).resolve().parents[1]
    result = prepare(manifest, root=root, output=output, code_count=2)
    assert result["complete_rows_audited"] == 3
    assert result["selection_count_satisfied"]
    assert [x["uuid"] for x in result["selected"]] == ["fixture", "third"]
    assert result["dispositions"]["near_duplicate_of_selected_task"] == 1
    assert result["ranges"][0]["trailing_bytes"] > 0
    with pytest.raises(ValueError, match="already exists"):
        prepare(manifest, root=root, output=output)
