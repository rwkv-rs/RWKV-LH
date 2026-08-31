"""Build Stage-2 routing-boundary state-tuning data from corrected live residuals."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.model_io import parse_tool_selection

from scripts import generate_rwkv_action_state_tuning_round1_2k_v1 as round1
from scripts import generate_rwkv_action_state_tuning_v1 as pilot


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage2_route_boundary_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_STATE_TUNING_THREE_STAGE_V1_20260826"
PREREGISTRATION = EXPERIMENT / "STAGE2_PREREGISTRATION.md"
RESIDUAL = (
    EXPERIMENT
    / "stage2_residual_discovery"
    / "ecra_route120_B_stage1_child_orientation_fixed"
    / "results.json"
)
VERSION = "rwkv-lh.state-tuning.stage2-route-boundary.v1"
VARIANTS = 4
FAMILY_COUNTS = {
    "train": {
        "structured_connector": 80,
        "general_web": 40,
        "mixed_local_first": 20,
        "privacy_local_first": 20,
    },
    "dev": {
        "structured_connector": 12,
        "general_web": 4,
        "mixed_local_first": 4,
        "privacy_local_first": 4,
    },
}
SIGNATURES = {
    "structured_connector": "FST-S2-001",
    "general_web": "FST-S2-002",
    "mixed_local_first": "FST-S2-003",
    "privacy_local_first": "FST-S2-004",
}
CONNECTOR_OPERATIONS = (
    "github_repository",
    "github_release",
    "github_commit",
    "github_code",
    "package_release",
    "scholarly_record",
    "weather",
    "weather_alerts",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def identity(split: str, cluster: str, family: int, variant: int) -> tuple[str, str]:
    code = {
        "structured_connector": "SC",
        "general_web": "GW",
        "mixed_local_first": "ML",
        "privacy_local_first": "PL",
    }[cluster]
    family_id = f"AST-S2-SF-{code}-{split.upper()}-{family + 1:04d}"
    trajectory_id = f"AST-S2-{code}-{split.upper()}-{family + 1:04d}-{variant + 1:02d}"
    return family_id, trajectory_id


def connector_query(operation: str, family: int, variant: int) -> str:
    nonce = f"{family + 71:04d}-{variant + 31:02d}"
    return {
        "github_repository": f"aurora-sim-{nonce}/quartz-index-{variant + 2}",
        "github_release": f"lattice-lab-{nonce}/harbor-engine-{family % 17 + 3}",
        "github_commit": f"ember-org-{nonce}/signal-core@{hashlib.sha256(nonce.encode()).hexdigest()[:12]}",
        "github_code": f"violet-group-{nonce}/archive-kit:src/marker-{variant + 1}.py",
        "package_release": (
            "pypi" if family % 3 == 0 else "npm" if family % 3 == 1 else "crates"
        )
        + f":synthetic-route-{nonce}",
        "scholarly_record": f"10.9999/synthetic.route.{nonce}",
        "weather": f"Fictional Cedar Basin {nonce}",
        "weather_alerts": f"Synthetic Amber District {nonce}",
    }[operation]


def connector_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    operation = CONNECTOR_OPERATIONS[(family * VARIANTS + variant) % len(CONNECTOR_OPERATIONS)]
    query = connector_query(operation, family + (0 if split == "train" else 10000), variant)
    language = "zh" if variant % 2 == 0 else "en"
    subject = {
        "github_repository": ("精确代码仓库元数据", "exact repository metadata"),
        "github_release": ("精确仓库发布记录", "exact repository release record"),
        "github_commit": ("精确提交记录", "exact commit record"),
        "github_code": ("精确仓库文件记录", "exact repository file record"),
        "package_release": ("生态系统包发布记录", "ecosystem package release record"),
        "scholarly_record": ("标识符对应的论文记录", "scholarly identifier record"),
        "weather": ("结构化天气观测", "structured weather observation"),
        "weather_alerts": ("结构化天气预警", "structured weather alert"),
    }[operation]
    if language == "zh":
        request = (
            f"本轮只需要查询虚构公开标识 `{query}` 的{subject[0]}。标识和记录类型均已明确，"
            "应选择结构化 connector source；不要把它降级为一般网页搜索。"
        )
    else:
        request = (
            f"This turn requires the {subject[1]} for fictional public identifier `{query}`. "
            "Both identifier and record type are explicit, so select the structured connector "
            "source rather than general web search."
        )
    semantic_family_id, trajectory_id = identity(
        split, "structured_connector", family, variant
    )
    return {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": trajectory_id,
        "source_seed_id": "ST-ACT-005",
        "semantic_family_id": semantic_family_id,
        "split": split,
        "language": language,
        "network_policy": "auto_public",
        "request": request,
        "workspace_files": [],
        "turns": [
            pilot._turn(
                "connector_lookup", {"operation": operation, "query": query}, "initial"
            )
        ],
        "prelude": [],
        "expected_backend_executions": 1,
        "private_oracle_digest": "",
    }


def web_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    slot = family + (0 if split == "train" else 10000)
    topic = (
        "community greenhouse notice",
        "public venue hours page",
        "vendor support bulletin",
        "hosted service incident page",
        "general documentation guide",
        "public event announcement",
    )[family % 6]
    query = f"Fictional {topic} slate-{slot + 41}-{variant + 9}"
    language = "zh" if variant % 2 == 0 else "en"
    if language == "zh":
        request = (
            f"从一般公共网页查找 `{query}`。没有仓库、包名、DOI、结构化天气地区或其他精确"
            "登记标识；使用 web source，不要虚构 connector 类型。"
        )
    else:
        request = (
            f"Find `{query}` on ordinary public pages. No repository, package, DOI, structured "
            "weather region, or other exact registry identifier is supplied; use a web source "
            "and do not invent a connector type."
        )
    semantic_family_id, trajectory_id = identity(split, "general_web", family, variant)
    return {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": trajectory_id,
        "source_seed_id": "ST-ACT-004",
        "semantic_family_id": semantic_family_id,
        "split": split,
        "language": language,
        "network_policy": "auto_public",
        "request": request,
        "workspace_files": [],
        "turns": [
            pilot._turn("web_search", {"query": query, "max_results": 5}, "initial")
        ],
        "prelude": [],
        "expected_backend_executions": 1,
        "private_oracle_digest": "",
    }


def inherited_candidate(
    split: str, cluster: str, family: int, variant: int
) -> dict[str, Any]:
    if cluster == "mixed_local_first":
        seed = "ST-ACT-011" if family % 2 == 0 else "ST-ACT-012"
    else:
        seed = "ST-ACT-013" if family % 2 == 0 else "ST-ACT-014"
    group = family + (300 if split == "train" else 10300)
    candidate = pilot._instantiate(seed, group, variant)
    semantic_family_id, trajectory_id = identity(split, cluster, family, variant)
    candidate.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": semantic_family_id,
            "split": split,
            "private_oracle_digest": "",
        }
    )
    return candidate


def candidates() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split, counts in FAMILY_COUNTS.items():
        for cluster, family_count in counts.items():
            for family in range(family_count):
                for variant in range(VARIANTS):
                    if cluster == "structured_connector":
                        row = connector_candidate(split, family, variant)
                    elif cluster == "general_web":
                        row = web_candidate(split, family, variant)
                    else:
                        row = inherited_candidate(split, cluster, family, variant)
                    row["failure_cluster"] = cluster
                    row["failure_signature_id"] = SIGNATURES[cluster]
                    rows.append(row)
    return rows


def selected_stage(candidate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    positive, validation, _rejected = pilot._replay(candidate)
    matches = [
        dict(row)
        for row in positive
        if row["stage"] == "selector" and int(row["turn_index"]) == 0
    ]
    if len(matches) != 1:
        raise RuntimeError(f"selector boundary missing: {candidate['trajectory_id']}")
    row = matches[0]
    if parse_tool_selection(str(row["target"])) != row["target_operation"]:
        raise RuntimeError(f"selector target failed: {candidate['trajectory_id']}")
    row.update(
        {
            "schema_version": "rwkv-lh.failure-grounded-action-stage-sft.v1",
            "failure_cluster": candidate["failure_cluster"],
            "failure_signature_id": candidate["failure_signature_id"],
            "target_reason": (
                "distinguish structured connectors from general public web"
                if candidate["failure_cluster"]
                in {"structured_connector", "general_web"}
                else "observe the local dependency before any downstream route"
            ),
            "training_intent": "correct_live_route_boundary_not_generic_task_sft",
        }
    )
    return row, validation


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    if not PREREGISTRATION.is_file() or not RESIDUAL.is_file():
        raise RuntimeError("Stage-2 preregistration or corrected residual is missing")
    residual = json.loads(RESIDUAL.read_text(encoding="utf-8"))
    metrics = residual["metrics"]
    if metrics["web_connector_f1_by_class"]["connector_lookup"] != 0.0:
        raise RuntimeError("corrected connector residual changed")
    if metrics["network_decision_macro_f1"] < 0.9:
        raise RuntimeError("Stage-2 must not mask a general network-decision failure")

    source_candidates = candidates()
    expected_total = sum(
        sum(value.values()) * VARIANTS for value in FAMILY_COUNTS.values()
    )
    if len(source_candidates) != expected_total or expected_total != 736:
        raise RuntimeError(f"candidate count changed: {len(source_candidates)}")
    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    for index, candidate in enumerate(source_candidates, 1):
        stage, validation = selected_stage(candidate)
        stages.append(stage)
        validations.append(
            {
                "trajectory_id": candidate["trajectory_id"],
                "failure_cluster": candidate["failure_cluster"],
                **validation,
            }
        )
        if index % 80 == 0:
            print(f"controller replay {index}/{expected_total}", flush=True)

    train = [row for row in stages if row["split"] == "train"]
    dev = [row for row in stages if row["split"] == "dev"]
    if len(train) != 640 or len(dev) != 96:
        raise RuntimeError(f"split count changed: train={len(train)} dev={len(dev)}")
    expected_train = {
        cluster: families * VARIANTS
        for cluster, families in FAMILY_COUNTS["train"].items()
    }
    expected_dev = {
        cluster: families * VARIANTS
        for cluster, families in FAMILY_COUNTS["dev"].items()
    }
    if Counter(row["failure_cluster"] for row in train) != Counter(expected_train):
        raise RuntimeError("train cluster quota changed")
    if Counter(row["failure_cluster"] for row in dev) != Counter(expected_dev):
        raise RuntimeError("dev cluster quota changed")
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    if train_families & dev_families:
        raise RuntimeError("semantic family crosses train/dev")
    texts = [row["text"] for row in stages]
    prompts = [row["prompt"] for row in stages]
    if len(texts) != len(set(texts)) or len(prompts) != len(set(prompts)):
        raise RuntimeError("exact stage duplicate detected")
    contamination = round1._holdout_contamination(source_candidates)
    if any(int(row.get("backend_execution_count", 0)) for row in validations if row["failure_cluster"] == "privacy_local_first"):
        raise RuntimeError("privacy fixture reached the frozen backend")

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
    write_jsonl(OUTPUT / "validation.jsonl", validations)
    write_json(
        OUTPUT / "hard_negative_registry.json",
        {
            "schema_version": "rwkv-lh.route-boundary-hard-negatives.v1",
            "observed_live_residual": str(RESIDUAL.relative_to(ROOT)),
            "transition_counts": {
                "connector_lookup->web_search": 19,
                "connector_lookup->no_action": 1,
                "mixed_local_first_wrong_or_missing": 19,
            },
            "negative_rules": [
                "general web is negative when an exact structured identifier and record type are present",
                "a downstream network or deterministic tool is negative before its local dependency is observed",
            ],
        },
    )
    (OUTPUT / "README.md").write_text(
        "# RWKV-LH Stage 2 route-boundary state tuning\n\n"
        "640 train and 96 dev selector boundaries target corrected live connector/web "
        "and local-first residuals. They are Controller-rendered synthetic transitions, "
        "not ECRA questions or generic task answers. Training requires target_suffix and BOS 0.\n",
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
        "artifact_kind": "corrected_live_residual_route_boundary_state_tuning",
        "purpose": "Correct structured-connector/web and local-dependency ordering residuals without task-answer SFT.",
        "training_ready": False,
        "local_validation_complete": True,
        "remote_tokenizer_validated": False,
        "controller_replay": True,
        "strong_model_as_label_source": False,
        "live_network_used": False,
        "loss_mask": "target_suffix",
        "bos_token_id": 0,
        "counts": {
            "train": len(train),
            "dev": len(dev),
            "train_semantic_families": len(train_families),
            "dev_semantic_families": len(dev_families),
        },
        "cluster_counts": {"train": expected_train, "dev": expected_dev},
        "target_operation_counts": {
            "train": dict(sorted(Counter(row["target_operation"] for row in train).items())),
            "dev": dict(sorted(Counter(row["target_operation"] for row in dev).items())),
        },
        "validation": {
            "controller_replay_rate": 1.0,
            "target_parse_rate": 1.0,
            "exact_prompt_duplicate_count": 0,
            "train_dev_family_overlap_count": 0,
            "privacy_backend_execution_count": 0,
            "contamination": contamination,
        },
        "parent": {
            "state_checkpoint_sha256": "180fb98e70144d2d078bc3f9c43778c0d7011627c6b5446cfa7783041afd04f8",
            "corrected_residual": str(RESIDUAL.relative_to(ROOT)),
            "corrected_residual_sha256": sha256(RESIDUAL),
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": sha256(PREREGISTRATION),
        },
        "generation": "uv run python scripts/generate_rwkv_state_tuning_stage2_route_boundary_v1.py",
        "files": files,
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
