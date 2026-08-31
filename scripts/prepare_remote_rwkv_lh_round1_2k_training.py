"""Fail-closed preflight for the remote Round1 2K state-tuning run."""

from __future__ import annotations

import hashlib
import json
import platform
import socket
from datetime import datetime
from pathlib import Path

import torch


PROJECT = Path("/home/chase/chase/RWKV-PEFT")
DATA = PROJECT / "data/rwkv_lh_action_state_tuning_round1_2k_v1"
MODEL = Path("/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth")
TRAIN = DATA / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
MANIFEST = DATA / "manifest.json"
REPORT = DATA / "remote_training_contract_validation.json"
RUN = PROJECT / "out/g1i-13.3b-rwkv-lh-r1-2k-v1-state-target-ctx2496-lr2e-5-seed826"
EXPECTED = {
    MODEL: "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562",
    TRAIN: "10d807891f33f589cd505438392217dc7dc6e63f0832a1cc3b9e01940c518819",
    MANIFEST: "b180e5d46748fd1e3d7af7327f6f68e8e4d349bc6333c2f846f2e914454faca3",
    REPORT: "3b56f38821273ea45534e5f1c524329982bafa20f1f8718eeffeb269f3699a31",
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

dataset_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
remote_report = json.loads(REPORT.read_text(encoding="utf-8"))
if not dataset_manifest["training_ready"] or not dataset_manifest["remote_tokenizer_validated"]:
    raise SystemExit("dataset manifest is not training-ready")
if dataset_manifest["loss_mask"] != "target_suffix":
    raise SystemExit("loss mask is not target_suffix")
if remote_report["overall"]["failure_count"] != 0:
    raise SystemExit("remote tokenizer validation failed")
if remote_report["target_suffix_audit"]["exact_label_match_rate"] != 1.0:
    raise SystemExit("remote target-suffix label audit failed")

rows = [
    json.loads(line)
    for line in TRAIN.read_text(encoding="utf-8").splitlines()
    if line.strip()
]
if len(rows) != 2000:
    raise SystemExit(f"training rows changed: {len(rows)}")
if any(
    row.get("text") != row.get("prompt", "") + row.get("target", "")
    or not row.get("target")
    for row in rows
):
    raise SystemExit("training prompt/target contract failed")

base = torch.load(MODEL, map_location="cpu", weights_only=True, mmap=True)
base_state_keys = [key for key in base if key.endswith(".time_state")]
if base_state_keys:
    raise SystemExit("base model unexpectedly contains a state continuation")

if RUN.exists() and any(RUN.iterdir()):
    raise SystemExit(f"refusing non-empty output directory: {RUN}")
RUN.mkdir(parents=True, exist_ok=True)
source_paths = [
    PROJECT / "train.py",
    PROJECT / "rwkvt/dataset/dataset.py",
    PROJECT / "rwkvt/rwkv7/att.py",
    PROJECT / "rwkvt/peft_loading.py",
    PROJECT / "rwkvt/lightning_train/trainer.py",
]
run_manifest = {
    "schema_version": "rwkv-lh.state-tuning-run-preflight.v1",
    "status": "preflight_passed",
    "created_at": datetime.now().astimezone().isoformat(),
    "host": socket.gethostname(),
    "platform": platform.platform(),
    "gpu_index": 0,
    "base_model": {
        "path": str(MODEL),
        "sha256": EXPECTED[MODEL],
        "base_time_state_keys": 0,
    },
    "state_initialization": {
        "mode": "zero_state_from_RWKV_Tmix_x070_State",
        "continuation_checkpoint": None,
    },
    "dataset": {
        "path": str(TRAIN),
        "sha256": EXPECTED[TRAIN],
        "manifest_sha256": EXPECTED[MANIFEST],
        "remote_validation_sha256": EXPECTED[REPORT],
        "rows": 2000,
        "loss_mask": "target_suffix",
        "supervised_target_tokens": 53342,
        "historical_assistant_tokens_supervised": 0,
    },
    "training": {
        "peft": "state",
        "ctx_len": 2496,
        "micro_bsz": 1,
        "accumulate_grad_batches": 1,
        "epoch_steps": 2000,
        "epoch_count": 1,
        "step_save": 250,
        "lr_init": 2e-5,
        "lr_final": 2e-6,
        "lr_schedule": "cos",
        "warmup_steps": 50,
        "beta1": 0.9,
        "beta2": 0.99,
        "adam_eps": 1e-8,
        "random_seed": 826,
        "precision": "bf16",
        "strategy": "deepspeed_stage_1",
        "grad_cp": 1,
        "op": "fla",
    },
    "source_sha256": {str(path.relative_to(PROJECT)): sha256(path) for path in source_paths},
    "torch": torch.__version__,
}
(RUN / "run_manifest.pretrain.json").write_text(
    json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(json.dumps(run_manifest, ensure_ascii=False, indent=2))
