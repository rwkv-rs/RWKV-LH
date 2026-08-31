"""Fail-closed preflight for Stage-1 selector state continuation on the server."""

from __future__ import annotations

import hashlib
import json
import platform
import socket
from datetime import datetime
from pathlib import Path

import torch


PROJECT = Path("/home/chase/chase/RWKV-PEFT")
DATA = PROJECT / "data/rwkv_lh_state_tuning_stage1_selector_v1"
BASE = Path(
    "/home/chase/weights/BlinkDL__rwkv7-g1/"
    "rwkv7-g1i-13.3b-20260805-ctx16384.pth"
)
PARENT = (
    PROJECT
    / "out/g1i-13.3b-rwkv-lh-r1-2k-v1-state-target-ctx2496-lr2e-5-seed826"
    / "rwkv-step-2000.pth"
)
TRAIN = DATA / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
MANIFEST = DATA / "manifest.json"
REPORT = DATA / "remote_training_contract_validation.json"
RUN = (
    PROJECT
    / "out/g1i-13.3b-rwkv-lh-stage1-selector500-cont-r1-lr5e-5-seed827"
)
EXPECTED = {
    BASE: "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562",
    PARENT: "601c3c4df8c6e82918efa36d5425626eb9cffa4a0c5f0512da83aa5063e423f5",
    TRAIN: "0d50563893e9f1950bf8ab95d737c45e3d3c01dadd9f95bb7247da37c4afc4f7",
    MANIFEST: "d34ff4c5ada6a11896200180e71716707995d9f1b94c7414bdee054e501b176d",
    REPORT: "b8fbda841bc6508d18432a383b49fb2612ced352b8031c90a2975a53f2f73193",
}
SOURCE_EXPECTED = {
    "train.py": "00b713e1f3ece6b056c9f4b15a264c84f1aa4e2c17a257490242226942889307",
    "rwkvt/args_type.py": "eae3287a1ae8d36b15c1bad68970a8954f14cd612b1c4ea2dd2808325a948daf",
    "rwkvt/dataset/dataset.py": "2623899a459b23962422afb893c358ee7efd57b83c08c97a39706fc6b0d1356d",
    "rwkvt/rwkv7/att.py": "ae9765c714e4c1f1e80ff010933ff32a10c3fcbe17fb8539a1e3b98b9b195923",
    "rwkvt/peft_loading.py": "746cb8a07a5bf80b1db163a353357b0d7672762a2859d587e3384fecf5a708be",
    "rwkvt/state_init.py": "2e1bf49b25a18b3a3a5378daba60ed99c00716b07e97670bbc232ee940f0d293",
    "rwkvt/lightning_train/trainer.py": "89bd8b2c24482349584f6ce878584c6a2c452d472d8e92b66799b1228ae2451d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


for path, expected in EXPECTED.items():
    if not path.is_file():
        raise SystemExit(f"missing required input: {path}")
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"input digest mismatch: {path}: {actual}")
for relative, expected in SOURCE_EXPECTED.items():
    path = PROJECT / relative
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(f"training source changed: {relative}: {actual}")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
report = json.loads(REPORT.read_text(encoding="utf-8"))
if not manifest["training_ready"] or not manifest["remote_tokenizer_validated"]:
    raise SystemExit("Stage-1 manifest is not remote-training-ready")
if manifest["counts"]["train"] != 500 or manifest["counts"]["dev"] != 79:
    raise SystemExit("Stage-1 dataset counts changed")
if manifest["validation"]["target_outer_function"] != "select_tool":
    raise SystemExit("Stage-1 is not selector-only")
if report["overall"]["failure_count"] != 0:
    raise SystemExit("remote tokenizer contract failed")
if report["target_suffix_audit"]["exact_label_match_rate"] != 1.0:
    raise SystemExit("remote target-suffix labels are not exact")
if report.get("jsonl_bos_token_id") != 0:
    raise SystemExit("remote training contract did not use RWKV BOS token 0")
if not report.get("bos_alignment_audit", {}).get(
    "first_target_predicted_from_last_prompt_token"
):
    raise SystemExit("remote BOS causal alignment failed")

rows = [
    json.loads(line)
    for line in TRAIN.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(rows) != 500:
    raise SystemExit("Stage-1 training rows changed")
if any(
    row.get("text") != row.get("prompt", "") + row.get("target", "")
    or '"function":"select_tool"' not in row.get("target", "")
    for row in rows
):
    raise SystemExit("Stage-1 prompt/target contract failed")

parent = torch.load(PARENT, map_location="cpu", weights_only=True, mmap=True)
expected_keys = {f"blocks.{layer}.att.time_state" for layer in range(61)}
if set(parent) != expected_keys:
    raise SystemExit("parent state key set changed")
for key in sorted(expected_keys):
    value = parent[key]
    if value.dtype != torch.bfloat16 or tuple(value.shape) != (64, 64, 64):
        raise SystemExit(f"parent state tensor contract failed: {key}")
    if not torch.isfinite(value).all().item() or not torch.count_nonzero(value).item():
        raise SystemExit(f"parent state value contract failed: {key}")

if RUN.exists() and any(RUN.iterdir()):
    raise SystemExit(f"refusing non-empty output directory: {RUN}")
RUN.mkdir(parents=True, exist_ok=True)
run_manifest = {
    "schema_version": "rwkv-lh.state-tuning-run-preflight.v2",
    "status": "preflight_passed",
    "created_at": datetime.now().astimezone().isoformat(),
    "host": socket.gethostname(),
    "platform": platform.platform(),
    "gpu_index": 0,
    "base_model": {"path": str(BASE), "sha256": EXPECTED[BASE]},
    "state_initialization": {
        "mode": "verified_state_continuation",
        "path": str(PARENT),
        "sha256": EXPECTED[PARENT],
        "tensor_count": 61,
    },
    "dataset": {
        "path": str(TRAIN),
        "sha256": EXPECTED[TRAIN],
        "manifest_sha256": EXPECTED[MANIFEST],
        "remote_validation_sha256": EXPECTED[REPORT],
        "rows": 500,
        "loss_mask": "target_suffix",
        "jsonl_bos_token_id": 0,
        "supervised_target_tokens": report["target_suffix_audit"][
            "total_supervised_tokens"
        ],
        "historical_assistant_tokens_supervised": 0,
    },
    "training": {
        "peft": "state",
        "op": "fla",
        "jsonl_bos_token_id": 0,
        "ctx_len": 2496,
        "epoch_steps": 500,
        "epoch_count": 1,
        "step_save": 100,
        "lr_init": 5e-5,
        "lr_final": 1e-5,
        "lr_schedule": "cos",
        "warmup_steps": 20,
        "random_seed": 827,
        "precision": "bf16",
        "strategy": "deepspeed_stage_1",
        "selected_checkpoint_rule": "final_step_500_unless_invalid",
    },
    "source_sha256": SOURCE_EXPECTED,
    "torch": torch.__version__,
}
(RUN / "run_manifest.pretrain.json").write_text(
    json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(run_manifest, ensure_ascii=False, indent=2))
