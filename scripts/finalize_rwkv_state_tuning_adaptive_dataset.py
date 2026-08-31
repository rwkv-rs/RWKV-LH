"""Finalize one trace-selected adaptive state-tuning dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = (ROOT / "data/datasets").resolve()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--expected-train", type=int, required=True)
    parser.add_argument("--expected-dev", type=int, default=400)
    args = parser.parse_args()
    data = args.data_dir.resolve()
    if DATASET_ROOT not in data.parents:
        raise SystemExit("adaptive dataset must remain under data/datasets")
    manifest_path = data / "manifest.json"
    report_path = data / "remote_training_contract_validation.json"
    alignment_path = data / "training_serving_tokenizer_alignment.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not str(manifest["dataset_version"]).startswith(
        "rwkv-lh.state-tuning.stage8-adaptive-round"
    ):
        raise SystemExit("unexpected adaptive dataset version")
    if manifest["training_ready"] or manifest["remote_tokenizer_validated"]:
        raise SystemExit("adaptive dataset is already finalized")
    if not (
        manifest["counts"]["train"] == args.expected_train
        and manifest["counts"]["dev"] == args.expected_dev
    ):
        raise SystemExit("adaptive dataset count changed")
    for relative, metadata in manifest["files"].items():
        path = data / relative
        if (
            not path.is_file()
            or path.stat().st_size != metadata["bytes"]
            or sha256(path) != metadata["sha256"]
        ):
            raise SystemExit(f"pre-finalization artifact changed: {relative}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    expected_rows = args.expected_train + args.expected_dev
    if not (
        report["overall"]["rows"] == expected_rows
        and report["overall"]["failure_count"] == 0
        and report["overall"]["maximum_tokens"] <= 2497
        and report["jsonl_bos_token_id"] == 0
        and report["target_suffix_audit"]["exact_label_match_rate"] == 1.0
        and report["target_suffix_audit"]["historical_assistant_tokens_supervised"]
        == 0
        and report["bos_alignment_audit"][
            "first_target_predicted_from_last_prompt_token"
        ]
    ):
        raise SystemExit("adaptive remote training contract failed")
    if not (
        alignment["rows"] == expected_rows
        and alignment["comparisons"] == expected_rows * 3
        and alignment["failure_count"] == 0
        and alignment["exact_token_id_match_rate"] == 1.0
        and alignment["bos_contract_match_rate"] == 1.0
    ):
        raise SystemExit("adaptive training-serving tokenizer alignment failed")
    manifest["training_ready"] = True
    manifest["remote_tokenizer_validated"] = True
    manifest["remote_validation"] = {
        "training_contract_report_sha256": sha256(report_path),
        "training_serving_alignment_sha256": sha256(alignment_path),
        "authoritative_rows": expected_rows,
        "maximum_tokens": report["overall"]["maximum_tokens"],
        "failure_count": 0,
        "target_suffix_exact_rate": 1.0,
        "historical_assistant_tokens_supervised": 0,
        "training_serving_token_id_match_rate": 1.0,
        "bos_contract_match_rate": 1.0,
    }
    for path in (report_path, alignment_path):
        manifest["files"][path.name] = {
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "training_ready": True,
                "manifest_sha256": sha256(manifest_path),
                "train": args.expected_train,
                "dev": args.expected_dev,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
