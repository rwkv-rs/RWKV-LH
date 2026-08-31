from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from rwkv_lh.exact_tool_selector.coverage_runner import (
    AppendOnlyHashJournal,
    CoverageRunnerError,
    ExactToolCoverageRunner,
    ExecutorIdentity,
    canonical_json,
    file_sha256,
)
from rwkv_lh.model_io import JSON_CALL_STOP_SUFFIXES
from rwkv_lh.runtime.protocol import CompletionResponse
from rwkv_lh.runtime.settings import RuntimeSettings

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_exact_tool_coverage_v1"
MODEL = "rwkv7-g1i-13.3b-20260805-ctx16384"


def _rows(path: Path = DATASET / "preflight.jsonl") -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _settings(**overrides: Any) -> RuntimeSettings:
    values: dict[str, Any] = {
        "base_url": "http://127.0.0.1:18070/v1",
        "api_key": "",
        "model": MODEL,
        "backend_profile": "vllm-rwkv-native",
        "retry_attempts": 1,
        "return_token_ids": True,
        "state_profile_id": "executor-stage8",
        "state_profile_sha256": "c" * 64,
    }
    values.update(overrides)
    return RuntimeSettings(**values)


def _identity() -> ExecutorIdentity:
    return ExecutorIdentity(
        model=MODEL,
        model_sha256="a" * 64,
        engine_revision="67f0c5996c50dca0ad779da545cb491527de988f",
        engine_diff_sha256="b" * 64,
        profile_id="executor-stage8",
        profile_sha256="c" * 64,
    )


class OracleClient:
    model_name = MODEL

    def __init__(
        self,
        case: Mapping[str, Any],
        *,
        raw_override: str | None = None,
        token_ids: Sequence[int] = (11, 12, 13),
    ) -> None:
        self.case = case
        self.raw_override = raw_override
        self.token_ids = list(token_ids)
        self.calls = 0

    def text_completion(
        self,
        prompt: str,
        max_tokens: int = 768,
        stop: Sequence[str] | None = None,
    ) -> CompletionResponse:
        self.calls += 1
        assert max_tokens == 512
        assert tuple(stop or ()) == JSON_CALL_STOP_SUFFIXES
        assert prompt.startswith("System: Tools: [")
        tools_raw = prompt.removeprefix("System: Tools: ").split("\n", 1)[0]
        tools = json.loads(tools_raw)
        assert len(tools) == 1
        assert tools[0]["name"] == self.case["label"]
        assert all(
            field not in prompt
            for field in (
                "allowed_token_ids",
                "bad_words",
                "guided_decoding",
                "guided_json",
                "guided_regex",
                "logit_bias",
            )
        )
        if self.raw_override is not None:
            raw = self.raw_override
        elif self.case["label"] == "final_answer":
            facts = self.case["verifier"]["required_facts"]
            raw = canonical_json(
                {
                    "function": "final_answer",
                    "params": {"text": f"{facts[0]} is complete"},
                }
            )
        else:
            raw = canonical_json(
                {
                    "function": self.case["label"],
                    "params": self.case["executor_contract"]["expected_arguments"],
                }
            )
        return CompletionResponse(
            content=raw,
            finish_reason="stop",
            response_id=f"RESP-{self.case['case_id']}",
            model=MODEL,
            metadata={"token_ids": list(self.token_ids)},
        )


def _runner(
    tmp_path: Path,
    factory,
    *,
    settings: RuntimeSettings | None = None,
) -> ExactToolCoverageRunner:
    return ExactToolCoverageRunner(
        output_root=tmp_path / "run",
        runtime_settings=settings or _settings(),
        executor_identity=_identity(),
        fixture_manifest_sha256=file_sha256(DATASET / "manifest.json"),
        completion_client_factory=factory,
    )


