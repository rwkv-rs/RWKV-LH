"""Generic fail-closed preflight for preregistered RWKV state continuation."""

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
BASE = Path("/home/chase/weights/BlinkDL__rwkv7-g1/rwkv7-g1i-13.3b-20260805-ctx16384.pth")
BASE_SHA = "5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562"
SOURCE_EXPECTED = {
    "train.py": "00b713e1f3ece6b056c9f4b15a264c84f1aa4e2c17a257490242226942889307",
    "rwkvt/args_type.py": "eae3287a1ae8d36b15c1bad68970a8954f14cd612b1c4ea2dd2808325a948daf",
    "rwkvt/dataset/SFTdataset.py": "22b4e16b4efb950357b852b4af8bea239c988f237bfae4e142ae1a8793f9e82f",
    "rwkvt/dataset/dataset.py": "b3910be23e377d8aed5f17e978e7607513599a1f5211e8367153e65f3bd7fe89",
    "rwkvt/dataset/mask.py": "9b1a55790c22c1f73122b5e672adcac91d0af3b007110166e0763baf970e9de9",
    "rwkvt/rwkv7/att.py": "ae9765c714e4c1f1e80ff010933ff32a10c3fcbe17fb8539a1e3b98b9b195923",
    "rwkvt/peft_loading.py": "b0ffc7c47387595417df9cd1eab76771033daece2f31acc7218072574046848a",
    "rwkvt/state_init.py": "7911aaf2ad3c730f228424b45811f26ed39fbb79046a1060f16d8f49203f225d",
    "rwkvt/state_tuning.py": "75d70d322386a03090eede445ffae2bf56a5e67f12de49e3e4269fe427f7365d",
    "rwkvt/lightning_train/light_rwkv.py": "a0ed9dbea2e42007cb9203e7efcd99da8f5a67262ecdf14fb0485747b1c79aea",
    "rwkvt/lightning_train/trainer.py": "3378c30095c9bced39fab170f120b309d80ff363abb6c2c3b0481040065d7133",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_training_commands(rows: list[dict], expected_rows: int) -> None:
    """Validate mixed selector/direct-tool state-tuning targets fail-closed."""
    if len(rows) != expected_rows:
        raise ValueError("training row count changed")
    for index, row in enumerate(rows):
        prompt = row.get("prompt", "")
        target = row.get("target", "")
        if not prompt or not target or row.get("text") != prompt + target:
            raise ValueError(f"training text contract failed at row {index}")
        try:
            command = json.loads(target)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(
                f"training target is not one JSON command at row {index}"
            ) from error
        if not (
            isinstance(command, dict)
            and isinstance(command.get("function"), str)
            and command["function"]
            and isinstance(command.get("params"), dict)
        ):
            raise ValueError(f"training command contract failed at row {index}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--parent-sha256", required=True)
    parser.add_argument("--train-sha256", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--alignment-sha256", required=True)
    parser.add_argument("--train-rows", type=int, required=True)
    parser.add_argument("--dev-rows", type=int, required=True)
    parser.add_argument("--step-save", type=int, required=True)
    parser.add_argument("--lr-init", type=float, required=True)
    parser.add_argument("--lr-final", type=float, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--selection-label", required=True)
    args = parser.parse_args()

    train = args.data_dir / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
    manifest_path = args.data_dir / "manifest.json"
    report_path = args.data_dir / "remote_training_contract_validation.json"
    alignment_path = args.data_dir / "training_serving_tokenizer_alignment.json"
    expected = {
        BASE: BASE_SHA,
        args.parent: args.parent_sha256,
        train: args.train_sha256,
        manifest_path: args.manifest_sha256,
        report_path: args.report_sha256,
        alignment_path: args.alignment_sha256,
    }
    for path, digest in expected.items():
        if not path.is_file() or sha256(path) != digest:
            raise SystemExit(f"required input changed: {path}")
    for relative, digest in SOURCE_EXPECTED.items():
        path = PROJECT / relative
        if not path.is_file() or sha256(path) != digest:
            raise SystemExit(f"training source changed: {relative}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    if not manifest["training_ready"] or not manifest["remote_tokenizer_validated"]:
        raise SystemExit("dataset is not remote-training-ready")
    if manifest["counts"]["train"] != args.train_rows or manifest["counts"]["dev"] != args.dev_rows:
        raise SystemExit("dataset counts changed")
    if report["overall"]["failure_count"] != 0:
        raise SystemExit("remote training contract failed")
    if report["target_suffix_audit"]["exact_label_match_rate"] != 1.0:
        raise SystemExit("target-suffix labels are not exact")
    if report.get("jsonl_bos_token_id") != 0:
        raise SystemExit("training contract did not use BOS token 0")
    if not report["bos_alignment_audit"]["first_target_predicted_from_last_prompt_token"]:
        raise SystemExit("BOS causal alignment failed")
    if not (
        alignment["rows"] == args.train_rows + args.dev_rows
        and alignment["failure_count"] == 0
        and alignment["exact_token_id_match_rate"] == 1.0
        and alignment["bos_contract_match_rate"] == 1.0
    ):
        raise SystemExit("training-serving tokenizer alignment failed")
    rows = [json.loads(line) for line in train.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        validate_training_commands(rows, args.train_rows)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    parent = torch.load(args.parent, map_location="cpu", weights_only=True, mmap=True)
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
    if args.run_dir.exists() and any(args.run_dir.iterdir()):
        raise SystemExit(f"refusing non-empty output directory: {args.run_dir}")
    args.run_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": "rwkv-lh.state-tuning-run-preflight.v3",
        "status": "preflight_passed",
        "created_at": datetime.now().astimezone().isoformat(),
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "gpu_index": 0,
        "base_model": {"path": str(BASE), "sha256": BASE_SHA},
        "state_initialization": {"mode": "verified_state_continuation", "path": str(args.parent), "sha256": args.parent_sha256, "tensor_count": 61},
        "dataset": {
            "path": str(train),
            "sha256": args.train_sha256,
            "manifest_sha256": args.manifest_sha256,
            "remote_validation_sha256": args.report_sha256,
            "training_serving_alignment_sha256": args.alignment_sha256,
            "rows": args.train_rows,
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "supervised_target_tokens": report["target_suffix_audit"]["total_supervised_tokens"],
            "historical_assistant_tokens_supervised": 0,
        },
        "training": {
            "peft": "state", "op": "fla", "ctx_len": 2496,
            "epoch_steps": args.train_rows, "epoch_count": 1,
            "step_save": args.step_save, "lr_init": args.lr_init,
            "lr_final": args.lr_final, "lr_schedule": "cos",
            "warmup_steps": 40, "random_seed": args.seed,
            "precision": "bf16", "strategy": "deepspeed_stage_1",
            "selected_checkpoint_rule": args.selection_label,
        },
        "source_sha256": SOURCE_EXPECTED,
        "torch": torch.__version__,
    }
    (args.run_dir / "run_manifest.pretrain.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
