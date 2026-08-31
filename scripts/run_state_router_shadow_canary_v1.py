"""Run the preregistered Stage-1 Shadow canary through the real product Controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.model import LongHorizonModel
from rwkv_lh.product_runtime import build_product_controller
from rwkv_lh.retrieval import NetworkPolicyMode, RetrievalRuntimeConfig, runtime_policy_document
from rwkv_lh.runtime import OpenAICompatibleRWKVClient, get_runtime_settings
from rwkv_lh.state_router.protocol import canonical_digest
from rwkv_lh.state_router.shadow import read_shadow_records, shadow_log_path
from rwkv_lh.store import LongHorizonStore


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_state_router_shadow_canary_v1"
DEFAULT_OUTPUT = (
    ROOT / "data/experiments/STATE_ROUTER_STAGE1_SHADOW_CANARY_V1_20260827"
)
PROTOCOL_ROOT = ROOT / "data/experiments/STATE_ROUTER_STAGE1_SHADOW_V1_20260827"
CODE_MANIFEST = PROTOCOL_ROOT / "FROZEN_CODE_MANIFEST.json"
EXPECTED_CASES_SHA256 = "cf650d5c2af0011012c0d88780efc597c90ff392542e9b313d99408911426d53"
EXPECTED_ENGINE_REVISION = "67f0c5996c50dca0ad779da545cb491527de988f"
ENGINE_ROOT = Path("/home/chase/GitHub/vllm-rwkv")
SCHEMA_VERSION = "rwkv-lh.state-router-shadow-canary-results.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def append_jsonl(path: Path, event: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(event), ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def verified_code_manifest() -> dict[str, Any]:
    value = json.loads(CODE_MANIFEST.read_text(encoding="utf-8"))
    if value.get("schema_version") != "rwkv-lh.frozen-code-manifest.v1":
        raise RuntimeError("unsupported frozen implementation manifest")
    for item in value.get("files") or []:
        path = ROOT / str(item["path"])
        if not path.is_file() or file_sha256(path) != item["sha256"]:
            raise RuntimeError(f"frozen implementation drift: {path}")
    return value


def verified_cases() -> list[dict[str, Any]]:
    cases_path = DATASET / "cases.json"
    if file_sha256(cases_path) != EXPECTED_CASES_SHA256:
        raise RuntimeError("preregistered Shadow canary dataset drift")
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("sample_count") != 8:
        raise RuntimeError("Shadow canary manifest sample count drift")
    values = json.loads(cases_path.read_text(encoding="utf-8"))
    if not isinstance(values, list) or len(values) != 8:
        raise RuntimeError("Shadow canary must contain exactly eight cases")
    return [dict(item) for item in values]


def verified_engine() -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ENGINE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--short"],
        cwd=ENGINE_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != EXPECTED_ENGINE_REVISION or dirty:
        raise RuntimeError("local vllm-rwkv revision/cleanliness drift")
    return {
        "root": str(ENGINE_ROOT),
        "revision": revision,
        "clean": True,
    }


def _close_controller(controller: Any) -> None:
    base = getattr(controller, "_controller", controller)
    session = getattr(getattr(base, "model", None), "session", None)
    client = getattr(session, "client", None)
    close = getattr(client, "close", None)
    if callable(close):
        close()


def run_case(case: Mapping[str, Any], output: Path, max_transitions: int) -> dict[str, Any]:
    case_id = str(case["case_id"])
    case_root = output / "runs" / case_id
    workspace = case_root / "workspace"
    workspace.mkdir(parents=True)
    for seed in case.get("seed_files") or []:
        relative = Path(str(seed["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"invalid canary seed path: {relative}")
        target = (workspace / relative).resolve()
        target.relative_to(workspace.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(seed["content"]), encoding="utf-8")

    model_trace = case_root / "model_trace.jsonl"
    store = LongHorizonStore(case_root / "state", checkpoint_retention=100_000)
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode(str(case["network_policy"])))
    goal = LongHorizonModel.create_literal_goal(
        str(case["request"]),
        str(workspace),
        constraints=[str(item) for item in case.get("constraints") or []],
        runtime_policy=runtime_policy_document(config, state_router_mode="shadow"),
    )
    state = store.create_run(goal, case_id)
    controller = build_product_controller(
        store,
        state,
        state_root=case_root,
        max_transitions=max_transitions,
        model_audit_hook=lambda event: append_jsonl(model_trace, event),
    )
    started = time.perf_counter()
    failure = ""
    result = None
    try:
        result = controller.run(case_id)
        state = result.state
    except BaseException as exc:
        failure = f"{type(exc).__name__}: {exc}"[:4000]
        try:
            state = store.load(case_id)
        except Exception:
            pass
    finally:
        _close_controller(controller)

    shadow = read_shadow_records(case_root, case_id, limit=1000)["events"]
    predictions = [
        item
        for item in shadow
        if item.get("event_type") in {"prediction", "prediction_error"}
    ]
    outcomes = [item for item in shadow if item.get("event_type") == "outcome"]
    prediction = predictions[0] if len(predictions) == 1 else {}
    outcome = outcomes[0] if len(outcomes) == 1 else {}
    router_output = dict(prediction.get("router_output") or {})
    behavior = dict(outcome.get("observed_main_behavior") or {})
    expected_route = str(case["expected_route_family"])
    expected_network = str(case["expected_network_recommendation"])
    causal_types = [state.causal_records[item].event_type for item in state.causal_order]
    records_valid = True
    for record in shadow:
        recorded_digest = str(record.get("record_digest") or "")
        unhashed = dict(record)
        unhashed.pop("record_digest", None)
        records_valid = records_valid and recorded_digest == canonical_digest(unhashed)
    return {
        "case_id": case_id,
        "purpose": case["purpose"],
        "expected": {
            "route_family": expected_route,
            "network_recommendation": expected_network,
        },
        "router_output": router_output,
        "observed_main_behavior": behavior,
        "reference_is_ground_truth": False,
        "route_correct": router_output.get("route_family") == expected_route,
        "network_correct": router_output.get("network_recommendation") == expected_network,
        "ood_abstain_correct": (
            expected_route != "abstain" or router_output.get("route_family") == "abstain"
        ),
        "prediction_event_count": len(predictions),
        "outcome_event_count": len(outcomes),
        "prediction_error": dict(prediction.get("error") or {}),
        "paired": (
            len(predictions) == 1
            and len(outcomes) == 1
            and prediction.get("invocation_id") == outcome.get("invocation_id")
        ),
        "tool_menu_unchanged": bool(
            (outcome.get("comparison") or {}).get("tool_menu_unchanged", False)
        ),
        "all_influence_false": all(
            item.get("shadow_only") is True
            and isinstance(item.get("influence"), Mapping)
            and all(value is False for value in item["influence"].values())
            for item in shadow
        ),
        "record_digests_valid": records_valid and bool(shadow),
        "shadow_records_run_id_match": all(
            item.get("run_id") == case_id for item in shadow
        ),
        "shadow_causal_event_count": sum(
            "state_router" in event_type or "shadow" in event_type
            for event_type in causal_types
        ),
        "shadow_log": str(shadow_log_path(case_root, case_id).relative_to(output)),
        "shadow_record_count": len(shadow),
        "run_status": state.status.value,
        "revision": state.revision,
        "action_count": len(state.actions),
        "controller_failure": failure,
        "controller_returned": result is not None,
        "final_output_sha256": hashlib.sha256(
            state.final_output.encode("utf-8")
        ).hexdigest(),
        "final_output_bytes": len(state.final_output.encode("utf-8")),
        "latency_seconds": time.perf_counter() - started,
    }


def aggregate(
    cases: list[Mapping[str, Any]],
    results: list[Mapping[str, Any]],
) -> dict[str, Any]:
    count = len(results)
    ood = [item for item in results if item["expected"]["route_family"] == "abstain"]
    high_confidence = [
        item
        for item in results
        if float((item.get("router_output") or {}).get("confidence", {}).get("route_family", 0.0))
        >= 0.92
        and (item.get("router_output") or {}).get("route_family") != "abstain"
    ]
    run_ids_by_log: dict[str, set[str]] = {}
    for item in results:
        log = str(item["shadow_log"])
        run_ids_by_log.setdefault(log, set()).add(str(item["case_id"]))
    cross_run_mixing = (
        sum(len(ids) != 1 for ids in run_ids_by_log.values())
        + sum(not bool(item["shadow_records_run_id_match"]) for item in results)
    )
    metrics = {
        "sample_count": count,
        "route_accuracy": sum(bool(item["route_correct"]) for item in results) / count,
        "network_accuracy": sum(bool(item["network_correct"]) for item in results) / count,
        "ood_abstain_correct": sum(bool(item["ood_abstain_correct"]) for item in ood),
        "ood_count": len(ood),
        "high_confidence_count": len(high_confidence),
        "high_confidence_route_accuracy": (
            sum(bool(item["route_correct"]) for item in high_confidence) / len(high_confidence)
            if high_confidence
            else None
        ),
        "main_behavior_route_agreement": sum(
            (item.get("router_output") or {}).get("route_family")
            == (item.get("observed_main_behavior") or {}).get("route_family")
            for item in results
        )
        / count,
    }
    infrastructure = {
        "paired_cases": sum(bool(item["paired"]) for item in results),
        "prediction_error_cases": sum(bool(item["prediction_error"]) for item in results),
        "prediction_errors_nonfatal": all(
            not item["prediction_error"] or bool(item["controller_returned"])
            for item in results
        ),
        "tool_menu_unchanged_cases": sum(
            bool(item["tool_menu_unchanged"]) for item in results
        ),
        "all_influence_false": all(bool(item["all_influence_false"]) for item in results),
        "record_digests_valid": all(bool(item["record_digests_valid"]) for item in results),
        "cross_run_mixing": cross_run_mixing,
        "shadow_causal_event_count": sum(
            int(item["shadow_causal_event_count"]) for item in results
        ),
        "controller_failure_cases": sum(bool(item["controller_failure"]) for item in results),
    }
    gates = {
        "route_accuracy_gte_0_75": metrics["route_accuracy"] >= 0.75,
        "network_accuracy_gte_0_875": metrics["network_accuracy"] >= 0.875,
        "ood_abstain_1_of_1": (
            metrics["ood_count"] == 1 and metrics["ood_abstain_correct"] == 1
        ),
        "prediction_outcome_pairing_8_of_8": infrastructure["paired_cases"] == 8,
        "prediction_errors_nonfatal": infrastructure["prediction_errors_nonfatal"],
        "tool_menu_unchanged_8_of_8": infrastructure["tool_menu_unchanged_cases"] == 8,
        "cross_run_mixing_zero": infrastructure["cross_run_mixing"] == 0,
        "all_influence_false": infrastructure["all_influence_false"],
        "record_digests_valid": infrastructure["record_digests_valid"],
        "shadow_causal_event_count_zero": infrastructure["shadow_causal_event_count"] == 0,
    }
    return {
        "metrics": metrics,
        "infrastructure": infrastructure,
        "gates": gates,
        "all_canary_gates_pass": all(gates.values()),
        "formal_stage1_graduation": False,
        "formal_stage1_graduation_reason": (
            "Requires at least 100 deduplicated, reviewed organic Shadow traces; "
            "this fixed canary is explicitly excluded."
        ),
        "case_ids": [str(item["case_id"]) for item in cases],
    }


def artifact_manifest(output: Path) -> dict[str, Any]:
    files = []
    for path in sorted(output.rglob("*")):
        if (
            not path.is_file()
            or path.name == "ARTIFACT_MANIFEST.json"
            or path.name == "long_horizon.db"
            or path.name.endswith(("-wal", "-shm"))
        ):
            continue
        files.append(
            {
                "path": path.relative_to(output).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return {
        "schema_version": "rwkv-lh.experiment-stable-artifact-manifest.v2",
        "generated_at": utc_now(),
        "exclusions": [
            "physical SQLite long_horizon.db, *-wal, and *-shm; use LOGICAL_STATE_MANIFEST.json"
        ],
        "files": files,
    }


def logical_state_manifest(output: Path) -> dict[str, Any]:
    databases: list[dict[str, Any]] = []
    for database in sorted(output.glob("runs/*/state/long_horizon.db")):
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            tables: dict[str, Any] = {}
            names = [
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
            ]
            for table in names:
                columns = [
                    str(row[1])
                    for row in connection.execute(f'PRAGMA table_info("{table}")')
                ]
                rows = []
                for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                    rows.append(
                        [
                            {
                                "blob_sha256": hashlib.sha256(value).hexdigest(),
                                "bytes": len(value),
                            }
                            if isinstance(value, bytes)
                            else value
                            for value in row
                        ]
                    )
                tables[table] = {
                    "columns": columns,
                    "row_count": len(rows),
                    "logical_rows_sha256": canonical_digest(rows),
                }
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        finally:
            connection.close()
        snapshot = {
            "database": database.relative_to(output).as_posix(),
            "integrity_check": integrity,
            "tables": tables,
        }
        snapshot["logical_database_sha256"] = canonical_digest(snapshot)
        databases.append(snapshot)
    return {
        "schema_version": "rwkv-lh.experiment-logical-sqlite-manifest.v1",
        "generated_at": utc_now(),
        "method": "SQLite mode=ro; tables/rows ordered; BLOBs represented by SHA-256",
        "databases": databases,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-transitions", type=int, default=200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output.expanduser().resolve()
    if output.exists():
        raise SystemExit(f"refusing to overwrite formal canary output: {output}")
    if not 1 <= args.max_transitions <= 500:
        raise SystemExit("max-transitions must be between 1 and 500")
    cases = verified_cases()
    code_manifest = verified_code_manifest()
    engine = verified_engine()
    settings = get_runtime_settings()
    client = OpenAICompatibleRWKVClient(settings)
    try:
        health = client.health().to_dict()
    finally:
        client.close()
    if not health.get("available"):
        raise SystemExit(f"main RWKV endpoint unavailable: {health.get('error')}")

    output.mkdir(parents=True)
    run_started_at = utc_now()
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        case_id = str(case["case_id"])
        print(f"[{index}/{len(cases)}] starting {case_id}", flush=True)
        result = run_case(case, output, args.max_transitions)
        results.append(result)
        partial = {
            "schema_version": SCHEMA_VERSION,
            "status": "running",
            "run_started_at": run_started_at,
            "completed_cases": len(results),
            "results": results,
        }
        write_json(output / "partial_results.json", partial)
        print(
            f"[{index}/{len(cases)}] finished {case_id}: "
            f"router={result['router_output'].get('route_family', 'error')} "
            f"main={result['observed_main_behavior'].get('route_family', 'unknown')} "
            f"status={result['run_status']}",
            flush=True,
        )

    summary = aggregate(cases, results)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "preregistration": str(
            (PROTOCOL_ROOT / "PREREGISTRATION.md").relative_to(ROOT)
        ),
        "dataset": {
            "schema_version": "rwkv-lh.state-router-shadow-canary.v1",
            "path": str((DATASET / "cases.json").relative_to(ROOT)),
            "sha256": EXPECTED_CASES_SHA256,
        },
        "frozen_code_manifest": {
            "path": str(CODE_MANIFEST.relative_to(ROOT)),
            "sha256": file_sha256(CODE_MANIFEST),
            "file_count": len(code_manifest.get("files") or []),
        },
        "local_router_engine": engine,
        "main_runtime": {
            "endpoint": settings.base_url,
            "model": settings.model,
            "backend_profile": settings.backend_profile,
            "health": health,
        },
        "parameters": {"max_transitions": args.max_transitions, "case_order": "dataset order"},
        "run_started_at": run_started_at,
        "run_finished_at": utc_now(),
        "results": results,
        **summary,
    }
    write_json(output / "results.json", payload)
    write_json(output / "LOGICAL_STATE_MANIFEST.json", logical_state_manifest(output))
    write_json(output / "ARTIFACT_MANIFEST.json", artifact_manifest(output))
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), flush=True)
    return 0 if summary["all_canary_gates_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