def test_offline_preflight_executes_all_operations_and_preserves_raw_first(
    tmp_path: Path,
) -> None:
    rows = _rows()
    clients: dict[str, OracleClient] = {}

    def factory(case: Mapping[str, Any]) -> OracleClient:
        client = OracleClient(case)
        clients[str(case["case_id"])] = client
        return client

    runner = _runner(tmp_path, factory)
    results = [runner.run_case(row) for row in rows]

    assert len(rows) == 40
    assert all(result.accepted for result in results)
    assert len(clients) == 38
    assert all(client.calls == 1 for client in clients.values())
    records = AppendOnlyHashJournal.verify(runner.journal.path)
    raw_records = [
        record
        for record in records
        if record["event_type"] == "rwkv_raw_generation_committed"
    ]
    finished = [
        record for record in records if record["event_type"] == "attempt_finished"
    ]
    assert len(raw_records) == 38
    assert len(finished) == 40
    assert all(record["payload"]["accepted"] for record in finished)
    assert all(
        record["payload"]["raw_generation"]["postprocessed"] is False
        and record["payload"]["raw_output_modified"] is False
        and record["payload"]["raw_generation"]["raw_token_ids"] == [11, 12, 13]
        for record in raw_records
    )

    by_attempt: dict[str, list[str]] = {}
    for record in records:
        attempt_id = str(record["payload"].get("attempt_id") or "")
        if attempt_id:
            by_attempt.setdefault(attempt_id, []).append(record["event_type"])
    for result in results:
        events = by_attempt[result.attempt_id]
        if result.label == "ABSTAIN":
            assert "rwkv_raw_generation_committed" not in events
            assert "harness_execution_started" not in events
            continue
        assert events.index("rwkv_raw_generation_committed") < events.index(
            "raw_generation_parsed_derived_view"
        )
        if result.label != "final_answer":
            assert events.index("raw_generation_parsed_derived_view") < events.index(
                "harness_execution_started"
            )


@pytest.mark.parametrize(
    ("raw_factory", "token_ids", "expected_error"),
    [
        (lambda case: "not-json", (11,), "ModelIOError"),
        (
            lambda case: canonical_json(
                {"function": case["label"], "params": {"path": "wrong.txt"}}
            ),
            (11,),
            "CoverageRunnerError",
        ),
        (
            lambda case: canonical_json(
                {
                    "function": case["label"],
                    "params": case["executor_contract"]["expected_arguments"],
                }
            ),
            (),
            "CoverageRunnerError",
        ),
    ],
)
def test_rejected_attempt_keeps_exact_raw_and_never_repairs(
    tmp_path: Path,
    raw_factory,
    token_ids: Sequence[int],
    expected_error: str,
) -> None:
    case = next(row for row in _rows() if row["label"] == "read_file")
    raw = raw_factory(case)
    client = OracleClient(case, raw_override=raw, token_ids=token_ids)
    runner = _runner(tmp_path, lambda _case: client)

    result = runner.run_case(case)

    assert result.accepted is False
    assert expected_error in result.error
    records = AppendOnlyHashJournal.verify(runner.journal.path)
    raw_record = next(
        record
        for record in records
        if record["event_type"] == "rwkv_raw_generation_committed"
    )
    generation = raw_record["payload"]["raw_generation"]
    assert generation["raw_output"] == raw
    assert generation["raw_output_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert raw_record["payload"]["raw_output_modified"] is False
    assert not any(
        record["event_type"] == "harness_execution_started" for record in records
    )


def test_hash_journal_detects_modification_and_deletion(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    journal = AppendOnlyHashJournal(path)
    journal.append("first", {"value": 1})
    journal.append("second", {"value": 2})
    original = path.read_text(encoding="utf-8")

    path.write_text(original.replace('"value":1', '"value":9', 1), encoding="utf-8")
    with pytest.raises(CoverageRunnerError, match="hash chain"):
        AppendOnlyHashJournal.verify(path)

    path.write_text(original.splitlines()[1] + "\n", encoding="utf-8")
    with pytest.raises(CoverageRunnerError, match="hash chain"):
        AppendOnlyHashJournal.verify(path)


def test_runner_refuses_hidden_retries_or_missing_token_ids(tmp_path: Path) -> None:
    case = _rows()[0]
    with pytest.raises(ValueError, match="hidden generation retries"):
        _runner(
            tmp_path,
            lambda _case: OracleClient(case),
            settings=_settings(retry_attempts=2),
        )
    with pytest.raises(ValueError, match="returned token IDs"):
        _runner(
            tmp_path,
            lambda _case: OracleClient(case),
            settings=_settings(return_token_ids=False),
        )
