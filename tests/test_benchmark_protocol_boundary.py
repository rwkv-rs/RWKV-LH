from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from rwkv_lh.goal_state_protocols import executor_args_v4
from rwkv_lh.model_session import SessionSampling
from rwkv_lh.runtime.settings import RuntimeSettings
from scripts import run_rwkv_e2e_benchmark as benchmark


def test_source_manifest_never_hashes_benchmark_dataset_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "scripts/runner.py"
    source.parent.mkdir()
    source.write_text("# fixture source\n", encoding="utf-8")
    protected = tmp_path / "benchmarks/isolated/tasks.json"
    protected.parent.mkdir(parents=True)
    protected.write_text("unused fixture\n", encoding="utf-8")
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path == protected:
            raise AssertionError("source manifest opened a benchmark task resource")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(
        benchmark,
        "_git_output",
        lambda *args: "scripts/runner.py\nbenchmarks/isolated/tasks.json\n",
    )

    manifest = benchmark._source_tree_manifest(tmp_path)

    assert [record["path"] for record in manifest] == ["scripts/runner.py"]


@pytest.mark.parametrize(
    ("suite_key", "expected_keys"),
    (
        ("agentladderv1", ("agentladderv1",)),
        ("core30", ("core30",)),
        ("all", benchmark.FORMAL90_SUITE_KEYS),
        ("realagentholdoutv2", ("realagentholdoutv2",)),
    ),
)
def test_metadata_reads_only_explicitly_selected_suite_resources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suite_key: str,
    expected_keys: tuple[str, ...],
) -> None:
    repository = tmp_path / "repository"
    runner = repository / "scripts/run_fixture.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# fake benchmark runner\n", encoding="utf-8")
    vocabulary = repository / "rwkv_lh/vocabulary.txt"
    vocabulary.parent.mkdir()
    vocabulary.write_text("fixture vocabulary\n", encoding="utf-8")
    reference = repository / "data/datasets/rwkv_e2e_90_v1/codex_reference_answers.json"
    reference.parent.mkdir(parents=True)
    reference.write_text("{}\n", encoding="utf-8")
    output = repository / "run"
    output.mkdir()
    accessed_resources: list[tuple[str, str]] = []
    git_calls: list[tuple[str, ...]] = []
    reference_reads: list[Path] = []
    original_read_bytes = Path.read_bytes

    class FixtureResource:
        def __init__(self, key: str, name: str) -> None:
            self.key = key
            self.name = name

        def __str__(self) -> str:
            return str(repository / "benchmarks" / self.key / self.name)

        def read_bytes(self) -> bytes:
            if self.key not in expected_keys:
                raise AssertionError(f"unselected suite was opened: {self.key}")
            accessed_resources.append((self.key, self.name))
            return f"fixture resource {self.key}/{self.name}".encode("utf-8")

    def guarded_read_bytes(path: Path) -> bytes:
        if path == reference:
            if not set(expected_keys).intersection(benchmark.FORMAL90_SUITE_KEYS):
                raise AssertionError("non-formal suite opened E2E-90 reference answers")
            reference_reads.append(path)
        return original_read_bytes(path)

    def git_output(*args: str) -> str:
        git_calls.append(args)
        if args[0] == "ls-files":
            return "scripts/run_fixture.py\n"
        if args[0] == "rev-parse":
            return "fixture-commit\n"
        return ""

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    monkeypatch.setattr(benchmark, "__file__", str(runner))
    monkeypatch.setattr(benchmark, "VOCAB_PATH", vocabulary)
    monkeypatch.setattr(benchmark, "_git_output", git_output)
    monkeypatch.setattr(
        benchmark,
        "get_runtime_settings",
        lambda: RuntimeSettings(base_url="http://fixture.invalid", api_key="", model="fixture"),
    )
    monkeypatch.setattr(
        benchmark,
        "suite_resources",
        lambda definition: (
            FixtureResource(definition.key, "tasks.json"),
            FixtureResource(definition.key, "acceptance.json"),
        ),
    )
    monkeypatch.setattr(executor_args_v4, "INPUT_SCHEMA_VERSION", "current-executor-protocol")
    sampling = SessionSampling(temperature=0.37, top_p=0.88)
    monkeypatch.setattr(benchmark.LongHorizonModel, "_SAMPLING", sampling)
    arguments = argparse.Namespace(
        suite=suite_key,
        retry_failures_from=None,
        max_transitions=5,
        concurrency=1,
        stateful_goal=False,
        supervisor_strategy="static",
        supervisor_pending_resume_attempts=0,
    )
    tasks = [{"task_id": "fixture-case", "level": "basic"}]

    benchmark._write_run_metadata(
        output,
        arguments=arguments,
        suite_title="fixture suite",
        tasks=tasks,
        selected=tasks,
        health={},
        capabilities={},
        selector_identity={"fixture_identity": "configured"},
    )

    protocol = json.loads((output / "RUN_PROTOCOL.json").read_text(encoding="utf-8"))
    assert accessed_resources == [
        (key, filename)
        for key in expected_keys
        for filename in ("tasks.json", "acceptance.json")
    ]
    assert {resource["suite"] for resource in protocol["source_resources"]} == set(expected_keys)
    assert protocol["architecture"] == executor_args_v4.INPUT_SCHEMA_VERSION
    assert protocol["sampling"]["sampling_policy"]["temperature"] == sampling.temperature
    assert protocol["sampling"]["top_p"] == sampling.top_p
    assert bool(reference_reads) == bool(set(expected_keys).intersection(benchmark.FORMAL90_SUITE_KEYS))
    diff_calls = [call for call in git_calls if call[0] == "diff"]
    assert len(diff_calls) == 1
    assert "--" in diff_calls[0], "metadata must restrict git diff to source paths"
    assert "benchmarks" not in diff_calls[0]
    assert "data" not in diff_calls[0]
