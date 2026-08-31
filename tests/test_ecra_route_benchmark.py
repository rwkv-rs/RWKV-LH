from __future__ import annotations

from pathlib import Path

import pytest

from rwkv_lh.retrieval import EgressProvenance
from scripts.run_ecra_route_benchmark import (
    SyntheticFrozenBackend,
    _aggregate,
    _benchmark_request,
    _byte_ngram_cosine,
    _provenance_resolver,
    _safe_relative_path,
)


def _result(
    case_id: str,
    category: str,
    expected_tool: str,
    actual_tool: str,
    *,
    policy_rejections: int = 0,
    backend_executions: int = 0,
) -> dict:
    expected_sequence = [expected_tool]
    return {
        "case_id": case_id,
        "category": category,
        "expected": {"tool_sequence": expected_sequence},
        "actual": {
            "operations": [actual_tool],
            "network_called": actual_tool in {"web_search", "connector_lookup"},
            "first_network_tool": (
                actual_tool
                if actual_tool in {"web_search", "connector_lookup"}
                else ""
            ),
            "policy_rejection_count": policy_rejections,
            "backend_execution_count": backend_executions,
            "strong_planner_concrete_operation_count": 0,
            "failure": "",
            "run_status": "completed",
        },
        "checks": {
            "first_tool_exact": expected_tool == actual_tool,
            "expected_sequence_prefix": expected_sequence == [actual_tool],
        },
    }


def test_route_benchmark_path_and_similarity_contract() -> None:
    assert _safe_relative_path("nested/file.txt") == Path("nested/file.txt")
    for unsafe in ("", "../escape", "/absolute", "nested/../../escape"):
        with pytest.raises(ValueError, match="unsafe"):
            _safe_relative_path(unsafe)
    assert _byte_ngram_cosine("same", "same") == 1.0
    assert _byte_ngram_cosine("", "") == 1.0
    assert _byte_ngram_cosine("alpha", "omega") == 0.0
    wrapped = _benchmark_request({"instruction": "find the current release"})
    assert "action routing, not factual answer quality" in wrapped
    assert "must remain source-neutral" in wrapped
    assert "RWKV alone selects the concrete source" in wrapped
    assert "mandatory completion contract is only the route outcome" in wrapped
    assert "Network/Safety Gate alone" in wrapped
    assert "never create a work node just to generate or verify it" in wrapped
    assert wrapped.endswith("Original user task: find the current release")


def test_route_benchmark_provenance_is_conservative() -> None:
    resolver = _provenance_resolver(
        {
            "workspace_files": [
                {"path": "secret.txt", "content": "token", "data_class": "secret"}
            ]
        }
    )

    labels = resolver(
        None,
        "connector_lookup",
        {"operation": "github_release", "query": "token"},
    )

    assert labels == {
        "operation": EgressProvenance.MODEL_PUBLIC_QUERY,
        "query": EgressProvenance.SECRET,
    }


def test_synthetic_backend_is_frozen_and_content_addressed() -> None:
    backend = SyntheticFrozenBackend("ECRA-ROUTE-test")
    first = backend.execute("web_search", {"query": "public", "max_results": 5})
    second = backend.execute("web_search", {"query": "public", "max_results": 5})

    assert first == second
    assert len(backend.executions) == 2
    assert first.provider_attempts == (
        {"provider": "synthetic-frozen-route-fixture", "status": "ok"},
    )
    assert first.records[0].structured_fields["route_status"] == "completed"
    assert first.records[0].structured_fields["selected_tool"] == "web_search"


def test_route_benchmark_aggregate_enforces_routing_and_privacy_gates() -> None:
    results = [
        _result("local", "local-only", "read_file", "read_file"),
        _result(
            "web",
            "public-web-required",
            "web_search",
            "web_search",
            backend_executions=1,
        ),
        _result(
            "connector",
            "structured-connector",
            "connector_lookup",
            "connector_lookup",
            backend_executions=1,
        ),
        _result("compute", "deterministic-compute", "calculator", "calculator"),
        _result(
            "mixed",
            "mixed-local-online",
            "web_search",
            "web_search",
            backend_executions=1,
        ),
        _result(
            "privacy",
            "privacy-policy-rejection",
            "web_search",
            "web_search",
            policy_rejections=1,
        ),
    ]

    aggregate = _aggregate(results, comparison=None)

    assert aggregate["metrics"]["network_decision_macro_f1"] == 1.0
    assert aggregate["metrics"]["web_connector_macro_f1"] == 1.0
    assert aggregate["metrics"]["privacy_backend_execution_count"] == 0
    assert all(
        value for value in aggregate["gates"].values() if value is not None
    )

    results[-1]["actual"]["policy_rejection_count"] = 0
    results[-1]["actual"]["backend_execution_count"] = 1
    unsafe = _aggregate(results, comparison=None)
    assert not unsafe["gates"]["privacy_backend_execution_count"]
    assert not unsafe["gates"]["privacy_policy_rejection_coverage"]

    results[0]["actual"]["run_status"] = "interrupted"
    interrupted = _aggregate(results, comparison=None)
    assert interrupted["metrics"]["failed_or_unavailable_case_count"] == 1
    assert not interrupted["gates"]["failed_or_unavailable_case_count"]
