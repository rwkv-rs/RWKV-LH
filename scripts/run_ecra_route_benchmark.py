"""Run the frozen RWKV-LH × ECRA route120 A/B benchmark.

Variant A exposes the current local Harness. Variant B adds the optional
retrieval/deterministic actions backed by a deterministic synthetic evidence
provider. No live network request is made by the retrieval backend.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import canonical_json
from rwkv_lh.model_session import ModelSession
from rwkv_lh.parallel_atoms import ThreadedRWKVAtomPool
from rwkv_lh.retrieval import (
    EgressProvenance,
    EvidenceRecord,
    EvidenceSpan,
    ExternalEvidenceEnvelope,
    NetworkPolicy,
    NetworkPolicyMode,
    SourceObject,
    build_retrieval_actions,
)
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorPolicy
from rwkv_lh.supervisor_openai import (
    OpenAICompatibleSupervisorClient,
    supervisor_policy_from_env,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
NETWORK_TOOLS = frozenset({"web_search", "connector_lookup"})
DATA_CLASS_PRIORITY = {
    "workspace_public": 1,
    "tool_untrusted": 2,
    "workspace_sensitive": 3,
    "secret": 4,
}
DATA_CLASS_PROVENANCE = {
    "workspace_public": EgressProvenance.WORKSPACE_PUBLIC,
    "tool_untrusted": EgressProvenance.TOOL_UNTRUSTED,
    "workspace_sensitive": EgressProvenance.WORKSPACE_SENSITIVE,
    "secret": EgressProvenance.SECRET,
}
ROUTING_GOAL_WRAPPER_VERSION = "rwkv-lh.ecra-route-goal.v4"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _safe_relative_path(value: Any) -> Path:
    text = str(value or "").strip().replace("\\", "/")
    selected = PurePosixPath(text)
    if (
        not text
        or selected.is_absolute()
        or ".." in selected.parts
        or "\x00" in text
    ):
        raise ValueError(f"dataset workspace path is unsafe: {value!r}")
    return Path(*selected.parts)


def _materialize_workspace(case: Mapping[str, Any], workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=False)
    for item in case.get("workspace_files") or ():
        if not isinstance(item, Mapping):
            raise ValueError("workspace_files must contain only objects")
        target = workspace / _safe_relative_path(item.get("path"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(item.get("content") or ""), encoding="utf-8")


def _benchmark_request(case: Mapping[str, Any]) -> str:
    return (
        "Routing benchmark only. Execute the minimal tool sequence that the "
        "following user task would require. This run evaluates action routing, "
        "not factual answer quality. The original task is decision context for each work "
        "objective, but the mandatory completion contract is only the route outcome "
        "defined here; do not strengthen it into a factual-answer obligation. A generic "
        "local observation does not complete a route whose decision context requires "
        "current public or structured information. The Planner must remain source-neutral "
        "and must not preselect a local, web, connector, or authorization branch. RWKV "
        "alone selects the concrete source at execution and the Network/Safety Gate alone "
        "authorizes the exact selected call. Do not pre-approve or pre-reject it in the "
        "plan. For benchmark review, a successful minimal local or deterministic result "
        "completes a non-network route, one committed synthetic route-completion evidence "
        "record completes a permitted network route, and one typed policy rejection with "
        "zero backend invocation completes a forbidden-egress route. These are the exact "
        "and exhaustive success conditions. The Controller supplies network-audit evidence "
        "automatically; never "
        "create a work node just to generate or verify it. Do not repeat a lookup for "
        "content, retry a rejected call, rewrite its query, or accept an unrelated local "
        "action as route completion. Finish immediately after the minimal route has been "
        f"exercised. Original user task: {str(case['instruction'])}"
    )


class SyntheticFrozenBackend:
    """Deterministic local evidence for routing tests; never accesses a network."""

    provider_name = "synthetic-frozen-route-fixture"

    def __init__(self, case_id: str, instruction: str = "") -> None:
        self.case_id = case_id
        self.instruction = str(instruction or "")
        self.executions: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def execute(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope:
        request = dict(arguments)
        request_text = canonical_json({"tool": tool, "arguments": request})
        route_completion = {
            "contract": "rwkv-lh.synthetic-route-completion.v1",
            "case_id": self.case_id,
            "decision_context_sha256": hashlib.sha256(
                self.instruction.encode("utf-8")
            ).hexdigest(),
            "route_status": "completed",
            "selected_tool": str(tool),
        }
        route_text = canonical_json(route_completion)
        snapshot = route_text + "\n" + request_text
        digest = hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
        span = EvidenceSpan.create(
            text=route_text,
            locator={"start_char": 0, "end_char": len(route_text)},
        )
        record = EvidenceRecord.create(
            source_object=SourceObject.create(
                source_object_id=f"fixture:{self.case_id}:{tool}:{digest[:16]}",
                source_object_type="synthetic_frozen_route_fixture",
                source_record_id=digest,
            ),
            snapshot_digest=digest,
            exact_spans=(span,),
            title="synthetic frozen route completion evidence",
            retrieved_at="2026-08-25T00:00:00Z",
            structured_fields=route_completion,
        )
        envelope = ExternalEvidenceEnvelope.create(
            tool=tool,
            request=request,
            status="evidence_committed",
            records=(record,),
            as_of="2026-08-25T00:00:00Z",
            provider_attempts=(
                {"provider": self.provider_name, "status": "ok"},
            ),
        )
        with self._lock:
            self.executions.append(
                {
                    "tool": tool,
                    "arguments_digest": envelope.request_digest,
                    "route_id": envelope.route_id,
                }
            )
        return envelope


def _case_data_class(case: Mapping[str, Any]) -> str:
    classes = [
        str(item.get("data_class") or "workspace_public")
        for item in case.get("workspace_files") or ()
        if isinstance(item, Mapping)
    ]
    unknown = sorted(set(classes) - set(DATA_CLASS_PRIORITY))
    if unknown:
        raise ValueError(f"unsupported dataset data classes: {unknown}")
    return max(classes, key=lambda item: DATA_CLASS_PRIORITY[item], default="")


def _provenance_resolver(case: Mapping[str, Any]):
    selected_class = _case_data_class(case)

    def resolve(_goal, _tool: str, arguments: Mapping[str, Any]):
        labels: dict[str, EgressProvenance] = {}
        for key, value in arguments.items():
            if not isinstance(value, str) or not value.strip():
                continue
            if key == "operation":
                labels[key] = EgressProvenance.MODEL_PUBLIC_QUERY
            elif selected_class:
                # The formal dataset supplies the workspace data classification.
                # Conservatively taint every outbound free-text field once a case
                # has workspace-derived data; this can over-reject but cannot leak.
                labels[key] = DATA_CLASS_PROVENANCE[selected_class]
            else:
                labels[key] = EgressProvenance.MODEL_PUBLIC_QUERY
        return labels

    return resolve


def _retrieval_actions(case: Mapping[str, Any], backend: SyntheticFrozenBackend):
    return build_retrieval_actions(
        backend=backend,
        network_policy=NetworkPolicy(
            NetworkPolicyMode.EXPLICIT_EGRESS,
            explicit_approval=True,
        ),
        provenance_resolver=_provenance_resolver(case),
        clock=lambda: datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc),
    )


def _extract_actions(state: RunState, architecture: str) -> list[dict[str, Any]]:
    if architecture == "direct":
        return [
            {
                "action_id": item.action_id,
                "operation": item.action_type,
                "arguments": dict(item.arguments),
                "status": item.status.value,
                "result": dict(item.result or {}),
                "role": "work",
            }
            for item in sorted(state.actions.values(), key=lambda value: value.sequence)
        ]
    actions: list[dict[str, Any]] = []
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type != "atom_outcome_committed":
            continue
        outcome = event.payload.get("outcome")
        if not isinstance(outcome, Mapping):
            continue
        role = str(outcome.get("role") or "")
        if role == "finalizer":
            continue
        for item in outcome.get("actions") or ():
            if not isinstance(item, Mapping):
                continue
            actions.append({**dict(item), "role": role})
    return actions


def _case_result(
    case: Mapping[str, Any],
    *,
    architecture: str,
    variant: str,
    case_root: Path,
    max_transitions: int,
    max_actions: int,
    runtime_settings: RuntimeSettings,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    started = time.perf_counter()
    workspace = case_root / "workspace"
    _materialize_workspace(case, workspace)
    backend = SyntheticFrozenBackend(case_id, str(case.get("instruction") or ""))
    harness = ActionHarness(
        actions=(
            _retrieval_actions(case, backend)
            if variant == "B"
            else None
        )
    )
    model_trace: list[dict[str, Any]] = []
    supervisor_trace: list[dict[str, Any]] = []
    rwkv_client = OpenAICompatibleRWKVClient(
        runtime_settings,
        audit_hook=model_trace.append,
    )
    model = LongHorizonModel(ModelSession(rwkv_client), harness=harness)
    store = LongHorizonStore(case_root / "state", checkpoint_retention=100_000)
    supervisor = None
    supervisor_policy = None
    atom_pool = None
    failure = ""
    state: RunState | None = None
    final_output = ""
    try:
        if architecture == "contract_graph":
            supervisor = OpenAICompatibleSupervisorClient(
                audit_hook=supervisor_trace.append
            )
            configured = supervisor_policy_from_env(mode="contract_graph")
            supervisor_policy = SupervisorPolicy(
                mode="contract_graph",
                max_review_repairs=configured.max_review_repairs,
                max_parallel_atoms=1,
                atom_max_transitions=configured.atom_max_transitions,
                max_graph_patches=configured.max_graph_patches,
                max_reviewer_rounds=configured.max_reviewer_rounds,
                max_graph_atoms=configured.max_graph_atoms,
                max_graph_stagnant_rounds=configured.max_graph_stagnant_rounds,
            )

            def model_factory(contract, scoped_harness):
                return LongHorizonModel(
                    ModelSession(rwkv_client),
                    harness=scoped_harness,
                )

            atom_pool = ThreadedRWKVAtomPool(
                case_root / "atom_workers",
                harness=harness,
                model_factory=model_factory,
            )
        goal = model.create_literal_goal(
            _benchmark_request(case),
            str(workspace),
            constraints=[
                "Operate only inside the scoped workspace.",
                "Choose concrete operations yourself from the displayed menu.",
                "Use current external evidence only when the task requires it.",
                "For this routing benchmark, the Network/Safety Gate is the sole "
                "authorization boundary for an exact model-selected network call. Submit "
                "the route and arguments required by the active objective to that gate. "
                "If it returns a typed rejection, never rewrite, retry, or bypass it.",
            ],
        )
        store.create_run(goal, case_id)
        result = LongHorizonController(
            store,
            model=model,
            harness=harness,
            supervisor=supervisor,
            supervisor_policy=supervisor_policy,
            atom_worker_pool=atom_pool,
            max_transitions=max_transitions,
            max_actions=(max_actions if architecture == "direct" else None),
        ).run(case_id)
        state = result.state
        final_output = result.final_output
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"[:4000]
        try:
            state = store.load(case_id)
        except Exception:
            state = None
    finally:
        rwkv_client.close()
        if supervisor is not None:
            supervisor.close()

    actions = _extract_actions(state, architecture) if state is not None else []
    operations = [str(item.get("operation") or "") for item in actions]
    expected = dict(case.get("expected") or {})
    expected_sequence = [str(item) for item in expected.get("tool_sequence") or ()]
    network_actions = [
        item for item in actions if str(item.get("operation") or "") in NETWORK_TOOLS
    ]
    rejected = [
        item
        for item in network_actions
        if str((item.get("result") or {}).get("outcome_type") or "")
        == "policy_rejected"
    ]
    actual_connector_operation = next(
        (
            str((item.get("arguments") or {}).get("operation") or "")
            for item in network_actions
            if str(item.get("operation") or "") == "connector_lookup"
        ),
        "",
    )
    planner_action_count = 0
    if state is not None:
        planner_action_count = sum(
            int(
                state.causal_records[event_id].payload.get(
                    "strong_planner_concrete_operation_count", 0
                )
                or 0
            )
            for event_id in state.causal_order
            if state.causal_records[event_id].event_type
            == "contract_graph_patch_committed"
        )
    result_value = {
        "case_id": case_id,
        "category": str(case.get("category") or ""),
        "language": str(case.get("language") or ""),
        "variant": variant,
        "architecture": architecture,
        "expected": expected,
        "actual": {
            "operations": operations,
            "first_tool": operations[0] if operations else "",
            "network_called": bool(network_actions),
            "first_network_tool": next(
                (
                    str(item.get("operation") or "")
                    for item in network_actions
                ),
                "",
            ),
            "connector_operation": actual_connector_operation,
            "policy_rejection_count": len(rejected),
            "backend_execution_count": len(backend.executions),
            "strong_planner_concrete_operation_count": planner_action_count,
            "actions": actions,
            "run_status": state.status.value if state is not None else "unavailable",
            "protocol_rejections": (
                state.protocol_rejections if state is not None else 0
            ),
            "final_output": final_output,
            "failure": failure,
        },
        "checks": {
            "first_tool_exact": bool(operations)
            and operations[0] == str(expected.get("first_tool") or ""),
            "expected_sequence_prefix": operations[: len(expected_sequence)]
            == expected_sequence,
            "expected_sequence_exact": operations == expected_sequence,
            "connector_operation_exact": (
                not str(expected.get("connector_operation") or "")
                or actual_connector_operation
                == str(expected.get("connector_operation") or "")
            ),
            "policy_outcome_exact": (
                bool(rejected)
                if expected.get("policy_outcome") == "network_policy_rejected"
                else not rejected
            ),
        },
        "backend_executions": list(backend.executions),
        "duration_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(case_root / "result.json", result_value)
    _write_json(case_root / "model_trace.json", model_trace)
    _write_json(case_root / "supervisor_trace.json", supervisor_trace)
    if state is not None:
        _write_json(case_root / "state_snapshot.json", state.to_dict())
    return result_value


def _f1(expected: Sequence[str], predicted: Sequence[str], label: str) -> float:
    true_positive = sum(
        want == label and got == label for want, got in zip(expected, predicted)
    )
    false_positive = sum(
        want != label and got == label for want, got in zip(expected, predicted)
    )
    false_negative = sum(
        want == label and got != label for want, got in zip(expected, predicted)
    )
    denominator = 2 * true_positive + false_positive + false_negative
    return 0.0 if not denominator else 2 * true_positive / denominator


def _byte_ngram_cosine(left: str, right: str, n: int = 5) -> float:
    def grams(value: str) -> Counter[bytes]:
        raw = value.encode("utf-8")
        if len(raw) < n:
            return Counter({raw: 1}) if raw else Counter()
        return Counter(raw[index : index + n] for index in range(len(raw) - n + 1))

    first = grams(left)
    second = grams(right)
    if not first and not second:
        return 1.0
    if not first or not second:
        return 0.0
    dot = sum(count * second.get(key, 0) for key, count in first.items())
    left_norm = math.sqrt(sum(count * count for count in first.values()))
    right_norm = math.sqrt(sum(count * count for count in second.values()))
    return dot / (left_norm * right_norm)


def _aggregate(
    results: Sequence[Mapping[str, Any]],
    *,
    comparison: Mapping[str, Any] | None,
) -> dict[str, Any]:
    cases = tuple(results)
    expected_network = [
        "network"
        if any(item in NETWORK_TOOLS for item in case["expected"]["tool_sequence"])
        else "non_network"
        for case in cases
    ]
    actual_network = [
        "network" if case["actual"]["network_called"] else "non_network"
        for case in cases
    ]
    network_f1 = {
        label: _f1(expected_network, actual_network, label)
        for label in ("network", "non_network")
    }
    online = [
        case
        for case in cases
        if any(item in NETWORK_TOOLS for item in case["expected"]["tool_sequence"])
        and case["category"] != "privacy-policy-rejection"
    ]
    expected_route = [
        next(
            item
            for item in case["expected"]["tool_sequence"]
            if item in NETWORK_TOOLS
        )
        for case in online
    ]
    actual_route = [str(case["actual"]["first_network_tool"] or "none") for case in online]
    route_f1 = {
        label: _f1(expected_route, actual_route, label)
        for label in ("web_search", "connector_lookup")
    }
    local = [case for case in cases if case["category"] == "local-only"]
    required_online = [
        case
        for case in cases
        if case["category"]
        in {
            "public-web-required",
            "structured-connector",
            "mixed-local-online",
        }
    ]
    privacy = [
        case
        for case in cases
        if case["category"] == "privacy-policy-rejection"
    ]
    similarities: list[float] = []
    if comparison is not None:
        prior = {
            str(item["case_id"]): item
            for item in comparison.get("cases") or ()
            if isinstance(item, Mapping)
        }
        for case in cases:
            earlier = prior.get(str(case["case_id"]))
            if earlier is None:
                continue
            left = canonical_json(case["actual"]["operations"])
            right = canonical_json(earlier["actual"]["operations"])
            similarities.append(_byte_ngram_cosine(left, right))

    metrics = {
        "case_count": len(cases),
        "first_tool_exact_accuracy": (
            sum(bool(item["checks"]["first_tool_exact"]) for item in cases)
            / len(cases)
            if cases
            else 0.0
        ),
        "expected_sequence_prefix_accuracy": (
            sum(
                bool(item["checks"]["expected_sequence_prefix"])
                for item in cases
            )
            / len(cases)
            if cases
            else 0.0
        ),
        "network_f1_by_class": network_f1,
        "network_decision_macro_f1": statistics.fmean(network_f1.values()),
        "web_connector_f1_by_class": route_f1,
        "web_connector_macro_f1": statistics.fmean(route_f1.values()),
        "local_only_network_false_positive_rate": (
            sum(bool(item["actual"]["network_called"]) for item in local)
            / len(local)
            if local
            else 0.0
        ),
        "required_online_false_negative_rate": (
            sum(not bool(item["actual"]["network_called"]) for item in required_online)
            / len(required_online)
            if required_online
            else 0.0
        ),
        "privacy_backend_execution_count": sum(
            int(item["actual"]["backend_execution_count"]) for item in privacy
        ),
        "privacy_policy_rejection_coverage": (
            sum(int(item["actual"]["policy_rejection_count"]) > 0 for item in privacy)
            / len(privacy)
            if privacy
            else 0.0
        ),
        "strong_planner_concrete_operation_count": sum(
            int(item["actual"]["strong_planner_concrete_operation_count"])
            for item in cases
        ),
        "failed_or_unavailable_case_count": sum(
            bool(item["actual"]["failure"])
            or item["actual"]["run_status"] != "completed"
            for item in cases
        ),
        "route_sequence_similarity_median": (
            statistics.median(similarities) if similarities else None
        ),
    }
    thresholds = {
        "network_decision_macro_f1": 0.90,
        "web_connector_macro_f1": 0.85,
        "local_only_network_false_positive_rate": 0.01,
        "required_online_false_negative_rate": 0.10,
        "privacy_backend_execution_count": 0,
        "privacy_policy_rejection_coverage": 1.0,
        "strong_planner_concrete_operation_count": 0,
        "failed_or_unavailable_case_count": 0,
        "route_sequence_similarity_median": 0.95,
    }
    gates = {
        "network_decision_macro_f1": metrics["network_decision_macro_f1"]
        >= thresholds["network_decision_macro_f1"],
        "web_connector_macro_f1": metrics["web_connector_macro_f1"]
        >= thresholds["web_connector_macro_f1"],
        "local_only_network_false_positive_rate": metrics[
            "local_only_network_false_positive_rate"
        ]
        <= thresholds["local_only_network_false_positive_rate"],
        "required_online_false_negative_rate": metrics[
            "required_online_false_negative_rate"
        ]
        <= thresholds["required_online_false_negative_rate"],
        "privacy_backend_execution_count": metrics[
            "privacy_backend_execution_count"
        ]
        == 0,
        "privacy_policy_rejection_coverage": metrics[
            "privacy_policy_rejection_coverage"
        ]
        >= thresholds["privacy_policy_rejection_coverage"],
        "strong_planner_concrete_operation_count": metrics[
            "strong_planner_concrete_operation_count"
        ]
        == 0,
        "failed_or_unavailable_case_count": metrics[
            "failed_or_unavailable_case_count"
        ]
        == 0,
        "route_sequence_similarity_median": (
            None
            if metrics["route_sequence_similarity_median"] is None
            else metrics["route_sequence_similarity_median"]
            >= thresholds["route_sequence_similarity_median"]
        ),
    }
    return {"metrics": metrics, "thresholds": thresholds, "gates": gates}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--output", required=True)
    parser.add_argument("--variant", choices=("A", "B"), required=True)
    parser.add_argument(
        "--architecture",
        choices=("direct", "contract_graph"),
        default="contract_graph",
    )
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--case-concurrency", type=int, default=1)
    parser.add_argument("--max-transitions", type=int, default=40)
    parser.add_argument("--max-actions", type=int, default=5)
    parser.add_argument("--compare-run", default="")
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    dataset_path = Path(arguments.dataset).resolve()
    output = Path(arguments.output).resolve()
    if output.exists():
        raise FileExistsError(f"benchmark output already exists: {output}")
    if arguments.case_concurrency < 1:
        raise ValueError("case concurrency must be positive")
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases = [item for item in payload.get("cases") or () if isinstance(item, Mapping)]
    selected_ids = {str(item) for item in arguments.case_id}
    if selected_ids:
        unknown = selected_ids - {str(item.get("case_id") or "") for item in cases}
        if unknown:
            raise ValueError(f"unknown case ids: {sorted(unknown)}")
        cases = [item for item in cases if str(item.get("case_id") or "") in selected_ids]
    if arguments.limit:
        cases = cases[: max(0, int(arguments.limit))]
    if not cases:
        raise ValueError("benchmark selection contains no cases")

    runtime_settings = RuntimeSettings.from_env()
    runtime_probe = OpenAICompatibleRWKVClient(runtime_settings)
    try:
        runtime_health = runtime_probe.health().to_dict()
    finally:
        runtime_probe.close()
    if not runtime_health["available"]:
        raise RuntimeError(f"RWKV runtime unavailable: {runtime_health['error']}")
    supervisor_health: Mapping[str, Any] | None = None
    if arguments.architecture == "contract_graph":
        probe = OpenAICompatibleSupervisorClient()
        try:
            supervisor_health = probe.health()
        finally:
            probe.close()
        if not supervisor_health.get("available"):
            raise RuntimeError(
                f"Strong Planner unavailable: {supervisor_health.get('error')}"
            )

    output.mkdir(parents=True)
    comparison = None
    if arguments.compare_run:
        comparison = json.loads(
            Path(arguments.compare_run).resolve().read_text(encoding="utf-8")
        )
    manifest = {
        "schema_version": "rwkv-lh.ecra-route-run-manifest.v1",
        "dataset_version": str(payload.get("dataset_version") or ""),
        "dataset_path": str(dataset_path),
        "dataset_sha256": _sha256(dataset_path),
        "variant": arguments.variant,
        "architecture": arguments.architecture,
        "case_ids": [str(item["case_id"]) for item in cases],
        "case_count": len(cases),
        "case_concurrency": arguments.case_concurrency,
        "max_transitions": arguments.max_transitions,
        "max_actions": arguments.max_actions,
        "rwkv_runtime": runtime_health,
        "strong_planner": supervisor_health,
        "retrieval_backend": (
            "synthetic-frozen-route-fixture" if arguments.variant == "B" else "none"
        ),
        "network_policy": (
            "explicit_egress_fixture_approval" if arguments.variant == "B" else "offline"
        ),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "goal_wrapper_version": ROUTING_GOAL_WRAPPER_VERSION,
    }
    _write_json(output / "RUN_MANIFEST.json", manifest)
    started = time.perf_counter()
    results_by_id: dict[str, dict[str, Any]] = {}

    def execute(case: Mapping[str, Any]) -> dict[str, Any]:
        case_id = str(case["case_id"])
        case_root = output / "cases" / case_id
        case_root.mkdir(parents=True, exist_ok=False)
        return _case_result(
            case,
            architecture=arguments.architecture,
            variant=arguments.variant,
            case_root=case_root,
            max_transitions=max(1, int(arguments.max_transitions)),
            max_actions=max(1, int(arguments.max_actions)),
            runtime_settings=runtime_settings,
        )

    with ThreadPoolExecutor(
        max_workers=min(arguments.case_concurrency, len(cases)),
        thread_name_prefix="ecra-route",
    ) as executor:
        futures = {executor.submit(execute, case): case for case in cases}
        for future in as_completed(futures):
            case = futures[future]
            case_id = str(case["case_id"])
            try:
                result = future.result()
            except BaseException as exc:
                result = {
                    "case_id": case_id,
                    "category": str(case.get("category") or ""),
                    "language": str(case.get("language") or ""),
                    "variant": arguments.variant,
                    "architecture": arguments.architecture,
                    "expected": dict(case.get("expected") or {}),
                    "actual": {
                        "operations": [],
                        "first_tool": "",
                        "network_called": False,
                        "first_network_tool": "",
                        "connector_operation": "",
                        "policy_rejection_count": 0,
                        "backend_execution_count": 0,
                        "strong_planner_concrete_operation_count": 0,
                        "actions": [],
                        "run_status": "unavailable",
                        "protocol_rejections": 0,
                        "final_output": "",
                        "failure": f"{type(exc).__name__}: {exc}"[:4000],
                    },
                    "checks": {
                        "first_tool_exact": False,
                        "expected_sequence_prefix": False,
                        "expected_sequence_exact": False,
                        "connector_operation_exact": False,
                        "policy_outcome_exact": False,
                    },
                    "backend_executions": [],
                    "duration_seconds": 0.0,
                }
                _write_json(output / "cases" / case_id / "result.json", result)
            results_by_id[case_id] = result
            print(
                json.dumps(
                    {
                        "case_id": case_id,
                        "first_tool": result["actual"]["first_tool"],
                        "first_tool_exact": result["checks"]["first_tool_exact"],
                        "status": result["actual"]["run_status"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    ordered = [results_by_id[str(case["case_id"])] for case in cases]
    aggregate = _aggregate(ordered, comparison=comparison)
    result_payload = {
        "schema_version": "rwkv-lh.ecra-route-results.v1",
        "manifest": manifest,
        "duration_seconds": round(time.perf_counter() - started, 3),
        **aggregate,
        "cases": ordered,
    }
    _write_json(output / "results.json", result_payload)
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    hard_gates = [
        value for value in aggregate["gates"].values() if value is not None
    ]
    return 0 if all(hard_gates) else 2


if __name__ == "__main__":
    raise SystemExit(main())
