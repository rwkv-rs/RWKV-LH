"""Fail-closed preflight for the frozen Stage7 state-continuation run."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import socket
from datetime import datetime
from pathlib import Path

import torch


PROJECT = Path("/home/chase/chase/RWKV-PEFT")
DATA = PROJECT / "data/rwkv_lh_state_tuning_stage7_factory_contrast_v1"
RUN = PROJECT / "out/g1i-13.3b-rwkv-lh-stage7-factory-contrast2000-cont-stage4-lr3e-6-seed833"
BASE = Path("/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth")
PARENT = PROJECT / "out/g1i-13.3b-rwkv-lh-stage4-balanced1140-cont-stage1-lr1e-5-seed830/rwkv-step-1140.pth"
RUNNER = PROJECT / "scripts/run_remote_rwkv_lh_stage7_factory_contrast_state_tuning.sh"
EXPECTED = {
    BASE: "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562",
    PARENT: "8af6f29bb8cd68ed2f5e7ca6bcee56f7df7c53bccb083a80d1fa51e680d81960",
    DATA / "manifest.json": "4033a1c92d68e028b206f1c2acd37369ae3ea29492513658e999dd74f26d2b70",
    DATA / "rwkv_state_tuning.train.requires_target_suffix.jsonl": "b9bcb35b9f9dcc715725fadd093a7f7933a154749f9d7fb733357bd74c57bd55",
    DATA / "remote_training_contract_validation.json": "6abe19907588405963e0ca571944c2a737282b1c543e004eef34d6f986b16fcd",
    DATA / "training_serving_tokenizer_alignment.json": "da78e978641dd2be8dd3166647a1ee59c4d6ac07f058179ed76fc57ba2033d36",
    RUNNER: "5595b82440eacca5263cc823c77c2206db79fcc034fc95f36cc29b7d10036c10",
}
SOURCE_EXPECTED = {
    "train.py": "00b713e1f3ece6b056c9f4b15a264c84f1aa4e2c17a257490242226942889307",
    "rwkvt/args_type.py": "eae3287a1ae8d36b15c1bad68970a8954f14cd612b1c4ea2dd2808325a948daf",
    "rwkvt/dataset/dataset.py": "28560c7d4dfa62c0a26953b6d993ad000a8dd1ea4cf9f9d973c00774f05e39ea",
    "rwkvt/dataset/mask.py": "8425e8fab950bcd8ea2a9be8f2113c1829619be04a0a61075f933054410a1355",
    "rwkvt/rwkv7/att.py": "ae9765c714e4c1f1e80ff010933ff32a10c3fcbe17fb8539a1e3b98b9b195923",
    "rwkvt/peft_loading.py": "746cb8a07a5bf80b1db163a353357b0d7672762a2859d587e3384fecf5a708be",
    "rwkvt/state_init.py": "2e1bf49b25a18b3a3a5378daba60ed99c00716b07e97670bbc232ee940f0d293",
    "rwkvt/lightning_train/trainer.py": "89bd8b2c24482349584f6ce878584c6a2c452d472d8e92b66799b1228ae2451d",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("check", "commit"), required=True)
    args = parser.parse_args()
    for path, digest in EXPECTED.items():
        if not path.is_file() or sha256(path) != digest:
            raise SystemExit(f"required artifact changed: {path}")
    for relative, digest in SOURCE_EXPECTED.items():
        path = PROJECT / relative
        if not path.is_file() or sha256(path) != digest:
            raise SystemExit(f"training source changed: {relative}")

    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads(
        (DATA / "remote_training_contract_validation.json").read_text(encoding="utf-8")
    )
    alignment = json.loads(
        (DATA / "training_serving_tokenizer_alignment.json").read_text(encoding="utf-8")
    )
    if not manifest["training_ready"] or not manifest["remote_tokenizer_validated"]:
        raise SystemExit("dataset is not remote-training-ready")
    if manifest["counts"]["train"] != 2000 or manifest["counts"]["dev"] != 400:
        raise SystemExit("dataset counts changed")
    contract = manifest["training_contract"]
    if contract != {
        "training_file": "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        "development_file": "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        "loss_mask": "target_suffix",
        "jsonl_bos_token_id": 0,
        "ctx_len": 2496,
        "peft": "state",
        "op": "fla",
        "seed": 833,
        "lr_init": "3e-6",
        "lr_final": "6e-7",
        "parent": "stage4-step1140-experimental",
        "checkpoint_steps": [500, 1000, 1500, 2000],
    }:
        raise SystemExit("training contract changed")
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        if (
            not path.is_file()
            or path.stat().st_size != metadata["bytes"]
            or sha256(path) != metadata["sha256"]
        ):
            raise SystemExit(f"manifest artifact changed: {relative}")
    if not (
        report["overall"]["rows"] == 2400
        and report["overall"]["failure_count"] == 0
        and report["overall"]["maximum_tokens"] <= 2497
        and report["target_suffix_audit"]["exact_label_match_rate"] == 1.0
        and report["target_suffix_audit"]["historical_assistant_tokens_supervised"] == 0
        and report["bos_alignment_audit"]["first_target_predicted_from_last_prompt_token"]
    ):
        raise SystemExit("authoritative RWKV-PEFT validation changed")
    if not (
        alignment["rows"] == 2400
        and alignment["comparisons"] == 7200
        and alignment["failure_count"] == 0
        and alignment["exact_token_id_match_rate"] == 1.0
        and alignment["bos_contract_match_rate"] == 1.0
    ):
        raise SystemExit("training-serving tokenizer validation changed")

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

    result = {
        "schema_version": "rwkv-lh.stage7-training-preflight.v1",
        "status": "preflight_passed",
        "mode": args.mode,
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
            "orientation": "direct_[V,K]",
        },
        "dataset": {
            "path": str(DATA),
            "manifest_sha256": EXPECTED[DATA / "manifest.json"],
            "train_sha256": EXPECTED[
                DATA / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
            ],
            "train_rows": 2000,
            "dev_rows": 400,
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "maximum_tokens": report["overall"]["maximum_tokens"],
            "supervised_target_tokens": report["target_suffix_audit"][
                "total_supervised_tokens"
            ],
        },
        "training": {
            "peft": "state",
            "op": "fla",
            "ctx_len": 2496,
            "epoch_steps": 2000,
            "epoch_count": 1,
            "step_save": 500,
            "candidate_steps": [500, 1000, 1500, 2000],
            "lr_init": 3e-6,
            "lr_final": 6e-7,
            "lr_schedule": "cos",
            "warmup_steps": 20,
            "data_shuffle": 0,
            "random_seed": 833,
            "precision": "bf16",
            "strategy": "deepspeed_stage_1",
            "selection_rule": "earliest checkpoint passing every preregistered hard gate; otherwise restore Stage1",
        },
        "runner_sha256": EXPECTED[RUNNER],
        "source_sha256": SOURCE_EXPECTED,
        "torch": torch.__version__,
    }
    if args.mode == "commit":
        RUN.mkdir(parents=True, exist_ok=False)
        (RUN / "run_manifest.pretrain.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
