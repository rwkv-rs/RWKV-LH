"""Finalize Stage6 after authoritative tokenizer and BOS validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage6_final_balance_v1"
MANIFEST = DATA / "manifest.json"
REPORT = DATA / "remote_training_contract_validation.json"
ALIGNMENT = DATA / "training_serving_tokenizer_alignment.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
if manifest["dataset_version"] != "rwkv-lh.state-tuning.stage6-final-balance.v1":
    raise SystemExit("unexpected dataset version")
if manifest["training_ready"] or manifest["remote_tokenizer_validated"]:
    raise SystemExit("dataset is already finalized")
for relative, metadata in manifest["files"].items():
    path = DATA / relative
    if not path.is_file() or sha256(path) != metadata["sha256"] or path.stat().st_size != metadata["bytes"]:
        raise SystemExit(f"pre-finalization artifact changed: {relative}")
report = json.loads(REPORT.read_text(encoding="utf-8"))
alignment = json.loads(ALIGNMENT.read_text(encoding="utf-8"))
if report["overall"]["rows"] != 1540 or report["overall"]["failure_count"] != 0:
    raise SystemExit("remote training contract failed")
if report["overall"]["maximum_tokens"] > 2497:
    raise SystemExit("remote tokenizer exceeded context contract")
if report["target_suffix_audit"]["exact_label_match_rate"] != 1.0:
    raise SystemExit("target-suffix label audit failed")
if report["target_suffix_audit"]["historical_assistant_tokens_supervised"] != 0:
    raise SystemExit("historical assistant tokens are supervised")
if not report["bos_alignment_audit"]["first_target_predicted_from_last_prompt_token"]:
    raise SystemExit("BOS causal alignment failed")
if not (
    alignment["rows"] == 1540
    and alignment["failure_count"] == 0
    and alignment["exact_token_id_match_rate"] == 1.0
    and alignment["bos_contract_match_rate"] == 1.0
):
    raise SystemExit("training/serving tokenizer alignment failed")
manifest["training_ready"] = True
manifest["remote_tokenizer_validated"] = True
manifest["remote_validation"] = {
    "training_contract_report_sha256": sha256(REPORT),
    "training_serving_alignment_sha256": sha256(ALIGNMENT),
    "authoritative_rows": 1540,
    "maximum_tokens": report["overall"]["maximum_tokens"],
    "failure_count": 0,
    "target_suffix_exact_rate": 1.0,
    "bos_contract_match_rate": 1.0,
}
for path in (REPORT, ALIGNMENT):
    manifest["files"][path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"training_ready": True, "manifest_sha256": sha256(MANIFEST)}, indent=2))
