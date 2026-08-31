#!/usr/bin/env python3
"""Run the frozen 40-case exact-tool Executor preflight without output repair."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.coverage_runner import (
    ExactToolCoverageRunner,
    ExecutorIdentity,
    canonical_json,
    file_sha256,
)
from rwkv_lh.model_session import SessionSampling
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.settings import RuntimeSettings

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_exact_tool_coverage_v1"
DEFAULT_MANIFEST = DATASET / "manifest.json"
DEFAULT_SOURCE = DATASET / "preflight.jsonl"
IDENTITY_SCHEMA = "rwkv-lh.executor-server-identity.v1"
SUMMARY_SCHEMA = "rwkv-lh.exact-tool-coverage-preflight-summary.v1"


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON object required: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError("preflight rows must be JSON objects")
    return rows


def _runtime(identity: ExecutorIdentity) -> RuntimeSettings:
    settings = RuntimeSettings(
        base_url=os.environ["RWKV_BASE_URL"].rstrip("/"),
        api_key=os.environ.get("RWKV_API_KEY", ""),
        model=identity.model,
        backend_profile="vllm-rwkv-native",
        connect_timeout_seconds=float(os.environ.get("RWKV_CONNECT_TIMEOUT", "10")),
        read_timeout_seconds=float(os.environ.get("RWKV_READ_TIMEOUT", "300")),
        retry_attempts=1,
        retry_backoff_seconds=0.0,
        default_temperature=0.05,
        default_top_p=1.0,
        default_top_k=0,
        default_presence_penalty=0.0,
        default_frequency_penalty=0.0,
        default_penalty_decay=0.996,
        max_model_len=int(os.environ.get("RWKV_MAX_MODEL_LEN", "16384")),
        return_token_ids=True,
        trust_environment_proxies=False,
        verify_tls=os.environ.get("RWKV_VERIFY_TLS", "true").casefold()
        not in {"0", "false", "no", "off"},
        tool_disclosure_mode="full",
        state_transport="prompt_replay",
        state_profile_id=identity.profile_id,
        state_profile_sha256=identity.profile_sha256,
    )
    settings.validate()
    return settings


def _identity(path: Path) -> tuple[ExecutorIdentity, dict[str, Any]]:
    manifest = _read_json(path)
    if manifest.get("schema_version") != IDENTITY_SCHEMA:
        raise ValueError("unsupported Executor identity manifest")
    identity = manifest.get("executor_identity")
    if not isinstance(identity, dict):
        raise TypeError("Executor identity manifest has no identity object")
    return ExecutorIdentity(**identity), manifest


def _write_exclusive(path: Path, value: dict[str, Any]) -> None:
    encoded = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        offset = 0
        while offset < len(encoded):
            offset += os.write(descriptor, encoded[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--executor-identity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-output-tokens", type=int, default=512)
    args = parser.parse_args()

    manifest_path = args.manifest.resolve(strict=True)
    source_path = args.source.resolve(strict=True)
    identity_path = args.executor_identity.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise SystemExit("preflight output directory already exists")
    if file_sha256(manifest_path) != args.manifest_sha256:
        raise SystemExit("coverage manifest SHA mismatch")
    manifest = _read_json(manifest_path)
    registered_preflight = manifest.get("files", {}).get("preflight.jsonl", {})
    if source_path.name != "preflight.jsonl" or file_sha256(
        source_path
    ) != registered_preflight.get("sha256"):
        raise SystemExit("preflight source differs from frozen coverage manifest")
    rows = _read_jsonl(source_path)
    if (
        len(rows) != 40
        or Counter(str(row.get("label") or "") for row in rows)
        != Counter({label: 2 for label in manifest["class_order"]})
        or any(row.get("split") != "preflight" for row in rows)
    ):
        raise SystemExit(
            "preflight source must contain two separate families per label"
        )

    identity, identity_manifest = _identity(identity_path)
    settings = _runtime(identity)
    registered_endpoint = str(identity_manifest.get("endpoint") or "").rstrip("/")
    if registered_endpoint != settings.base_url:
        raise SystemExit("runtime endpoint differs from Executor identity manifest")
    client = OpenAICompatibleRWKVClient(settings)
    health = client.health()
    if not health.available or tuple(health.models) != tuple(
        identity_manifest.get("models") or ()
    ):
        raise SystemExit(
            f"Executor health/served-model identity mismatch: {health.error}"
        )

    runner = ExactToolCoverageRunner(
        output_root=output,
        runtime_settings=settings,
        executor_identity=identity,
        fixture_manifest_sha256=args.manifest_sha256,
        completion_client_factory=lambda _case: OpenAICompatibleRWKVClient(settings),
        sampling=SessionSampling(
            temperature=0.05,
            top_p=1.0,
            top_k=0,
            presence_penalty=0.0,
            frequency_penalty=0.0,
            penalty_decay=0.996,
        ),
        max_output_tokens=args.max_output_tokens,
    )
    runner.journal.append(
        "preflight_run_started",
        {
            "schema_version": SUMMARY_SCHEMA,
            "source": source_path.relative_to(ROOT).as_posix(),
            "source_sha256": file_sha256(source_path),
            "fixture_manifest": manifest_path.relative_to(ROOT).as_posix(),
            "fixture_manifest_sha256": args.manifest_sha256,
            "executor_identity_manifest": identity_path.relative_to(ROOT).as_posix(),
            "executor_identity_manifest_sha256": file_sha256(identity_path),
            "runner_path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "runner_sha256": file_sha256(Path(__file__).resolve()),
            "coverage_runner_sha256": file_sha256(
                ROOT / "rwkv_lh/exact_tool_selector/coverage_runner.py"
            ),
            "health": health.to_dict(),
            "generation_concurrency": 1,
            "automatic_retry_count": 0,
            "forbidden_decoding_fields": [],
        },
    )
    results = [runner.run_case(row) for row in rows]
    accepted = sum(result.accepted for result in results)
    runner.journal.append(
        "preflight_run_finished",
        {
            "case_count": len(results),
            "accepted": accepted,
            "rejected": len(results) - accepted,
            "raw_retention_count": sum(
                bool(result.raw_output_sha256) for result in results
            ),
            "journal_sha256_before_terminal_record": file_sha256(runner.journal.path),
        },
    )
    summary = {
        "schema_version": SUMMARY_SCHEMA,
        "status": "passed" if accepted == len(results) else "failed",
        "case_count": len(results),
        "accepted": accepted,
        "rejected": len(results) - accepted,
        "source_sha256": file_sha256(source_path),
        "fixture_manifest_sha256": args.manifest_sha256,
        "executor_identity_manifest_sha256": file_sha256(identity_path),
        "journal_sha256": file_sha256(runner.journal.path),
        "results": [result.to_dict() for result in results],
    }
    _write_exclusive(output / "summary.json", summary)
    print(canonical_json({key: summary[key] for key in summary if key != "results"}))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
