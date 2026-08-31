"""Build a no-duplicate residual curriculum from a completed Stage8 dev trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
STAGE8 = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_mutation_stop_v1"
STAGE7 = ROOT / "data/datasets/rwkv_lh_state_tuning_stage7_factory_contrast_v1"
ROUND1 = ROOT / "data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1"
PAIR = {
    ("mutation_success_stop", "after-identical-repeat"): "after-first-success",
    ("mutation_success_stop", "changed-required-value"): "before-mutation",
    ("mutation_success_stop", "after-first-success"): "before-mutation",
    ("mutation_success_stop", "before-mutation"): "after-first-success",
    ("idempotent_repeat_stop", "identical-count-two"): "first-success",
    ("idempotent_repeat_stop", "target-wrong"): "first-success",
    ("idempotent_repeat_stop", "unrelated-success"): "first-success",
    ("idempotent_repeat_stop", "first-success"): "target-wrong",
    ("investigate_scope_stop", "source-incomplete"): "source-unobserved",
    ("investigate_scope_stop", "source-complete"): "source-unobserved",
    ("investigate_scope_stop", "downstream-missing-out-of-scope"): "source-unobserved",
    ("investigate_scope_stop", "source-unobserved"): "source-complete",
    ("verify_evidence_stop", "target-evidence-incomplete"): "target-evidence-missing",
    ("verify_evidence_stop", "both-evidence-complete"): "target-evidence-missing",
    ("verify_evidence_stop", "source-evidence-missing"): "both-evidence-complete",
    ("verify_evidence_stop", "target-evidence-missing"): "both-evidence-complete",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_key(row: Mapping[str, Any], salt: str) -> str:
    return hashlib.sha256(
        (
            salt
            + "|"
            + str(row.get("semantic_family_id") or "")
            + "|"
            + str(row["prompt_sha256"])
        ).encode("utf-8")
    ).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--round", type=int, choices=(2, 3), required=True)
    parser.add_argument("--accuracy-threshold", type=float, default=0.95)
    parser.add_argument("--anchor-per-source", type=int, default=200)
    parser.add_argument("--exclude-round1-anchors", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    dataset_root = (ROOT / "data/datasets").resolve()
    if dataset_root not in output.parents:
        raise SystemExit("adaptive output must remain under data/datasets")
    if output.exists():
        raise FileExistsError(f"refusing existing adaptive dataset: {output}")

    stage8_train = read_jsonl(STAGE8 / "stage_sft.train.jsonl")
    stage8_dev = read_jsonl(STAGE8 / "stage_sft.dev.jsonl")
    evaluation = read_json(args.evaluation)
    dev_by_prompt = {str(row["prompt_sha256"]): row for row in stage8_dev}
    metrics: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for result in evaluation["results"]:
        source = dev_by_prompt[str(result["prompt_sha256"])]
        key = (str(source["failure_cluster"]), str(source["state_lane"]))
        metrics[key]["rows"] += 1
        metrics[key]["schema_valid"] += int(bool(result["schema_valid"]))
        metrics[key]["operation_correct"] += int(bool(result["operation_correct"]))
    if sum(row["rows"] for row in metrics.values()) != 400:
        raise RuntimeError("adaptive evaluation is not the frozen Stage8 dev400")

    weak: set[tuple[str, str]] = set()
    lane_metrics: dict[str, dict[str, float | int]] = {}
    for (cluster, lane), counts in sorted(metrics.items()):
        accuracy = counts["operation_correct"] / counts["rows"]
        schema_rate = counts["schema_valid"] / counts["rows"]
        lane_metrics[f"{cluster}/{lane}"] = {
            "rows": counts["rows"],
            "schema_valid_rate": schema_rate,
            "operation_accuracy": accuracy,
        }
        if accuracy < args.accuracy_threshold or schema_rate < 1.0:
            weak.add((cluster, lane))
    if not weak:
        weakest = min(
            metrics,
            key=lambda key: (
                metrics[key]["operation_correct"] / metrics[key]["rows"],
                key,
            ),
        )
        weak.add(weakest)
    selected_lanes = set(weak)
    selected_lanes.update((cluster, PAIR[(cluster, lane)]) for cluster, lane in weak)
    residual_rows = [
        dict(row)
        for row in stage8_train
        if (str(row.get("failure_cluster", "")), str(row.get("state_lane", "")))
        in selected_lanes
    ]
    if not residual_rows:
        raise RuntimeError("adaptive residual selection is empty")
    for row in residual_rows:
        row["adaptive_role"] = (
            "observed_residual"
            if (str(row["failure_cluster"]), str(row["state_lane"])) in weak
            else "matched_state_contrast"
        )

    anchors: list[dict[str, Any]] = []
    used_text = {str(row["text"]) for row in residual_rows}
    anchor_sources = [("stage7", STAGE7 / "stage_sft.train.jsonl")]
    if not args.exclude_round1_anchors:
        anchor_sources.append(
            ("round1", ROUND1 / "stage_sft.train.jsonl")
        )
    for label, path in anchor_sources:
        source = read_jsonl(path)
        source.sort(key=lambda row: stable_key(row, f"stage8-round{args.round}-{label}"))
        picked = []
        for row in source:
            text = str(row["text"])
            if text in used_text:
                continue
            picked.append(row)
            used_text.add(text)
            if len(picked) == args.anchor_per_source:
                break
        if len(picked) != args.anchor_per_source:
            raise RuntimeError(f"insufficient {label} safety anchors")
        for index, original in enumerate(picked, 1):
            row = dict(original)
            row.update(
                {
                    "failure_cluster": f"{label}_adaptive_safety_anchor",
                    "failure_signature_id": f"FST-S8-R{args.round}-{label.upper()}-ANCHOR",
                    "training_intent": "preserve_preexisting_selector_routing_and_safety",
                    "contrast_group": f"AST-S8-R{args.round}-{label.upper()}-ANCHOR-{index:04d}",
                    "adaptive_role": "safety_anchor",
                }
            )
            anchors.append(row)

    train = residual_rows + anchors
    train.sort(key=lambda row: stable_key(row, f"stage8-round{args.round}-train"))
    dev = [dict(row) for row in stage8_dev]
    if len({str(row["text"]) for row in [*train, *dev]}) != len(train) + len(dev):
        raise RuntimeError("adaptive corpus contains an exact stage duplicate")
    train_families = {str(row["semantic_family_id"]) for row in train}
    dev_families = {str(row["semantic_family_id"]) for row in dev}
    if train_families & dev_families:
        raise RuntimeError("adaptive train/dev semantic family overlap")

    output.mkdir(parents=True)
    write_jsonl(output / "stage_sft.train.jsonl", train)
    write_jsonl(output / "stage_sft.dev.jsonl", dev)
    write_jsonl(
        output / "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        ({"prompt": row["prompt"], "target": row["target"], "text": row["text"]} for row in train),
    )
    write_jsonl(
        output / "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        ({"prompt": row["prompt"], "target": row["target"], "text": row["text"]} for row in dev),
    )
    files = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(output.iterdir())
        if path.is_file()
    }
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": f"rwkv-lh.state-tuning.stage8-adaptive-round{args.round}.v1",
        "artifact_kind": "trace_selected_no_duplicate_matched_state_residual_curriculum",
        "purpose": "Correct only selector lanes that remained below the frozen Stage8 dev threshold while retaining matched contrasts and prior routing anchors.",
        "training_ready": False,
        "local_validation_complete": True,
        "remote_tokenizer_validated": False,
        "strong_model_as_label_source": False,
        "controller_replay_inherited_and_digest_bound": True,
        "counts": {
            "train": len(train),
            "dev": len(dev),
            "residual_rows": sum(row["adaptive_role"] == "observed_residual" for row in residual_rows),
            "matched_contrast_rows": sum(row["adaptive_role"] == "matched_state_contrast" for row in residual_rows),
            "safety_anchor_rows": len(anchors),
            "train_clusters": dict(Counter(str(row["failure_cluster"]) for row in train)),
        },
        "selection": {
            "accuracy_threshold_exclusive": args.accuracy_threshold,
            "anchor_per_source": args.anchor_per_source,
            "anchor_sources": [label for label, _ in anchor_sources],
            "weak_lanes": [f"{cluster}/{lane}" for cluster, lane in sorted(weak)],
            "selected_lanes": [f"{cluster}/{lane}" for cluster, lane in sorted(selected_lanes)],
            "lane_metrics": lane_metrics,
            "no_oversampling": True,
            "exact_stage_duplicate_count": 0,
            "train_dev_family_overlap_count": 0,
        },
        "source": {
            "evaluation": str(args.evaluation.resolve()),
            "evaluation_sha256": sha256(args.evaluation),
            "stage8_manifest_sha256": sha256(STAGE8 / "manifest.json"),
            "stage7_manifest_sha256": sha256(STAGE7 / "manifest.json"),
            "round1_manifest_sha256": (
                ""
                if args.exclude_round1_anchors
                else sha256(ROUND1 / "manifest.json")
            ),
            "generator_sha256": sha256(Path(__file__)),
        },
        "training_contract": {
            "training_file": "rwkv_state_tuning.train.requires_target_suffix.jsonl",
            "development_file": "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": 2496,
            "peft": "state",
            "op": "fla",
        },
        "files": files,
        "generation": (
            f"uv run python {Path(__file__).resolve()} "
            f"--evaluation {args.evaluation.resolve()} --output {output} "
            f"--round {args.round} --accuracy-threshold {args.accuracy_threshold} "
            f"--anchor-per-source {args.anchor_per_source}"
            + (" --exclude-round1-anchors" if args.exclude_round1_anchors else "")
        ),
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps(manifest["counts"] | manifest["selection"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
