from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from rwkv_lh.goal_state_protocols import executor_args_v4
from rwkv_lh.benchmark_verifier import CheckResult, IsolatedVerifierResult
from rwkv_lh.controller import ControllerResult
from rwkv_lh.model_session import SessionSampling
from rwkv_lh.retrieval.policy import NetworkPolicyMode
from rwkv_lh.runtime.executor_profiles import ExecutorProfileBinding, EXECUTOR_PROFILE_ROUTING_DISABLED
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import CausalEventDraft, RunStatus
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
        supervisor_batch_failure_policy="continue_model_failures",
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
    assert protocol["supervisor_batch_failure_policy"] == "continue_model_failures"
    assert bool(reference_reads) == bool(set(expected_keys).intersection(benchmark.FORMAL90_SUITE_KEYS))
    diff_calls = [call for call in git_calls if call[0] == "diff"]
    assert len(diff_calls) == 1
    assert "--" in diff_calls[0], "metadata must restrict git diff to source paths"
    assert "benchmarks" not in diff_calls[0]
    assert "data" not in diff_calls[0]


@pytest.mark.parametrize("suite_key", (*benchmark.FORMAL90_SUITE_KEYS, "agentv1", "agentladderv1", "realprojectdevv1"))
def test_suite_path_identity_preserves_existing_public_resource_strings(suite_key: str) -> None:
    definition = benchmark.SUITES[suite_key]
    # Only these explicitly public packages are loaded; no sealed resource is read.
    expected = tuple(str(item) for item in benchmark.suite_resources(definition))
    assert tuple(str(item) for item in benchmark.suite_resource_paths(definition)) == expected


def test_importing_runner_does_not_import_default_or_optional_suite_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_resource_import(package: str):
        raise AssertionError(f"unselected resource import: {package}")

    monkeypatch.setattr(benchmark.importlib.resources, "files", forbidden_resource_import)
    name = "fixture_benchmark_without_suite_resources"
    spec = importlib.util.spec_from_file_location(name, benchmark.__file__)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    assert str(module.ACCEPTANCE_RESOURCE) == str(benchmark.ACCEPTANCE_RESOURCE)
    assert str(module.TASKS_RESOURCE) == str(benchmark.TASKS_RESOURCE)


@pytest.mark.parametrize("leaked_suite", (None, "core30", "fixture_optional_missing"))
def test_run_case_exports_with_missing_optional_suite_and_retains_global_leak_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, leaked_suite: str | None,
) -> None:
    """Exercise real case finalization with explicit mock model/verifier results."""
    optional = benchmark.SuiteDefinition(
        key="fixture_optional_missing", title="Optional fixture", package="benchmarks.rwkv_e2e.fixture_optional_missing",
        tasks_schema="fixture.tasks", acceptance_schema="fixture.acceptance", expected_count=1,
        level_counts={"project": 1},
    )
    monkeypatch.setattr(benchmark, "SUITES", {**benchmark.SUITES, optional.key: optional})
    resource_imports = []

    def unavailable_resource(package: str):
        resource_imports.append(package)
        raise ModuleNotFoundError(f"optional suite unavailable: {package}")

    monkeypatch.setattr(benchmark.importlib.resources, "files", unavailable_resource)
    text = "ordinary model trace with no private path"
    if leaked_suite is not None:
        definition = benchmark.SUITES[leaked_suite]
        text = str(Path(benchmark.__file__).resolve().parents[1].joinpath(*definition.package.split("."), "acceptance.json"))

    def session_factory(*, client, settings, audit_hook):
        audit_hook({"type": "fixture_model_observation", "text": text})
        return object()

    literal_goal = benchmark.LongHorizonModel.create_literal_goal

    class FixtureModel:
        create_literal_goal = staticmethod(literal_goal)

        def __init__(self, *args, **kwargs):
            pass

    def completed_controller(store, model, harness, task_id, **kwargs):
        state = store.load(task_id)
        state.status = RunStatus.COMPLETED
        state = store.save(state, causal_event=CausalEventDraft.create(
            "run_completed", {"reason": "explicit_mock_completion"}, subject_id=task_id,
        ))
        return ControllerResult(state=state, final_output="fixture answer", transitions=0)

    settings = RuntimeSettings(base_url="http://fixture.invalid", api_key="", model="fixture")
    binding = ExecutorProfileBinding(settings, EXECUTOR_PROFILE_ROUTING_DISABLED, NetworkPolicyMode.OFFLINE, "executor")
    monkeypatch.setattr(benchmark, "executor_profile_binding_for_run", lambda state: binding)
    monkeypatch.setattr(benchmark, "OpenAICompatibleRWKVClient", lambda settings: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(benchmark, "create_model_session", session_factory)
    monkeypatch.setattr(benchmark, "LongHorizonModel", FixtureModel)
    monkeypatch.setattr(benchmark, "_run_controller", completed_controller)
    monkeypatch.setattr(benchmark, "_agent_process_tree_closed", lambda workspace: True)
    monkeypatch.setattr(benchmark, "final_output_non_intervention_evidence", lambda *args, **kwargs: ("fixture answer", "fixture answer", True))
    monkeypatch.setattr(benchmark, "run_isolated_verifier", lambda *args, **kwargs: IsolatedVerifierResult(
        checks=(CheckResult("fixture", True, {}),), metadata={"backend": "bubblewrap"},
    ))
    result = benchmark.run_case(
        {"task_id": "OPTIONAL-PACKAGE-FIXTURE", "level": "project", "user_request": "Exercise case finalization only.", "workspace_files": {}},
        {"checks": []}, tmp_path, max_transitions=1,
    )
    audit = json.loads((tmp_path / result["audit"]).read_text())
    assert resource_imports == []
    assert result["agent_completed"] is True
    assert result["external_passed"] is True
    assert result["failure"] == ""
    assert result["passed"] is (leaked_suite is None)
    assert audit["anti_cheating"]["acceptance_resource_path_absent_from_model_trace"] is (leaked_suite is None)
    assert audit["model_trace"][0]["text"] == text
    assert (tmp_path / "cases/OPTIONAL-PACKAGE-FIXTURE/model_trace.json").is_file()
