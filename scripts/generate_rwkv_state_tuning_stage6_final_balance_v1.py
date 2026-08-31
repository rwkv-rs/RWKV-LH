"""Build the preregistered Stage6 final balanced state-tuning dataset."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from scripts import generate_rwkv_action_state_tuning_round1_2k_v1 as round1
from scripts import generate_rwkv_state_tuning_stage3_natural_route_stop_v1 as stage3
from scripts import generate_rwkv_state_tuning_stage4_balanced_boundary_v1 as stage4
from scripts import generate_rwkv_state_tuning_stage5_route_stop_v1 as stage5


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage6_final_balance_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_STATE_TUNING_STAGE4_TO_STAGE6_V1_20260827"
AMENDMENT = EXPERIMENT / "STAGE6_PREREGISTRATION_AMENDMENT.md"
STAGE5_RESULT = EXPERIMENT / "STAGE5_RESULT.md"
STAGE1_DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1"
STAGE4_DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage4_balanced_boundary_v1"
STAGE5_DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage5_route_stop_v1"
VERSION = "rwkv-lh.state-tuning.stage6-final-balance.v1"
VARIANTS = 4
SIGNATURES = {
    "stable_selector_replay": "FST-S6-001",
    "connector_boundary": "FST-S6-002",
    "ordinary_web_boundary": "FST-S6-003",
    "local_safety_boundary": "FST-S6-004",
    "mixed_local_first_boundary": "FST-S6-005",
    "privacy_local_first_boundary": "FST-S6-006",
    "completion_after_success": "FST-S6-007",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def immutable_request(prompt: str) -> str:
    marker = "User: Task state: "
    start = prompt.index(marker) + len(marker)
    state, _end = json.JSONDecoder().raw_decode(prompt[start:])
    return str(state["immutable_request"])


def identity(split: str, cluster: str, family: int, variant: int) -> tuple[str, str]:
    code = {
        "connector_boundary": "CB",
        "ordinary_web_boundary": "OW",
        "local_safety_boundary": "LO",
        "mixed_local_first_boundary": "ML",
        "privacy_local_first_boundary": "PL",
        "completion_after_success": "CS",
    }[cluster]
    return (
        f"AST-S6-SF-{code}-{split.upper()}-{family + 1:04d}",
        f"AST-S6-{code}-{split.upper()}-{family + 1:04d}-{variant + 1:02d}",
    )


def remap_stage(
    row: Mapping[str, Any], split: str, cluster: str, family: int, variant: int, intent: str
) -> dict[str, Any]:
    item = dict(row)
    family_id, trajectory_id = identity(split, cluster, family, variant)
    item.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": family_id,
            "split": split,
            "failure_cluster": cluster,
            "failure_signature_id": SIGNATURES[cluster],
            "training_intent": intent,
        }
    )
    return item


def stable_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, contamination = stage3.stable_rows()
    for row in rows:
        row["failure_signature_id"] = SIGNATURES["stable_selector_replay"]
        row["training_intent"] = "preserve_stage1_selector_safety_and_stopping"
    return rows, contamination


def stage4_boundary_anchors() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = [
        row
        for row in read_jsonl(STAGE4_DATA / "stage_sft.train.jsonl")
        if row["failure_cluster"] != "stable_selector_replay"
    ]
    cluster_map = {
        "natural_connector_paired": "connector_boundary",
        "ordinary_web_hard_negative": "ordinary_web_boundary",
        "local_only_network_hard_negative": "local_safety_boundary",
        "mixed_local_first_natural": "mixed_local_first_boundary",
        "privacy_local_first_natural": "privacy_local_first_boundary",
    }
    counters: Counter[str] = Counter()
    result: list[dict[str, Any]] = []
    contamination: list[dict[str, Any]] = []
    for row in source:
        cluster = cluster_map[str(row["failure_cluster"])]
        index = counters[cluster]
        counters[cluster] += 1
        family, variant = divmod(index, VARIANTS)
        item = remap_stage(
            row,
            "train",
            cluster,
            family,
            variant,
            "retain_complete_stage4_balanced_boundary_anchor",
        )
        result.append(item)
        contamination.append(
            {"trajectory_id": item["trajectory_id"], "request": immutable_request(str(item["prompt"]))}
        )
    expected = Counter(
        {
            "connector_boundary": 80,
            "ordinary_web_boundary": 160,
            "local_safety_boundary": 160,
            "mixed_local_first_boundary": 160,
            "privacy_local_first_boundary": 80,
        }
    )
    if counters != expected:
        raise RuntimeError(f"Stage4 boundary source changed: {counters}")
    return result, contamination


def stage5_residual_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = read_jsonl(STAGE5_DATA / "stage_sft.train.jsonl")
    connector = [row for row in source if row["failure_cluster"] == "github_connector_residual"]
    completion = [row for row in source if row["failure_cluster"] == "completion_after_success"]
    selected_completion = [completion[(index * len(completion)) // 80] for index in range(80)]
    if len(connector) != 40 or len({row["prompt_sha256"] for row in selected_completion}) != 80:
        raise RuntimeError("Stage5 residual source changed")
    result: list[dict[str, Any]] = []
    contamination: list[dict[str, Any]] = []
    for cluster, rows in (
        ("connector_boundary", connector),
        ("completion_after_success", selected_completion),
    ):
        family_offset = 20 if cluster == "connector_boundary" else 0
        for index, row in enumerate(rows):
            family, variant = divmod(index, VARIANTS)
            item = remap_stage(
                row,
                "train",
                cluster,
                family + family_offset,
                variant,
                "focused_connector_residual" if cluster == "connector_boundary" else "calibrated_stop_after_sufficient_evidence",
            )
            result.append(item)
            contamination.append(
                {"trajectory_id": item["trajectory_id"], "request": immutable_request(str(item["prompt"]))}
            )
    return result, contamination


def candidate(split: str, cluster: str, family: int, variant: int) -> dict[str, Any]:
    if cluster == "connector_boundary":
        row = stage5.focused_connector_candidate(split, family + 41000, variant)
    elif cluster == "ordinary_web_boundary":
        row = stage4.web_candidate(split, family + 42000, variant)
    elif cluster == "local_safety_boundary":
        row = stage4.local_candidate(split, family + 43000, variant)
    elif cluster == "mixed_local_first_boundary":
        row = stage4.mixed_candidate(split, family + 44000, variant)
    elif cluster == "privacy_local_first_boundary":
        row = stage4.privacy_candidate(split, family + 45000, variant)
    elif cluster == "completion_after_success":
        row = stage5.completion_candidate(split, family + 100, variant)
    else:
        raise ValueError(cluster)
    family_id, trajectory_id = identity(split, cluster, family, variant)
    row.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": family_id,
            "split": split,
            "failure_cluster": cluster,
            "failure_signature_id": SIGNATURES[cluster],
        }
    )
    return row


def replay_candidate(candidate_row: Mapping[str, Any], completion: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    if completion:
        row, validation = stage5.selected_completion_stage(candidate_row)
    else:
        row, validation = stage5.selected_initial_stage(candidate_row)
    row["failure_cluster"] = candidate_row["failure_cluster"]
    row["failure_signature_id"] = candidate_row["failure_signature_id"]
    row["training_intent"] = (
        "calibrated_stop_after_sufficient_evidence"
        if completion
        else "final_balanced_route_boundary_correction"
    )
    return row, validation


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    if not AMENDMENT.is_file() or not STAGE5_RESULT.is_file():
        raise RuntimeError("Stage6 preregistration amendment or Stage5 result is missing")

    stable, stable_contamination = stable_rows()
    anchors, anchor_contamination = stage4_boundary_anchors()
    residual, residual_contamination = stage5_residual_rows()

    raw_candidates: list[tuple[dict[str, Any], bool]] = []
    # Forty new ordinary-web residuals.
    for family in range(10):
        for variant in range(VARIANTS):
            raw_candidates.append((candidate("train", "ordinary_web_boundary", family + 40, variant), False))
    # Family-disjoint dev240.
    dev_quotas = {
        "connector_boundary": 12,
        "ordinary_web_boundary": 12,
        "local_safety_boundary": 8,
        "mixed_local_first_boundary": 12,
        "privacy_local_first_boundary": 6,
        "completion_after_success": 10,
    }
    for cluster, families in dev_quotas.items():
        for family in range(families):
            for variant in range(VARIANTS):
                raw_candidates.append((candidate("dev", cluster, family, variant), cluster == "completion_after_success"))

    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    raw_for_contamination: list[dict[str, Any]] = []
    for index, (candidate_row, completion) in enumerate(raw_candidates, 1):
        try:
            stage, validation = replay_candidate(candidate_row, completion)
        except Exception as exc:
            raise RuntimeError(
                f"Stage6 replay failed at {index}/{len(raw_candidates)} for {candidate_row['trajectory_id']}"
            ) from exc
        stages.append(stage)
        raw_for_contamination.append(candidate_row)
        validations.append(
            {"trajectory_id": candidate_row["trajectory_id"], "failure_cluster": candidate_row["failure_cluster"], **validation}
        )
        if index % 100 == 0:
            print(f"controller replay {index}/{len(raw_candidates)}", flush=True)

    train = [*stable, *anchors, *residual, *(row for row in stages if row["split"] == "train")]
    dev = [row for row in stages if row["split"] == "dev"]
    expected_train = Counter(
        {
            "stable_selector_replay": 500,
            "connector_boundary": 120,
            "ordinary_web_boundary": 200,
            "local_safety_boundary": 160,
            "mixed_local_first_boundary": 160,
            "privacy_local_first_boundary": 80,
            "completion_after_success": 80,
        }
    )
    expected_dev = Counter(
        {
            "connector_boundary": 48,
            "ordinary_web_boundary": 48,
            "local_safety_boundary": 32,
            "mixed_local_first_boundary": 48,
            "privacy_local_first_boundary": 24,
            "completion_after_success": 40,
        }
    )
    if Counter(row["failure_cluster"] for row in train) != expected_train:
        raise RuntimeError("Stage6 train quota changed")
    if Counter(row["failure_cluster"] for row in dev) != expected_dev:
        raise RuntimeError("Stage6 dev quota changed")
    if len(train) != 1300 or len(dev) != 240:
        raise RuntimeError(f"Stage6 split count changed: {len(train)}, {len(dev)}")
    if len({row["text"] for row in [*train, *dev]}) != 1540:
        raise RuntimeError("Stage6 exact stage duplicate detected")
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    if train_families & dev_families:
        raise RuntimeError("Stage6 semantic family crosses train/dev")
    contamination = round1._holdout_contamination(
        [*stable_contamination, *anchor_contamination, *residual_contamination, *raw_for_contamination]
    )

    OUTPUT.mkdir(parents=True)
    write_jsonl(OUTPUT / "stage_sft.train.jsonl", train)
    write_jsonl(OUTPUT / "stage_sft.dev.jsonl", dev)
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        ({"prompt": row["prompt"], "target": row["target"], "text": row["text"]} for row in train),
    )
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        ({"prompt": row["prompt"], "target": row["target"], "text": row["text"]} for row in dev),
    )
    write_jsonl(OUTPUT / "new_candidate_validation.jsonl", validations)
    write_json(
        OUTPUT / "residual_registry.json",
        {
            "schema_version": "rwkv-lh.stage6-residuals.v1",
            "source": "Stage5 frozen ECRA120",
            "residuals": {
                "pre_evidence_over_completion": "mixed 3/20, privacy 3/10, local 23/30 after 240 completion rows",
                "web_connector_boundary": "public-web 21/25 and connector 12/20",
            },
            "correction": "restart Stage1; restore all Stage4 boundary anchors; retain only 80/240 completion rows",
        },
    )
    (OUTPUT / "README.md").write_text(
        "# RWKV-LH Stage6 final balanced state tuning\n\n"
        "Stage6 restarts from Stage1, restores every Stage4 balanced boundary anchor, "
        "retains a calibrated one-third of Stage5 completion rows, and adds focused connector/web residuals.\n",
        encoding="utf-8",
    )
    files = {
        path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in sorted(OUTPUT.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "artifact_kind": "failure_grounded_final_balanced_state_tuning",
        "purpose": "Jointly recover Stage4 local-first boundaries and Stage5 stopping without pre-evidence over-completion.",
        "training_ready": False,
        "local_validation_complete": True,
        "remote_tokenizer_validated": False,
        "counts": {
            "train": len(train),
            "dev": len(dev),
            "train_semantic_families": len(train_families),
            "dev_semantic_families": len(dev_families),
            "train_clusters": dict(expected_train),
            "dev_clusters": dict(expected_dev),
        },
        "contamination": contamination,
        "source": {
            "stage1_manifest_sha256": sha256(STAGE1_DATA / "manifest.json"),
            "stage4_manifest_sha256": sha256(STAGE4_DATA / "manifest.json"),
            "stage5_manifest_sha256": sha256(STAGE5_DATA / "manifest.json"),
            "stage5_result_sha256": sha256(STAGE5_RESULT),
            "stage6_amendment_sha256": sha256(AMENDMENT),
        },
        "training_contract": {
            "training_file": "rwkv_state_tuning.train.requires_target_suffix.jsonl",
            "development_file": "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": 2496,
            "peft": "state",
            "op": "fla",
            "seed": 832,
            "lr_init": "5e-6",
            "lr_final": "1e-6",
            "parent": "stage1-step500",
            "final_step": 1300,
        },
        "files": files,
        "generation": f"uv run python {Path(__file__).resolve()}",
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"] | {"contamination": contamination}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
