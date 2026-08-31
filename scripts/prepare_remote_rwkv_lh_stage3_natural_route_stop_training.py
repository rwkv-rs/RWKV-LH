"""Fail-closed preflight for Stage-3 natural-route/stop state continuation."""

from __future__ import annotations

import hashlib
import json
import platform
import socket
from datetime import datetime
from pathlib import Path

import torch


PROJECT = Path("/home/chase/chase/RWKV-PEFT")
DATA = PROJECT / "data/rwkv_lh_state_tuning_stage3_natural_route_stop_v1"
BASE = Path(
    "/home/chase/weights/BlinkDL__rwkv7-g1/"
    "rwkv7-g1i-13.3b-20260805-ctx16384.pth"
)
PARENT = (
    PROJECT
    / "out/g1i-13.3b-rwkv-lh-stage1-selector500-cont-r1-lr5e-5-seed827"
    / "rwkv-step-500.pth"
)
TRAIN = DATA / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
MANIFEST = DATA / "manifest.json"
REPORT = DATA / "remote_training_contract_validation.json"
RUN = (
    PROJECT
    / "out/g1i-13.3b-rwkv-lh-stage3-natural-route-stop1400-cont-stage1-lr2e-5-seed829"
)
EXPECTED = {
    BASE: "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562",
    PARENT: "180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8",
    TRAIN: "e855d516d3866d885b2e72b40114a8bfd06a41d2de9117c7aa092c0e9c2a9ffc",
    MANIFEST: "f695f620473d4935d6f4d101b704b05182fac612780750e4402aaf051dab0c1d",
    REPORT: "6b14681c482b7c0ac86eca0bf5c9563952fb15a72ee0f04523f98fe76b63a0b7",
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
    if not path.is_file() or sha256(path) != expected:
        raise SystemExit(f"required input changed: {path}")
for relative, expected in SOURCE_EXPECTED.items():
    path = PROJECT / relative
    if not path.is_file() or sha256(path) != expected:
        raise SystemExit(f"training source changed: {relative}")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
report = json.loads(REPORT.read_text(encoding="utf-8"))
if not manifest["training_ready"] or not manifest["remote_tokenizer_validated"]:
    raise SystemExit("Stage-3 dataset is not remote-training-ready")
if manifest["counts"]["train"] != 1400 or manifest["counts"]["dev"] != 176:
    raise SystemExit("Stage-3 dataset counts changed")
if report["overall"]["failure_count"] != 0:
    raise SystemExit("remote training contract failed")
if report["target_suffix_audit"]["exact_label_match_rate"] != 1.0:
    raise SystemExit("remote target-suffix labels are not exact")
if report.get("jsonl_bos_token_id") != 0:
    raise SystemExit("remote training contract did not use BOS token 0")
if not report["bos_alignment_audit"]["first_target_predicted_from_last_prompt_token"]:
    raise SystemExit("remote BOS causal alignment failed")

rows = [
    json.loads(line)
    for line in TRAIN.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(rows) != 1400 or any(
    row.get("text") != row.get("prompt", "") + row.get("target", "")
    or '"function":"select_tool"' not in row.get("target", "")
    for row in rows
):
    raise SystemExit("Stage-3 selector training contract failed")

parent = torch.load(PARENT, map_location="cpu", weights_only=True, mmap=True)
expected_keys = {f"blocks.{layer}.att.time_state" for layer in range(61)}
if set(parent) != expected_keys:
    raise SystemExit("parent state key set changed")
for key in sorted(expected_keys):
    value = parent[key]
    if (
        value.dtype != torch.bfloat16
        or tuple(value.shape) != (64, 64, 64)
        or not torch.isfinite(value).all().item()
        or not torch.count_nonzero(value).item()
    ):
        raise SystemExit(f"parent state tensor contract failed: {key}")

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
        "rows": 1400,
        "loss_mask": "target_suffix",
        "jsonl_bos_token_id": 0,
        "supervised_target_tokens": report["target_suffix_audit"]["total_supervised_tokens"],
        "historical_assistant_tokens_supervised": 0,
    },
    "training": {
        "peft": "state",
        "op": "fla",
        "ctx_len": 2496,
        "epoch_steps": 1400,
        "epoch_count": 1,
        "step_save": 350,
        "lr_init": 2e-5,
        "lr_final": 4e-6,
        "lr_schedule": "cos",
        "warmup_steps": 40,
        "random_seed": 829,
        "precision": "bf16",
        "strategy": "deepspeed_stage_1",
        "selected_checkpoint_rule": "final_step_1400_unless_invalid",
    },
    "source_sha256": SOURCE_EXPECTED,
    "torch": torch.__version__,
}
(RUN / "run_manifest.pretrain.json").write_text(
    json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(run_manifest, ensure_ascii=False, indent=2))
