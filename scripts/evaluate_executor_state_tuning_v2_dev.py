#!/usr/bin/env python3
"""Evaluate frozen Executor V2 prompts without altering RWKV output.

The exact HTTP response and extracted model text/token IDs are committed to an
append-only raw journal and fsynced before the function-call parser runs.  Each
source row is requested exactly once; transport or protocol failures are data,
not retry triggers.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.harness import HarnessError
from rwkv_lh.model_io import (
    JSON_CALL_STOP_SUFFIXES,
    ModelIOError,
    canonical_json,
    parse_model_command,
    parse_model_command_with_trace,
    validate_final_answer,
)
from rwkv_lh.retrieval import RetrievalRuntimeConfig, build_product_harness
from rwkv_lh.retrieval.policy import NetworkPolicyMode
from rwkv_lh.schema import TaskAction


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = (
    ROOT / "data/datasets/rwkv_lh_executor_state_tuning_v2_2k" / "stage_sft.dev.jsonl"
)
SAMPLING = {
    "temperature": 0.05,
    "top_p": 1.0,
    "top_k": 0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "penalty_decay": 0.996,
    "min_tokens": 0,
    "max_tokens": 256,
    "seed": 829,
    "stop": list(JSON_CALL_STOP_SUFFIXES),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            rows.append(value)
    return rows


def canonical_record_sha(record: Mapping[str, Any]) -> str:
    payload = canonical_json(record).encode("utf-8")
    return sha256_bytes(payload)


def append_fsynced(path: Path, value: Mapping[str, Any]) -> None:
    payload = (canonical_json(value) + "\n").encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def request_once(
    endpoint: str,
    request_body: bytes,
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/completions",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    status = 0
    body = b""
    transport_error = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = int(exc.code)
        body = exc.read()
        transport_error = f"HTTPError: {exc}"[:1000]
    except Exception as exc:  # failure is recorded; no retry is allowed
        transport_error = f"{type(exc).__name__}: {exc}"[:1000]
    return {
        "http_status": status,
        "response_body": body,
        "transport_error": transport_error,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def extract_openai_envelope(body: bytes) -> tuple[dict[str, Any], str]:
    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {}, f"UnicodeDecodeError: {exc}"
    try:
        value = json.loads(decoded)
    except json.JSONDecodeError as exc:
        return {}, f"JSONDecodeError: {exc}"
    if not isinstance(value, dict):
        return {}, "ProtocolError: response body is not an object"
    choices = value.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        return {}, "ProtocolError: response requires exactly one choice"
    choice = choices[0]
    if not isinstance(choice, dict) or not isinstance(choice.get("text"), str):
        return {}, "ProtocolError: response choice has no text"
    token_ids = choice.get("token_ids")
    if not isinstance(token_ids, list) or any(
        not isinstance(item, int) or isinstance(item, bool) or item < 0
        for item in token_ids
    ):
        return {}, "ProtocolError: response choice has no exact token_ids"
    return {
        "response_id": str(value.get("id") or ""),
        "response_model": str(value.get("model") or ""),
        "created": value.get("created"),
        "finish_reason": str(choice.get("finish_reason") or ""),
        "raw_output": choice["text"],
        "raw_token_ids": token_ids,
        "prompt_token_ids": value.get("prompt_token_ids", []),
        "usage": value.get("usage", {}),
    }, ""


def final_required_facts(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    source_cache: dict[Path, list[dict[str, Any]]] = {}
    for row in rows:
        if row["selected_operation"] != "final_answer":
            continue
        # First-action corpora retain the original verifier locator. Newer
        # multistage corpora deliberately contain only the direct expected
        # call, whose complete final text is already covered by canonical
        # equality. Do not synthesize or infer hidden facts for those rows.
        source_path = str(row.get("source_path") or "").strip()
        source_line = row.get("source_line")
        if not source_path or source_line is None:
            continue
        source = ROOT / source_path
        if source not in source_cache:
            source_cache[source] = read_jsonl(source)
        values = source_cache[source]
        source_index = int(row["source_line"]) - 1
        if source_index < 0 or source_index >= len(values):
            raise ValueError(f"source line is outside {source}: {source_index + 1}")
        source_row = values[source_index]
        facts = list(dict(source_row.get("verifier") or {}).get("required_facts") or [])
        if not facts or any(not isinstance(item, str) or not item for item in facts):
            raise ValueError(
                f"final row lacks frozen required facts: {row['sample_id']}"
            )
        result[str(row["sample_id"])] = facts
    return result


def evaluation_cluster(row: Mapping[str, Any]) -> str:
    """Return the declared, non-inferred grouping for either dataset schema."""

    return str(
        row.get("cluster")
        or row.get("critical_multistage_family")
        or row.get("source_kind")
        or "unclassified"
    )


def derive_result(
    row: dict[str, Any],
    raw_record: dict[str, Any],
    *,
    harness: Any,
    required_facts: Mapping[str, list[str]],
) -> dict[str, Any]:
    expected = parse_model_command(str(row["target"]))
    raw_output = str(raw_record.get("raw_output") or "")
    parsed_operation = ""
    parsed_arguments: dict[str, Any] | None = None
    normalizations: list[str] = []
    parse_error = ""
    contract_error = ""
    schema_valid = False
    try:
        command, trace = parse_model_command_with_trace(raw_output)
        parsed_operation = command.name
        parsed_arguments = command.arguments
        normalizations = list(trace.transformations)
        if command.name == "final_answer":
            validate_final_answer(command)
        else:
            harness.validate_action_contract(
                TaskAction(command.name, command.arguments)
            )
        schema_valid = True
    except (ModelIOError, HarnessError, KeyError, ValueError) as exc:
        error = f"{type(exc).__name__}: {exc}"[:1000]
        if parsed_arguments is None:
            parse_error = error
        else:
            contract_error = error
    operation_correct = schema_valid and parsed_operation == row["selected_operation"]
    wire_arguments_exact = (
        operation_correct
        and parsed_arguments == expected.arguments
        and expected.name == parsed_operation
    )
    canonical_exact = wire_arguments_exact
    action_normalization: dict[str, Any] = {}
    canonicalization_error = ""
    if operation_correct and parsed_operation != "final_answer":
        try:
            actual_action, action_normalization = harness.normalize_action_with_trace(
                TaskAction(parsed_operation, parsed_arguments or {})
            )
            expected_action = harness.normalize_action(
                TaskAction(expected.name, expected.arguments)
            )
            canonical_exact = actual_action.arguments == expected_action.arguments
        except (HarnessError, KeyError, TypeError, ValueError) as exc:
            # Some registered optional defaults are intentionally unusable as
            # executable values (for example bind_evidence source="").  The
            # raw action already passed the authoritative contract above; keep
            # exact wire equality as the fail-closed comparison and expose the
            # canonicalizer defect instead of aborting raw retention.
            canonicalization_error = f"{type(exc).__name__}: {exc}"[:1000]
    facts = list(required_facts.get(str(row["sample_id"]), []))
    final_facts_present = True
    if facts:
        text = parsed_arguments.get("text", "") if parsed_arguments else ""
        final_facts_present = isinstance(text, str) and all(
            fact in text for fact in facts
        )
    return {
        "schema_version": "rwkv-lh.executor-v2-derived-evaluation.v1",
        "raw_record_sha256": raw_record["record_sha256"],
        "raw_sequence": raw_record["sequence"],
        "source_index": raw_record["source_index"],
        "sample_id": row["sample_id"],
        "language": row["language"],
        "cluster": evaluation_cluster(row),
        "expected_operation": row["selected_operation"],
        "parsed_operation": parsed_operation,
        "parsed_arguments": parsed_arguments,
        "normalizations": normalizations,
        "action_normalization": action_normalization,
        "canonicalization_error": canonicalization_error,
        "transport_valid": not raw_record["transport_error"]
        and raw_record["http_status"] == 200,
        "response_envelope_valid": not raw_record["response_envelope_error"],
        "schema_valid": schema_valid,
        "operation_correct": operation_correct,
        "canonical_call_exact": canonical_exact,
        "wire_arguments_exact": wire_arguments_exact,
        "byte_exact_target": raw_output == row["target"],
        "final_required_facts": facts,
        "final_required_facts_present": final_facts_present,
        "parse_error": parse_error,
        "contract_error": contract_error,
        "latency_ms": raw_record["latency_ms"],
    }


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def rates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    if not count:
        return {"rows": 0}
    latencies = [float(row["latency_ms"]) for row in rows]
    metrics = (
        "transport_valid",
        "response_envelope_valid",
        "schema_valid",
        "operation_correct",
        "canonical_call_exact",
        "wire_arguments_exact",
        "byte_exact_target",
    )
    result: dict[str, Any] = {"rows": count}
    for metric in metrics:
        passed = sum(bool(row[metric]) for row in rows)
        result[metric] = passed
        result[f"{metric}_rate"] = passed / count
    result["latency_ms_p50"] = round(percentile(latencies, 0.5), 3)
    result["latency_ms_p95"] = round(percentile(latencies, 0.95), 3)
    final_rows = [row for row in rows if row["final_required_facts"]]
    result["final_required_facts_applicable_rows"] = len(final_rows)
    result["final_required_facts_present"] = sum(
        bool(row["final_required_facts_present"]) for row in final_rows
    )
    result["final_required_facts_present_rate"] = (
        result["final_required_facts_present"] / len(final_rows) if final_rows else None
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--endpoint", required=True, help="OpenAI-compatible /v1 URL")
    parser.add_argument("--model", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--one-per-operation", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    rows = read_jsonl(source)
    if args.limit and args.one_per_operation:
        raise SystemExit("--limit and --one-per-operation are mutually exclusive")
    if args.one_per_operation:
        first_by_operation: dict[str, dict[str, Any]] = {}
        for row in rows:
            first_by_operation.setdefault(str(row["selected_operation"]), row)
        rows = list(first_by_operation.values())
    if args.limit:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("evaluation source is empty")
    identities = [str(row.get("sample_id") or "") for row in rows]
    if not all(identities) or len(set(identities)) != len(identities):
        raise SystemExit("sample_id must be non-empty and unique")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    raw_path = output / "RAW_GENERATIONS.jsonl"
    derived_path = output / "DERIVED_EVALUATION.jsonl"
    protocol_path = output / "RUN_PROTOCOL.json"
    protocol = {
        "schema_version": "rwkv-lh.executor-v2-evaluation-protocol.v1",
        "profile": args.profile,
        "source": str(source),
        "source_sha256": sha256_file(source),
        "rows": len(rows),
        "endpoint": args.endpoint,
        "requested_model": args.model,
        "sampling": SAMPLING,
        "concurrency": max(1, args.concurrency),
        "timeout_seconds": args.timeout_seconds,
        "request_attempts_per_row": 1,
        "hidden_retries": 0,
        "output_repair": False,
        "postprocessed": False,
        "raw_saved_before_command_parse": True,
    }
    protocol_path.write_text(
        json.dumps(protocol, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=output / "unused_retrieval_snapshots",
        sandbox_commands=False,
    )
    facts = final_required_facts(rows)
    futures: dict[Future[dict[str, Any]], tuple[int, dict[str, Any], bytes]] = {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        for index, row in enumerate(rows):
            payload = {
                "model": args.model,
                "prompt": row["prompt"],
                **SAMPLING,
                "add_special_tokens": True,
                "return_token_ids": True,
                "request_id": f"EXE-V2-{args.profile}-{index:04d}",
                "stream": False,
            }
            request_body = canonical_json(payload).encode("utf-8")
            future = executor.submit(
                request_once,
                args.endpoint,
                request_body,
                args.timeout_seconds,
            )
            futures[future] = (index, row, request_body)

        previous_raw_sha = "0" * 64
        derived: list[dict[str, Any]] = []
        for sequence, future in enumerate(as_completed(futures), 1):
            index, row, request_body = futures[future]
            outcome = future.result()
            response_body = bytes(outcome["response_body"])
            envelope, envelope_error = extract_openai_envelope(response_body)
            raw_record = {
                "schema_version": "rwkv-lh.executor-v2-raw-generation.v1",
                "sequence": sequence,
                "previous_record_sha256": previous_raw_sha,
                "source_index": index,
                "sample_id": row["sample_id"],
                "profile": args.profile,
                "prompt_sha256": row["prompt_sha256"],
                "request_body_sha256": sha256_bytes(request_body),
                "requested_model": args.model,
                "sampling": SAMPLING,
                "request_id": f"EXE-V2-{args.profile}-{index:04d}",
                "request_attempt": 1,
                "postprocessed": False,
                "http_status": outcome["http_status"],
                "transport_error": outcome["transport_error"],
                "latency_ms": outcome["latency_ms"],
                "response_body_sha256": sha256_bytes(response_body),
                "response_body_base64": base64.b64encode(response_body).decode("ascii"),
                "response_envelope_error": envelope_error,
                **envelope,
            }
            raw_record["raw_output_sha256"] = sha256_bytes(
                str(raw_record.get("raw_output") or "").encode("utf-8")
            )
            raw_record["raw_output_utf8_bytes"] = len(
                str(raw_record.get("raw_output") or "").encode("utf-8")
            )
            raw_without_digest = dict(raw_record)
            raw_record["record_sha256"] = canonical_record_sha(raw_without_digest)
            append_fsynced(raw_path, raw_record)
            previous_raw_sha = raw_record["record_sha256"]

            try:
                result = derive_result(
                    row,
                    raw_record,
                    harness=harness,
                    required_facts=facts,
                )
                result["evaluator_internal_error"] = ""
            except Exception as exc:  # raw is already durable; never lose the run
                row_facts = list(facts.get(str(row["sample_id"]), []))
                result = {
                    "schema_version": "rwkv-lh.executor-v2-derived-evaluation.v1",
                    "raw_record_sha256": raw_record["record_sha256"],
                    "raw_sequence": raw_record["sequence"],
                    "source_index": raw_record["source_index"],
                    "sample_id": row["sample_id"],
                    "language": row["language"],
                    "cluster": evaluation_cluster(row),
                    "expected_operation": row["selected_operation"],
                    "parsed_operation": "",
                    "parsed_arguments": None,
                    "normalizations": [],
                    "action_normalization": {},
                    "canonicalization_error": "",
                    "transport_valid": not raw_record["transport_error"]
                    and raw_record["http_status"] == 200,
                    "response_envelope_valid": not raw_record[
                        "response_envelope_error"
                    ],
                    "schema_valid": False,
                    "operation_correct": False,
                    "canonical_call_exact": False,
                    "wire_arguments_exact": False,
                    "byte_exact_target": False,
                    "final_required_facts": row_facts,
                    "final_required_facts_present": False,
                    "parse_error": "",
                    "contract_error": "",
                    "evaluator_internal_error": f"{type(exc).__name__}: {exc}"[:1000],
                    "latency_ms": raw_record["latency_ms"],
                }
            append_fsynced(derived_path, result)
            derived.append(result)
            if sequence % 25 == 0 or sequence == len(rows):
                print(f"raw-first completed {sequence}/{len(rows)}", flush=True)

    by_operation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in derived:
        by_operation[row["expected_operation"]].append(row)
        by_language[row["language"]].append(row)
        by_cluster[row["cluster"]].append(row)
    summary = {
        "schema_version": "rwkv-lh.executor-v2-live-eval-summary.v1",
        "profile": args.profile,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "protocol_sha256": sha256_file(protocol_path),
        "raw_journal_sha256": sha256_file(raw_path),
        "derived_journal_sha256": sha256_file(derived_path),
        "raw_records": sum(1 for _ in raw_path.open(encoding="utf-8")),
        "derived_records": len(derived),
        "raw_retention_rate": len(derived) / len(rows),
        "raw_saved_before_command_parse": True,
        "request_attempts_per_row": 1,
        "hidden_retries": 0,
        "postprocessed": False,
        "run_valid": not any(row["evaluator_internal_error"] for row in derived),
        "overall": rates(derived),
        "by_operation": {
            key: rates(value) for key, value in sorted(by_operation.items())
        },
        "by_language": {
            key: rates(value) for key, value in sorted(by_language.items())
        },
        "by_cluster": {key: rates(value) for key, value in sorted(by_cluster.items())},
        "parse_error_types": dict(
            Counter(
                row["parse_error"].split(":", 1)[0]
                for row in derived
                if row["parse_error"]
            )
        ),
        "contract_error_types": dict(
            Counter(
                row["contract_error"].split(":", 1)[0]
                for row in derived
                if row["contract_error"]
            )
        ),
        "canonicalization_error_types": dict(
            Counter(
                row["canonicalization_error"].split(":", 1)[0]
                for row in derived
                if row["canonicalization_error"]
            )
        ),
        "evaluator_internal_error_types": dict(
            Counter(
                row["evaluator_internal_error"].split(":", 1)[0]
                for row in derived
                if row["evaluator_internal_error"]
            )
        ),
    }
    (output / "SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps({"profile": args.profile, "overall": summary["overall"]}, indent=2)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
