"""Finalize Round1 2K only after authoritative remote training validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_ACTION_STATE_TUNING_ROUND1_2K_V1_20260826"
MANIFEST = DATA / "manifest.json"
REPORT = DATA / "remote_training_contract_validation.json"
AMENDMENT = EXPERIMENT / "PREREGISTRATION_AMENDMENT_TARGET_SUFFIX.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if manifest["dataset_version"] != "rwkv-lh.action-state-tuning.round1-2k.v1":
    raise SystemExit("unexpected dataset version")
if manifest["training_ready"] or manifest["remote_tokenizer_validated"]:
    raise SystemExit("dataset is already finalized")
if manifest["loss_mask"] != "target_suffix":
    raise SystemExit("dataset does not declare target_suffix")
for relative, metadata in manifest["files"].items():
    path = DATA / relative
    if (
        not path.is_file()
        or sha256(path) != metadata["sha256"]
        or path.stat().st_size != metadata["bytes"]
    ):
        raise SystemExit(f"pre-finalization artifact changed: {relative}")

report = json.loads(REPORT.read_text(encoding="utf-8"))
if report["overall"] != {
    "rows": 2200,
    "minimum_tokens": 1079,
    "maximum_tokens": 2457,
    "mean_tokens": 1525.8254545454545,
    "maximum_target_tokens": 76,
    "failure_count": 0,
}:
    raise SystemExit("unexpected remote tokenizer result")
target_audit = report["target_suffix_audit"]
if target_audit != {
    "authoritative_mydataset_exercised": True,
    "rows": 2200,
    "total_supervised_tokens": 53342,
    "expected_target_tokens": 53342,
    "historical_assistant_tokens_supervised": 0,
    "exact_label_match_rate": 1.0,
}:
    raise SystemExit("remote target-suffix label audit failed")

manifest["training_ready"] = True
manifest["remote_tokenizer_validated"] = True
manifest["validation"]["remote_training_contract"] = report
manifest["validation"]["remote_training_contract_report_sha256"] = sha256(REPORT)
manifest["remote"].update(
    {
        "tokenizer_validation_required": False,
        "loss_mask": "target_suffix",
        "training_file": (
            "/home/chase/chase/RWKV-PEFT/data/"
            "rwkv_lh_action_state_tuning_round1_2k_v1/"
            "rwkv_state_tuning.train.requires_target_suffix.jsonl"
        ),
        "source_sha256": report["source_sha256"],
        "dataset_py_backup": (
            "/home/chase/chase/RWKV-PEFT/rwkvt/dataset/"
            "dataset.py.pre-rwkv-lh-target-suffix.ced6ae02ceae.bak"
        ),
    }
)
manifest["source_files"].update(
    {
        str(AMENDMENT.relative_to(ROOT)): {"sha256": sha256(AMENDMENT)},
        "scripts/finalize_rwkv_action_state_tuning_round1_2k_v1.py": {
            "sha256": sha256(Path(__file__))
        },
    }
)
manifest["files"][REPORT.name] = {
    "sha256": sha256(REPORT),
    "bytes": REPORT.stat().st_size,
}
MANIFEST.write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(
    json.dumps(
        {
            "dataset_version": manifest["dataset_version"],
            "training_ready": manifest["training_ready"],
            "remote_tokenizer_validated": manifest["remote_tokenizer_validated"],
            "loss_mask": manifest["loss_mask"],
            "training_file": manifest["training_file"],
            "remote_validation_sha256": sha256(REPORT),
        },
        ensure_ascii=False,
        indent=2,
    )
)
