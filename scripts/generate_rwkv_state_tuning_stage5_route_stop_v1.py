"""Build Stage5 route-counterfactual and completion-boundary data."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.model_io import parse_tool_selection

from scripts import generate_rwkv_action_state_tuning_round1_2k_v1 as round1
from scripts import generate_rwkv_action_state_tuning_v1 as pilot
from scripts import generate_rwkv_state_tuning_stage3_natural_route_stop_v1 as stage3
from scripts import generate_rwkv_state_tuning_stage4_balanced_boundary_v1 as stage4


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage5_route_stop_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_STATE_TUNING_STAGE4_TO_STAGE6_V1_20260827"
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
STAGE4_RESULT = EXPERIMENT / "STAGE4_RESULT.md"
STAGE4_DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage4_balanced_boundary_v1"
STAGE1_DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1"
VERSION = "rwkv-lh.state-tuning.stage5-route-stop.v1"
VARIANTS = 4
SIGNATURES = {
    "stable_selector_replay": "FST-S5-001",
    "connector_anchor": "FST-S5-002",
    "github_connector_residual": "FST-S5-003",
    "ordinary_web_counterfactual": "FST-S5-004",
    "local_safety_anchor": "FST-S5-005",
    "mixed_local_first_anchor": "FST-S5-006",
    "privacy_local_first_anchor": "FST-S5-007",
    "completion_after_success": "FST-S5-008",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def immutable_request(prompt: str) -> str:
    marker = "User: Task state: "
    start = prompt.index(marker) + len(marker)
    state, _end = json.JSONDecoder().raw_decode(prompt[start:])
    return str(state["immutable_request"])


def remap_row(
    row: Mapping[str, Any], cluster: str, index: int, *, source_cluster: str
) -> dict[str, Any]:
    item = dict(row)
    item["source_failure_cluster"] = source_cluster
    item["failure_cluster"] = cluster
    item["failure_signature_id"] = SIGNATURES[cluster]
    item["semantic_family_id"] = f"AST-S5-SF-ANCHOR-{cluster.upper()}-{index + 1:04d}"
    item["training_intent"] = "retain_stage4_effective_boundary_as_stage5_anchor"
    return item


def stage4_anchors() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = read_jsonl(STAGE4_DATA / "stage_sft.train.jsonl")
    by_cluster: dict[str, list[dict[str, Any]]] = {}
    for row in source:
        by_cluster.setdefault(str(row["failure_cluster"]), []).append(row)
    quotas = {
        "natural_connector_paired": ("connector_anchor", 80),
        "ordinary_web_hard_negative": ("ordinary_web_counterfactual", 160),
        "local_only_network_hard_negative": ("local_safety_anchor", 80),
        "mixed_local_first_natural": ("mixed_local_first_anchor", 80),
        "privacy_local_first_natural": ("privacy_local_first_anchor", 40),
    }
    result: list[dict[str, Any]] = []
    contamination: list[dict[str, Any]] = []
    for source_cluster, (target_cluster, quota) in quotas.items():
        rows = by_cluster[source_cluster]
        if len(rows) < quota:
            raise RuntimeError(f"Stage4 anchor shortage: {source_cluster}")
        # Evenly span the source cluster rather than taking one surface block.
        selected = [rows[(index * len(rows)) // quota] for index in range(quota)]
        if len({row["prompt_sha256"] for row in selected}) != quota:
            raise RuntimeError(f"Stage4 anchor selection duplicated: {source_cluster}")
        for index, row in enumerate(selected):
            item = remap_row(row, target_cluster, index, source_cluster=source_cluster)
            result.append(item)
            contamination.append(
                {
                    "trajectory_id": f"S5-ANCHOR-{target_cluster}-{index + 1:04d}",
                    "request": immutable_request(str(item["prompt"])),
                }
            )
    return result, contamination


def stable_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, contamination = stage3.stable_rows()
    for row in rows:
        row["failure_signature_id"] = SIGNATURES["stable_selector_replay"]
        row["training_intent"] = "preserve_stage1_selector_safety_and_stopping"
    return rows, contamination


def new_identity(
    split: str, cluster: str, family: int, variant: int
) -> tuple[str, str]:
    code = {
        "github_connector_residual": "GC",
        "ordinary_web_counterfactual": "OW",
        "local_safety_anchor": "LO",
        "mixed_local_first_anchor": "ML",
        "privacy_local_first_anchor": "PL",
        "completion_after_success": "CS",
    }[cluster]
    family_id = f"AST-S5-SF-{code}-{split.upper()}-{family + 1:04d}"
    trajectory_id = f"AST-S5-{code}-{split.upper()}-{family + 1:04d}-{variant + 1:02d}"
    return family_id, trajectory_id


def remap_candidate(
    row: dict[str, Any], split: str, cluster: str, family: int, variant: int
) -> dict[str, Any]:
    semantic_family_id, trajectory_id = new_identity(split, cluster, family, variant)
    row.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": semantic_family_id,
            "split": split,
            "failure_cluster": cluster,
            "failure_signature_id": SIGNATURES[cluster],
        }
    )
    return row


def focused_connector_candidate(
    split: str, family: int, variant: int
) -> dict[str, Any]:
    operations = (
        "github_repository",
        "github_release",
        "github_commit",
        "github_code",
        "github_repository",
        "github_code",
        "package_release",
        "scholarly_record",
        "weather",
        "weather_alerts",
    )
    operation = operations[family % len(operations)]
    source_family = family + (2200 if split == "train" else 32200)
    query = stage3.connector_query(operation, split, source_family, variant)
    language = "zh" if variant % 2 == 0 else "en"
    row = {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": "",
        "source_seed_id": "ST-S5-CONNECTOR",
        "semantic_family_id": "",
        "split": split,
        "language": language,
        "network_policy": "auto_public",
        "request": stage3.connector_request(operation, query, language, variant),
        "workspace_files": [],
        "turns": [pilot._turn("connector_lookup", {"operation": operation, "query": query}, "initial")],
        "prelude": [],
        "expected_backend_executions": 1,
        "private_oracle_digest": "",
    }
    return remap_candidate(row, split, "github_connector_residual", family, variant)


def web_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    # Offset the Stage4 factory so no Stage4 train/dev semantic family or query is reused.
    source_family = family + (2600 if split == "train" else 32600)
    row = stage4.web_candidate(split, source_family, variant)
    return remap_candidate(row, split, "ordinary_web_counterfactual", family, variant)


def dev_anchor_candidate(
    split: str, cluster: str, family: int, variant: int
) -> dict[str, Any]:
    source_family = family + {
        "local_safety_anchor": 33000,
        "mixed_local_first_anchor": 34000,
        "privacy_local_first_anchor": 35000,
    }[cluster]
    if cluster == "local_safety_anchor":
        row = stage4.local_candidate(split, source_family, variant)
    elif cluster == "mixed_local_first_anchor":
        row = stage4.mixed_candidate(split, source_family, variant)
    else:
        row = stage4.privacy_candidate(split, source_family, variant)
    return remap_candidate(row, split, cluster, family, variant)


def completion_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    seeds = (
        "ST-ACT-001",
        "ST-ACT-002",
        "ST-ACT-003",
        "ST-ACT-008",
        "ST-ACT-009",
        "ST-ACT-010",
        "ST-ACT-011",
        "ST-ACT-012",
        "ST-ACT-013",
        "ST-ACT-014",
        "ST-ACT-018",
        "ST-ACT-019",
        "CUSTOM-DIGEST",
    )
    seed = seeds[family % len(seeds)]
    # Keep inherited date fixtures within Python's four-digit ISO range while
    # remaining disjoint from the Stage1 source families (0..5).
    group = family + (100 if split == "train" else 500)
    language = "zh" if variant % 2 == 0 else "en"
    if seed.startswith("ST-ACT"):
        row = pilot._instantiate(seed, group, variant)
    else:
        row = {
            "schema_version": pilot.CANDIDATE_SCHEMA,
            "trajectory_id": "",
            "source_seed_id": "ST-S5-COMPLETION",
            "semantic_family_id": "",
            "split": split,
            "language": language,
            "network_policy": "offline",
            "request": "",
            "workspace_files": [],
            "turns": [],
            "prelude": [],
            "expected_backend_executions": 0,
            "private_oracle_digest": "",
        }
        nonce = f"{group + 1:05d}-{variant + 1:02d}"
        path = f"completion/evidence-{nonce}.txt"
        row["workspace_files"] = [
            pilot._workspace_file(path, f"zero\none {nonce}\ntwo {nonce}\n")
        ]
        if seed == "CUSTOM-DIGEST":
            row["request"] = (
                f"计算 `{path}` 的本地摘要并报告。"
                if language == "zh"
                else f"Calculate the local digest of `{path}` and report it."
            )
            row["turns"] = [pilot._turn("file_digest", {"path": path}, "initial")]
    summary = (
        f"所需观察已经成功完成并记录，批次 {group + 1}-{variant + 1}。"
        if language == "zh"
        else f"The required observation completed successfully and was recorded for batch {group + 1}-{variant + 1}."
    )
    if row["turns"][-1]["target_operation"] != "final_answer":
        row["turns"].append(
            pilot._turn("final_answer", {"text": summary}, "after_required_evidence")
        )
    return remap_candidate(row, split, "completion_after_success", family, variant)


def selected_initial_stage(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    positive, validation, _rejected = pilot._replay(candidate)
    matches = [
        dict(row)
        for row in positive
        if row["stage"] == "selector" and int(row["turn_index"]) == 0
    ]
    if len(matches) != 1:
        raise RuntimeError(f"initial selector missing: {candidate['trajectory_id']}")
    return decorate(matches[0], candidate, "counterfactual_route_or_safety_anchor"), validation


def selected_completion_stage(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    positive, validation, _rejected = pilot._replay(candidate)
    matches = [
        dict(row)
        for row in positive
        if row["stage"] == "selector" and row["target_operation"] == "final_answer"
    ]
    if len(matches) != 1:
        raise RuntimeError(f"completion selector missing: {candidate['trajectory_id']}")
    return decorate(matches[0], candidate, "stop_after_sufficient_tool_evidence"), validation


def decorate(
    row: dict[str, Any], candidate: Mapping[str, Any], intent: str
) -> dict[str, Any]:
    if parse_tool_selection(str(row["target"])) != row["target_operation"]:
        raise RuntimeError(f"selector target failed: {candidate['trajectory_id']}")
    row.update(
        {
            "schema_version": "rwkv-lh.failure-grounded-action-stage-sft.v1",
            "failure_cluster": candidate["failure_cluster"],
            "failure_signature_id": candidate["failure_signature_id"],
            "training_intent": intent,
        }
    )
    return row


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    if not PREREGISTRATION.is_file() or not STAGE4_RESULT.is_file():
        raise RuntimeError("Stage5 preregistration or Stage4 result is missing")

    stable, stable_contamination = stable_rows()
    anchors, anchor_contamination = stage4_anchors()
    candidates: list[tuple[dict[str, Any], bool]] = []
    # New train residual: 10 focused families x 4 = 40 connector selectors.
    for family in range(10):
        for variant in range(VARIANTS):
            candidates.append((focused_connector_candidate("train", family, variant), False))
    # Completion residual: 60 train families x 4 = 240.
    for family in range(60):
        for variant in range(VARIANTS):
            candidates.append((completion_candidate("train", family, variant), True))

    # Family-disjoint dev240.
    for family in range(12):
        for variant in range(VARIANTS):
            candidates.append((focused_connector_candidate("dev", family, variant), False))
            candidates.append((web_candidate("dev", family, variant), False))
    for cluster, families in (
        ("local_safety_anchor", 8),
        ("mixed_local_first_anchor", 8),
        ("privacy_local_first_anchor", 4),
    ):
        for family in range(families):
            for variant in range(VARIANTS):
                candidates.append((dev_anchor_candidate("dev", cluster, family, variant), False))
    for family in range(16):
        for variant in range(VARIANTS):
            candidates.append((completion_candidate("dev", family, variant), True))

    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    raw_candidates: list[dict[str, Any]] = []
    for index, (candidate, completion) in enumerate(candidates, 1):
        raw_candidates.append(candidate)
        try:
            stage, validation = (
                selected_completion_stage(candidate)
                if completion
                else selected_initial_stage(candidate)
            )
        except Exception as exc:
            raise RuntimeError(
                f"Stage5 replay failed at {index}/{len(candidates)} for "
                f"{candidate['trajectory_id']} ({candidate['failure_cluster']})"
            ) from exc
        stages.append(stage)
        validations.append(
            {
                "trajectory_id": candidate["trajectory_id"],
                "failure_cluster": candidate["failure_cluster"],
                **validation,
            }
        )
        if index % 100 == 0:
            print(f"controller replay {index}/{len(candidates)}", flush=True)

    train = [*stable, *anchors, *(row for row in stages if row["split"] == "train")]
    dev = [row for row in stages if row["split"] == "dev"]
    expected_train = Counter(
        {
            "stable_selector_replay": 500,
            "connector_anchor": 80,
            "github_connector_residual": 40,
            "ordinary_web_counterfactual": 160,
            "local_safety_anchor": 80,
            "mixed_local_first_anchor": 80,
            "privacy_local_first_anchor": 40,
            "completion_after_success": 240,
        }
    )
    expected_dev = Counter(
        {
            "github_connector_residual": 48,
            "ordinary_web_counterfactual": 48,
            "local_safety_anchor": 32,
            "mixed_local_first_anchor": 32,
            "privacy_local_first_anchor": 16,
            "completion_after_success": 64,
        }
    )
    if Counter(row["failure_cluster"] for row in train) != expected_train:
        raise RuntimeError("Stage5 train quota changed")
    if Counter(row["failure_cluster"] for row in dev) != expected_dev:
        raise RuntimeError("Stage5 dev quota changed")
    if len(train) != 1220 or len(dev) != 240:
        raise RuntimeError(f"Stage5 split count changed: {len(train)}, {len(dev)}")
    if len({row["text"] for row in [*train, *dev]}) != len(train) + len(dev):
        raise RuntimeError("Stage5 exact stage duplicate detected")
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    if train_families & dev_families:
        raise RuntimeError("Stage5 semantic family crosses train/dev")
    contamination = round1._holdout_contamination(
        [*stable_contamination, *anchor_contamination, *raw_candidates]
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
            "schema_version": "rwkv-lh.stage5-residuals.v1",
            "source": "Stage4 frozen ECRA120",
            "selected_residual_families": {
                "completion_after_success": "failed/interrupted 9 > 4",
                "web_connector_confusion": "public-web 22/25 and connector 11/20",
            },
            "retained_anchors": {
                "mixed_local_first": "17/20",
                "privacy_local_first": "9/10",
                "local_network_fp": 0,
                "network_macro_f1": 0.9742101869761444,
            },
        },
    )
    (OUTPUT / "README.md").write_text(
        "# RWKV-LH Stage5 route + stop state tuning\n\n"
        "Stage5 restarts from Stage1. It retains the effective balanced Stage4 anchors, "
        "adds focused GitHub connector counterfactuals, and directly supervises final_answer "
        "selectors after sufficient real tool evidence.\n",
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
        "artifact_kind": "failure_grounded_route_counterfactual_and_completion_state_tuning",
        "purpose": "Correct Stage4 web/connector and stopping residuals while retaining its safe local-first boundary.",
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
            "stage4_result_sha256": sha256(STAGE4_RESULT),
            "preregistration_sha256": sha256(PREREGISTRATION),
        },
        "training_contract": {
            "training_file": "rwkv_state_tuning.train.requires_target_suffix.jsonl",
            "development_file": "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": 2496,
            "peft": "state",
            "op": "fla",
            "seed": 831,
            "lr_init": "7e-6",
            "lr_final": "1.4e-6",
            "parent": "stage1-step500",
        },
        "files": files,
        "generation": f"uv run python {Path(__file__).resolve()}",
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"] | {"contamination": contamination}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
