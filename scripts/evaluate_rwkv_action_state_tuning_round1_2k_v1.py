"""Evaluate deployed RWKV state on the frozen Round1 2K dev boundaries."""

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


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_one(index: int, row: dict[str, Any]) -> dict[str, Any]:
    client = OpenAICompatibleRWKVClient()
    started = time.perf_counter()
    raw = ""
    error = ""
    parsed_operation = ""
    parsed_arguments: dict[str, Any] | None = None
    try:
        with sampling_parameters(
            0.05,
            request_id=f"AST-R1-DEV-{index:04d}",
            top_p=1.0,
            top_k=0,
            presence_penalty=0.0,
            frequency_penalty=0.0,
            penalty_decay=0.996,
        ):
            response = client.text_completion(
                row["prompt"],
                max_tokens=160 if row["stage"] == "selector" else 256,
                stop=JSON_CALL_STOP_SUFFIXES,
            )
        raw = response.content
        if row["stage"] == "selector":
            parsed_operation = parse_tool_selection(raw)
            parsed_arguments = {"name": parsed_operation}
        else:
            command = parse_model_command(raw)
            parsed_operation = command.name
            parsed_arguments = command.arguments
    except Exception as exc:  # recorded as an evaluation outcome
        error = f"{type(exc).__name__}: {exc}"[:1000]

    if row["stage"] == "selector":
        expected_arguments = {"name": row["target_operation"]}
    else:
        expected_arguments = parse_model_command(row["target"]).arguments
    schema_valid = parsed_arguments is not None
    operation_correct = schema_valid and parsed_operation == row["target_operation"]
    arguments_exact = operation_correct and parsed_arguments == expected_arguments
    return {
        "index": index,
        "trajectory_id": row["trajectory_id"],
        "failure_cluster": row["failure_cluster"],
        "failure_signature_id": row["failure_signature_id"],
        "stage": row["stage"],
        "expected_operation": row["target_operation"],
        "parsed_operation": parsed_operation,
        "schema_valid": schema_valid,
        "operation_correct": operation_correct,
        "arguments_exact": arguments_exact,
        "raw_output": raw,
        "error": error,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def rates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    return {
        "rows": count,
        "schema_valid_rate": sum(row["schema_valid"] for row in rows) / count,
        "operation_accuracy": sum(row["operation_correct"] for row in rows) / count,
        "exact_transition_accuracy": sum(row["arguments_exact"] for row in rows) / count,
        "mean_latency_ms": sum(row["latency_ms"] for row in rows) / count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=32)
    args = parser.parse_args()
    settings = get_runtime_settings()
    source = DATA / "stage_sft.dev.jsonl"
    dev = read_jsonl(source)
    if len(dev) != 200:
        raise SystemExit("frozen dev split must contain 200 rows")

    results: list[dict[str, Any] | None] = [None] * len(dev)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {
            executor.submit(evaluate_one, index, row): index
            for index, row in enumerate(dev)
        }
        for completed, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results[result["index"]] = result
            if completed % 25 == 0:
                print(f"completed {completed}/{len(dev)}", flush=True)
    evaluated = [row for row in results if row is not None]

    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_stage: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evaluated:
        by_cluster[row["failure_cluster"]].append(row)
        by_signature[row["failure_signature_id"]].append(row)
        by_stage[row["stage"]].append(row)
    report = {
        "schema_version": "rwkv-lh.action-state-tuning-live-eval.v1",
        "label": args.label,
        "dataset_version": "rwkv-lh.action-state-tuning.round1-2k.v1",
        "dev_sha256": sha256(source),
        "endpoint": settings.base_url,
        "model": settings.model,
        "backend_profile": settings.backend_profile,
        "sampling": {
            "temperature": 0.05,
            "top_p": 1.0,
            "top_k": 0,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "penalty_decay": 0.996,
            "seed": None,
            "seed_note": "vllm-rwkv rapid sampler does not expose a request seed",
            "selector_max_tokens": 160,
            "direct_max_tokens": 256,
        },
        "concurrency": max(1, args.concurrency),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "overall": rates(evaluated),
        "by_cluster": {key: rates(value) for key, value in sorted(by_cluster.items())},
        "by_signature": {key: rates(value) for key, value in sorted(by_signature.items())},
        "by_stage": {key: rates(value) for key, value in sorted(by_stage.items())},
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
    print(json.dumps({key: report[key] for key in ("label", "duration_seconds", "overall", "by_cluster", "error_types")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
