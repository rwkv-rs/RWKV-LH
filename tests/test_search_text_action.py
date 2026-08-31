from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.schema import TaskAction
from rwkv_lh.token_budget import get_token_count


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "data/datasets/rwkv_lh_search_text_v1_cases.json"
DATASET_SHA256 = "75c86aade196d5f8df2d3ad2be97e44c6b2bae8e31dc0641b8b4bb2ec2fc001f"
DATASET = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
LOCATOR_FIELDS = ("path", "line_number", "column", "end_column", "match_text")


def materialize(workspace: Path, files: list[dict]) -> None:
    workspace.mkdir()
    for item in files:
        target = workspace / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")


def search(workspace: Path, **arguments):
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel.create_literal_goal("search fixture", str(workspace))
    return harness.execute(TaskAction("search_text", arguments), goal)


def payload(result) -> dict:
    assert result.success, result.error
    return json.loads(result.output)


def locators(matches: list[dict]) -> list[dict]:
    return [
        {field: item[field] for field in LOCATOR_FIELDS}
        for item in matches
    ]


def test_frozen_dataset_digest_and_metadata() -> None:
    assert hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest() == DATASET_SHA256
    assert DATASET["schema_version"] == "rwkv-lh.search-text-cases.v1"
    assert len(DATASET["cases"]) == 8


@pytest.mark.parametrize("case", DATASET["cases"], ids=lambda item: item["case_id"])
def test_frozen_search_cases_are_exact(tmp_path: Path, case: dict) -> None:
    workspace = tmp_path / "workspace"
    materialize(workspace, case["workspace_files"])
    arguments = {**case["arguments"], "max_results": 500, "max_tokens": 8192}

    result = search(workspace, **arguments)
    observed = payload(result)

    assert locators(observed["matches"]) == case["expected"]
    assert observed["complete"] is True
    assert observed["truncated"] is False
    assert observed["next_cursor"] == ""
    assert get_token_count(result.output) <= arguments["max_tokens"]


def test_registry_model_order_and_contract_are_authoritative() -> None:
    harness = ActionHarness(sandbox_commands=False)
    definition = harness.definition("search_text")
    schema = definition.parameters_schema()
    model_names = [
        item["name"] for item in LongHorizonModel(harness=harness).action_definitions()
    ]

    assert definition.read_only is True
    assert definition.side_effect is False
    assert definition.result_schema == "rwkv-lh.search-text-result.v1"
    assert schema["required"] == ["pattern"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["mode"]["enum"] == ["literal", "regex"]
    assert schema["properties"]["mode"]["default"] == "regex"
    assert model_names.index("search_text") == model_names.index("list_directory") + 1


def test_default_mode_uses_grep_style_regex_alternation(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    materialize(
        workspace,
        [{"path": "markers.txt", "content": "TODO first\nFIXME second\n"}],
    )

    observed = payload(search(workspace, pattern="TODO|FIXME"))

    assert observed["mode"] == "regex"
    assert [item["match_text"] for item in observed["matches"]] == [
        "TODO",
        "FIXME",
    ]


def test_pagination_union_equals_unpaged_results(tmp_path: Path) -> None:
    case = next(item for item in DATASET["cases"] if item["case_id"] == "ST-02-regex")
    workspace = tmp_path / "workspace"
    materialize(workspace, case["workspace_files"])
    base = {
        **case["arguments"],
        "max_results": 2,
        "max_tokens": 4096,
    }

    pages: list[dict] = []
    cursor = ""
    while True:
        page = payload(search(workspace, **base, start_after=cursor))
        pages.extend(locators(page["matches"]))
        if page["complete"]:
            break
        cursor = page["next_cursor"]
        assert cursor.startswith("search-v1.")

    assert pages == case["expected"]
    assert len({json.dumps(item, sort_keys=True) for item in pages}) == len(pages)


def test_cursor_is_bound_to_the_exact_search_contract(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    materialize(
        workspace,
        [{"path": "items.txt", "content": "TODO one\nTODO two\nFIXME three\n"}],
    )
    first = payload(
        search(
            workspace,
            pattern="TODO",
            max_results=1,
            max_tokens=4096,
        )
    )

    mismatched = search(
        workspace,
        pattern="FIXME",
        max_results=1,
        max_tokens=4096,
        start_after=first["next_cursor"],
    )

    assert mismatched.success is False
    assert mismatched.outcome_type == "invalid"
    assert "different search contract" in mismatched.error["message"]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"pattern": "(" , "mode": "regex"}, "regular expression is invalid"),
        ({"pattern": "TODO", "path": "../outside"}, "escapes goal workspace"),
        ({"pattern": "TODO", "mode": "wildcard"}, "must be one of"),
    ],
)
def test_invalid_search_contracts_fail_closed(
    tmp_path: Path,
    arguments: dict,
    message: str,
) -> None:
    workspace = tmp_path / "workspace"
    materialize(workspace, [{"path": "a.txt", "content": "TODO\n"}])

    result = search(workspace, **arguments)

    assert result.success is False
    assert result.outcome_type == "invalid"
    assert message in result.error["message"]


def test_binary_invalid_utf8_oversized_and_symlink_files_never_match(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "visible.txt").write_text("TODO visible\n", encoding="utf-8")
    (workspace / "binary.bin").write_bytes(b"TODO\x00hidden\n")
    (workspace / "invalid.txt").write_bytes(b"TODO\xffhidden\n")
    (workspace / "oversized.txt").write_text("TODO oversized\n", encoding="utf-8")
    outside_target = tmp_path / "target.txt"
    outside_target.write_text("TODO target\n", encoding="utf-8")
    (workspace / "linked.txt").symlink_to(outside_target)

    observed = payload(
        search(
            workspace,
            pattern="TODO",
            max_file_bytes=14,
            max_results=100,
            max_tokens=4096,
        )
    )

    assert [item["path"] for item in observed["matches"]] == ["visible.txt"]
    reasons = {item["path"]: item["reason"] for item in observed["skipped_files"]}
    assert reasons == {
        "binary.bin": "binary_nul",
        "invalid.txt": "invalid_utf8",
        "linked.txt": "symlink",
        "oversized.txt": "oversized",
    }
    assert observed["skipped_file_count"] == 4


def test_explicit_symlink_path_is_reported_without_following_it(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("TODO outside\n", encoding="utf-8")
    (workspace / "escape.txt").symlink_to(outside)

    observed = payload(search(workspace, pattern="TODO", path="escape.txt"))

    assert observed["matches"] == []
    assert observed["skipped_files"] == [
        {"path": "escape.txt", "reason": "symlink"}
    ]


def test_result_is_token_bounded_and_continuable(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "many.txt").write_text(
        "".join(f"TODO item {index} " + "x" * 100 + "\n" for index in range(30)),
        encoding="utf-8",
    )

    result = search(
        workspace,
        pattern="TODO",
        max_results=30,
        max_line_chars=80,
        max_tokens=512,
    )
    observed = payload(result)

    assert get_token_count(result.output) <= 512
    assert 0 < observed["match_count"] < 30
    assert observed["truncated"] is True
    assert observed["next_cursor"].startswith("search-v1.")

    second = payload(
        search(
            workspace,
            pattern="TODO",
            max_results=30,
            max_line_chars=80,
            max_tokens=512,
            start_after=observed["next_cursor"],
        )
    )
    assert second["matches"][0]["line_number"] > observed["matches"][-1]["line_number"]
