"""Batch control tests use derived case results, never model protocol inputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from rwkv_lh.runtime.settings import RuntimeSettings
from scripts import run_rwkv_e2e_benchmark as benchmark


def failure(category="protocol", status=200, error="SupervisorProtocolError: native completion did not finish: 'length'", retryable=False):
    return dict(failed=True, category=category, http_status=status, error=error,
                retryable=retryable, phase="goal_plan", unresolved_request_count=1)


@pytest.mark.parametrize("policy", ("stop_non_retryable", "continue_model_failures"))
def test_batch_failure_policy_cli_is_explicit(monkeypatch, policy):
    monkeypatch.setattr(sys, "argv", ["benchmark", "--supervisor-batch-failure-policy", policy])
    assert benchmark.parse_args().supervisor_batch_failure_policy == policy


def test_batch_failure_policy_default_preserves_stop(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["benchmark"])
    assert benchmark.parse_args().supervisor_batch_failure_policy == "stop_non_retryable"


@pytest.mark.parametrize(("summary", "aborts"), [
    (failure(), False),
    (failure(error="SupervisorProtocolError: response is not JSON"), False),
    (failure("semantic_validation", 0, "ValueError: invalid plan dependency"), False),
    (failure("semantic_validation", 0, "TypeError: invalid plan fields"), False),
    (failure("authorization", 401, "SupervisorTransportError: authorization"), True),
    (failure("authorization", 403, "SupervisorTransportError: authorization", True), True),
    (failure("endpoint", 404, "SupervisorTransportError: absent endpoint"), True),
    (failure("request", 400, "SupervisorTransportError: invalid request"), True),
    (failure("model_identity", 0, "ValueError: identity mismatch", True), True),
    (failure("configuration", 0, "ValueError: configuration mismatch", True), True),
    (failure("protocol", 0, "SupervisorProtocolError: no HTTP response"), True),
    (failure("protocol", 200, "RuntimeError: unexpected programming failure"), True),
    (failure("controller_supervisor_boundary", 0, "RuntimeError: unknown boundary"), True),
    (failure("unknown", 200, "unknown failure"), True),
    (failure("upstream", 503, "SupervisorTransportError: upstream", True), False),
    (failure("connection", 0, "SupervisorTransportError: connection", True), False),
])
def test_continue_policy_has_a_conservative_category_boundary(summary, aborts):
    original = dict(summary)
    assert benchmark.should_abort_supervisor_batch(summary, "continue_model_failures") is aborts
    assert summary == original


@pytest.mark.parametrize("concurrency", (1, 2))
@pytest.mark.parametrize(("policy", "summary", "expected_count", "expected_exit"), [
    ("stop_non_retryable", failure(), 1, 3),
    ("continue_model_failures", failure(), 3, 2),
    ("continue_model_failures", failure("semantic_validation", 0, "ValueError: invalid plan"), 3, 2),
    ("continue_model_failures", failure("authorization", 401, "SupervisorTransportError: authorization"), 1, 3),
    ("continue_model_failures", failure("request", 400, "SupervisorTransportError: invalid request"), 1, 3),
    ("continue_model_failures", failure("unknown", 0, "unknown failure"), 1, 3),
])
def test_main_preserves_each_case_failure_and_continues_only_by_explicit_policy(
    tmp_path: Path, monkeypatch, concurrency, policy, summary, expected_count, expected_exit,
):
    output = tmp_path / "run"
    args = argparse.Namespace(
        output=str(output), suite="core30", supervisor="openai", supervisor_strategy="static",
        stateful_goal=False, independent_selector=False, concurrency=concurrency,
        supervisor_pending_resume_attempts=0, supervisor_batch_failure_policy=policy,
        tool_disclosure_mode=None, retry_failures_from="", case=[], max_cases=None,
        max_transitions=200, list=False, validate_only=False,
    )
    tasks = [{"task_id": f"FIXTURE-{index}", "level": "basic", "user_request": "Batch-control fixture"} for index in range(3)]
    monkeypatch.setattr(benchmark, "parse_args", lambda: args)
    monkeypatch.setattr(benchmark, "load_suite", lambda suite: (tasks, {task["task_id"]: {} for task in tasks}))
    settings = RuntimeSettings(base_url="http://fixture.invalid", api_key="", model="fixture")
    monkeypatch.setattr(benchmark, "get_runtime_settings", lambda: settings)
    health = SimpleNamespace(available=True, models=("fixture",), to_dict=lambda: {}, error="")
    monkeypatch.setattr(benchmark, "OpenAICompatibleRWKVClient", lambda: SimpleNamespace(
        health=lambda: health, capabilities=lambda: SimpleNamespace(to_dict=lambda: {}), close=lambda: None))
    supervisor = SimpleNamespace(model="fixture", public_dict=lambda: {})
    monkeypatch.setattr(benchmark.SupervisorAPISettings, "from_env", lambda: supervisor)
    monkeypatch.setattr(benchmark, "OpenAICompatibleSupervisorClient", lambda settings: SimpleNamespace(
        health=lambda: {"available": True, "model_present": True}, close=lambda: None))
    monkeypatch.setattr(benchmark, "_write_run_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr(benchmark, "_write_report", lambda *args, **kwargs: None)
    calls = []

    def run_case(task, acceptance, destination, **kwargs):
        calls.append(task["task_id"])
        assert kwargs["supervisor_pending_resume_attempts"] == 0
        assert kwargs["max_transitions"] == 200
        return {"task_id": task["task_id"], "passed": False, "agent_completed": False,
                "external_passed": False, "status": "blocked", "supervisor_failure": dict(summary)}

    class DeferredFuture:
        def __init__(self, function, args, kwargs):
            self.function, self.args, self.kwargs = function, args, kwargs
            self.was_cancelled = False

        def cancel(self):
            self.was_cancelled = True
            return True

        def cancelled(self):
            return self.was_cancelled

        def result(self):
            return self.function(*self.args, **self.kwargs)

    class DeferredPool:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def submit(self, function, *args, **kwargs):
            return DeferredFuture(function, args, kwargs)

    monkeypatch.setattr(benchmark, "run_case", run_case)
    monkeypatch.setattr(benchmark, "ProcessPoolExecutor", DeferredPool)
    monkeypatch.setattr(benchmark, "as_completed", lambda futures: iter(futures))
    assert benchmark.main() == expected_exit
    assert calls == [task["task_id"] for task in tasks[:expected_count]]
    assert len(calls) == len(set(calls)), "no automatic retry of a failed case"
    results = json.loads((output / "results.json").read_text())["results"]
    assert len(results) == expected_count
    assert all(row["passed"] is False and row["supervisor_failure"] == summary for row in results)
    assert (output / "RUN_ABORTED.json").exists() is (expected_exit == 3)
    if expected_exit == 3:
        abort = json.loads((output / "RUN_ABORTED.json").read_text())
        assert abort["failure"]["category"] == summary["category"]
        assert abort["supervisor_batch_failure_policy"] == policy
    retry_manifest = json.loads((output / "retry_manifest.json").read_text())
    assert retry_manifest["selected_case_count"] == 3
    assert retry_manifest["completed_case_count"] == expected_count
