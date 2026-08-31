"""Evaluate a frozen state-tuning boundary dataset against the deployed RWKV."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from rwkv_lh.model_io import (
    JSON_CALL_STOP_SUFFIXES,
    parse_model_command,
    parse_tool_selection,
)
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.sampling import sampling_parameters
from rwkv_lh.runtime.settings import get_runtime_settings


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "rows": 0,
            "schema_valid": 0,
            "operation_correct": 0,
            "arguments_exact": 0,
            "schema_valid_rate": 0.0,
            "operation_accuracy": 0.0,
            "exact_transition_accuracy": 0.0,
        }
    count = len(rows)
    schema_valid = sum(bool(row["schema_valid"]) for row in rows)
    operation_correct = sum(bool(row["operation_correct"]) for row in rows)
    arguments_exact = sum(bool(row["arguments_exact"]) for row in rows)
    return {
        "rows": count,
        "schema_valid": schema_valid,
        "operation_correct": operation_correct,
        "arguments_exact": arguments_exact,
        "schema_valid_rate": schema_valid / count,
        "operation_accuracy": operation_correct / count,
        "exact_transition_accuracy": arguments_exact / count,
        "mean_latency_ms": sum(float(row["latency_ms"]) for row in rows) / count,
    }


def contrast_rates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        group = str(row.get("contrast_group") or "")
        if group:
            groups[group].append(row)
    complete = {key: value for key, value in groups.items() if len(value) == 4}
    correct = sum(
        all(bool(row["operation_correct"]) for row in value)
        for value in complete.values()
    )
    return {
        "groups_seen": len(groups),
        "complete_groups": len(complete),
        "groups_with_unexpected_size": len(groups) - len(complete),
        "operation_consistent_groups": correct,
        "operation_consistency_rate": correct / len(complete) if complete else 0.0,
    }


def evaluate_one(
    index: int,
    row: dict[str, Any],
    *,
    temperature: float,
    seed: int | None,
) -> dict[str, Any]:
    client = OpenAICompatibleRWKVClient()
    raw = ""
    error = ""
    response_model = ""
    parsed_outer_function = ""
    parsed_operation = ""
    parsed_arguments: dict[str, Any] | None = None
    started = time.perf_counter()
    try:
        with sampling_parameters(
            temperature,
            seed=seed,
            request_id=f"STATE-BOUNDARY-{index:05d}",
            top_p=1.0,
            top_k=0,
            presence_penalty=0.0,
            frequency_penalty=0.0,
            penalty_decay=0.996,
        ):
            response = client.text_completion(
                str(row["prompt"]),
                max_tokens=160 if row["stage"] == "selector" else 256,
                stop=JSON_CALL_STOP_SUFFIXES,
            )
        raw = response.content
        response_model = response.model
        wire = parse_model_command(raw)
        parsed_outer_function = wire.name
        if row["stage"] == "selector":
            parsed_operation = parse_tool_selection(raw)
            parsed_arguments = {"name": parsed_operation}
        else:
            parsed_operation = wire.name
            parsed_arguments = wire.arguments
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:1000]
        if raw and not parsed_outer_function:
            try:
                parsed_outer_function = parse_model_command(raw).name
            except Exception:
                pass

    expected_operation = str(row["target_operation"])
    expected_arguments = (
        {"name": expected_operation}
        if row["stage"] == "selector"
        else parse_model_command(str(row["target"])).arguments
    )
    schema_valid = parsed_arguments is not None
    operation_correct = schema_valid and parsed_operation == expected_operation
    arguments_exact = operation_correct and parsed_arguments == expected_arguments
    return {
        "index": index,
        "trajectory_id": row["trajectory_id"],
        "turn_index": int(row.get("turn_index", 0)),
        "contrast_group": str(row.get("contrast_group") or ""),
        "prompt_sha256": row["prompt_sha256"],
        "semantic_family_id": row["semantic_family_id"],
        "failure_cluster": row["failure_cluster"],
        "failure_signature_id": row["failure_signature_id"],
        "stage": row["stage"],
        "expected_operation": expected_operation,
        "parsed_outer_function": parsed_outer_function,
        "parsed_operation": parsed_operation,
        "schema_valid": schema_valid,
        "operation_correct": operation_correct,
        "arguments_exact": arguments_exact,
        "raw_output": raw,
        "raw_output_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "response_model": response_model,
        "error": error,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=826)
    parser.add_argument("--concurrency", type=int, default=16)
    args = parser.parse_args()
    rows = read_jsonl(args.source)
    if not rows:
        raise SystemExit("evaluation source is empty")
    if len(
        {
            f"{row['trajectory_id']}:{row.get('turn_index', 0)}:{row['stage']}"
            for row in rows
        }
    ) != len(rows):
        raise SystemExit("evaluation row identity is not unique")

    results: list[dict[str, Any] | None] = [None] * len(rows)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        pending = {
            executor.submit(
                evaluate_one,
                index,
                row,
                temperature=args.temperature,
                seed=args.seed,
            ): index
            for index, row in enumerate(rows)
        }
        for completed, future in enumerate(as_completed(pending), 1):
            result = future.result()
            results[result["index"]] = result
            if completed % 25 == 0:
                print(f"completed {completed}/{len(rows)}", flush=True)
    evaluated = [row for row in results if row is not None]
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_expected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evaluated:
        by_stage[row["stage"]].append(row)
        by_cluster[row["failure_cluster"]].append(row)
        by_expected[row["expected_operation"]].append(row)
    settings = get_runtime_settings()
    report = {
        "schema_version": "rwkv-lh.state-boundary-live-eval.v1",
        "label": args.label,
        "source": str(args.source.resolve()),
        "source_sha256": sha256(args.source),
        "endpoint": settings.base_url,
        "requested_model": settings.model,
        "backend_profile": settings.backend_profile,
        "sampling": {
            "temperature": args.temperature,
            "seed": args.seed,
            "top_p": 1.0,
            "top_k": 0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "penalty_decay": 0.996,
            "selector_max_tokens": 160,
            "direct_max_tokens": 256,
        },
        "concurrency": max(1, args.concurrency),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "overall": rates(evaluated),
        "contrast": contrast_rates(evaluated),
        "by_stage": {key: rates(value) for key, value in sorted(by_stage.items())},
        "by_cluster": {key: rates(value) for key, value in sorted(by_cluster.items())},
        "by_expected_operation": {
            key: rates(value) for key, value in sorted(by_expected.items())
        },
        "outer_function_counts": dict(
            Counter(row["parsed_outer_function"] for row in evaluated)
        ),
        "error_types": dict(
            Counter(row["error"].split(":", 1)[0] for row in evaluated if row["error"])
        ),
        "results": evaluated,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "label": report["label"],
                "duration_seconds": report["duration_seconds"],
                "overall": report["overall"],
                "outer_function_counts": report["outer_function_counts"],
                "error_types": report["error_types"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
