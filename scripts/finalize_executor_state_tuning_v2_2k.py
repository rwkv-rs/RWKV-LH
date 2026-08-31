#!/usr/bin/env python3
"""Finalize Executor V2 data after authoritative remote tokenizer validation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATA = ROOT / "data/datasets/rwkv_lh_executor_state_tuning_v2_2k"
MANIFEST = DATA / "manifest.json"
REPORT = DATA / "remote_training_contract_validation.json"
EXPECTED_PRE_MANIFEST_SHA256 = (
    "4b99878b8b4f01c823cb365ba0bbb44a1d27b25b2470e3a7b36194f7727ea2a6"
)
EXPECTED_SOURCE = {
    "tokenizer": "a135fc8703c3edd31e81d681a92ef5c055607ad686a60590cf588aa299962424",
    "vocab": "e6dee3d4e31b4d5c40ac99508ac6c701ceef4bed681bf2167ce9a908552bca89",
    "dataset_py": "b3910be23e377d8aed5f17e978e7607513599a1f5211e8367153e65f3bd7fe89",
    "mask_py": "9b1a55790c22c1f73122b5e672adcac91d0af3b007110166e0763baf970e9de9",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl_rows(path: Path) -> int:
    return sum(1 for line in path.open(encoding="utf-8") if line.strip())


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(sha256(MANIFEST) == EXPECTED_PRE_MANIFEST_SHA256, "pre-manifest changed")
    manifest: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(
        manifest.get("dataset_version") == "rwkv-lh.executor-state-tuning.v2-2k",
        "dataset version changed",
    )
    require(not manifest.get("training_ready"), "dataset already finalized")
    for relative, metadata in dict(manifest["files"]).items():
        path = DATA / relative
        require(path.is_file(), f"missing artifact: {relative}")
        require(sha256(path) == metadata["sha256"], f"artifact digest changed: {relative}")
        require(path.stat().st_size == metadata["bytes"], f"artifact size changed: {relative}")
        if metadata.get("rows") is not None:
            require(jsonl_rows(path) == metadata["rows"], f"row count changed: {relative}")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    require(
        report.get("schema_version") == "rwkv-lh.remote-training-contract-validation.v2",
        "remote validation schema changed",
    )
    require(report.get("ctx_len") == 2496, "remote ctx changed")
    require(report.get("jsonl_bos_token_id") == 0, "remote BOS changed")
    require(report.get("source_sha256") == EXPECTED_SOURCE, "remote sources changed")
    require(report["splits"]["train"]["rows"] == 2000, "remote train rows changed")
    require(report["splits"]["dev"]["rows"] == 480, "remote dev rows changed")
    require(report["overall"]["rows"] == 2480, "remote total rows changed")
    require(report["overall"]["failure_count"] == 0, "remote validation failed")
    require(
        report["overall"]["maximum_tokens"] <= report["request_token_capacity"],
        "remote tokenizer exceeded context",
    )
    target_audit = report["target_suffix_audit"]
    require(target_audit["authoritative_mydataset_exercised"] is True, "MyDataset not exercised")
    require(target_audit["rows"] == 2480, "target audit rows changed")
    require(target_audit["exact_label_match_rate"] == 1.0, "target labels changed")
    require(target_audit["historical_assistant_tokens_supervised"] == 0, "history supervised")
    bos_audit = report["bos_alignment_audit"]
    require(bos_audit["enabled"] is True, "BOS audit disabled")
    require(bos_audit["bos_present_in_every_authoritative_input"] is True, "BOS missing")
    require(
        bos_audit["first_target_predicted_from_last_prompt_token"] is True,
        "target causal alignment failed",
    )

    report_sha = sha256(REPORT)
    manifest["training_ready"] = True
    manifest["training_blocker"] = ""
    manifest["finalized_at"] = datetime.now().astimezone().isoformat()
    manifest["training_file"] = "rwkv_state_tuning.train.requires_target_suffix.jsonl"
    manifest["development_file"] = "rwkv_state_tuning.dev.requires_target_suffix.jsonl"
    manifest["validation"]["remote_tokenizer_validated"] = True
    manifest["validation"]["remote_training_contract"] = report
    manifest["validation"]["remote_training_contract_report_sha256"] = report_sha
    manifest["remote"] = {
        "ssh_alias": "rwkv-8222",
        "project_dir": "/home/chase/chase/RWKV-PEFT",
        "data_dir": "/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_state_tuning_v2_2k",
        "training_file": "/home/chase/chase/RWKV-PEFT/data/rwkv_lh_executor_state_tuning_v2_2k/rwkv_state_tuning.train.requires_target_suffix.jsonl",
        "gpu": 0,
        "ctx_len": 2496,
        "jsonl_bos_token_id": 0,
        "source_sha256": EXPECTED_SOURCE,
    }
    manifest["files"][REPORT.name] = {
        "path": REPORT.name,
        "bytes": REPORT.stat().st_size,
        "sha256": report_sha,
        "rows": None,
    }
    manifest["sources"][str(Path(__file__).relative_to(ROOT))] = {
        "sha256": sha256(Path(__file__)),
        "version": "executor-v2-finalizer.v1",
        "use": "fail-closed remote tokenizer/target-mask finalization",
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "dataset_version": manifest["dataset_version"],
                "training_ready": manifest["training_ready"],
                "train_rows": manifest["counts"]["train"]["rows"],
                "dev_rows": manifest["counts"]["dev"]["rows"],
                "maximum_remote_tokens": report["overall"]["maximum_tokens"],
                "target_suffix_exact_rate": target_audit["exact_label_match_rate"],
                "report_sha256": report_sha,
                "manifest_sha256": sha256(MANIFEST),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
