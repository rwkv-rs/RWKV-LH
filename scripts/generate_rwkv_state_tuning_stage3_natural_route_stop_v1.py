"""Build Stage-3 natural-route and stopping-boundary state-tuning data."""

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
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage3_natural_route_stop_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_STATE_TUNING_THREE_STAGE_V1_20260826"
PREREGISTRATION = EXPERIMENT / "STAGE3_PREREGISTRATION.md"
STAGE2_RESULT = EXPERIMENT / "STAGE2_RESULT.md"
STAGE1 = ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1"
VERSION = "rwkv-lh.state-tuning.stage3-natural-route-stop.v1"
VARIANTS = 4
NEW_FAMILY_COUNTS = {
    "train": {
        "natural_connector": 100,
        "ordinary_web": 25,
        "mixed_local_first": 50,
        "privacy_local_first": 50,
    },
    "dev": {
        "natural_connector": 16,
        "ordinary_web": 4,
        "mixed_local_first": 12,
        "privacy_local_first": 12,
    },
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
SIGNATURES = {
    "stable_selector_replay": "FST-S3-001",
    "natural_connector": "FST-S3-002",
    "ordinary_web": "FST-S3-003",
    "mixed_local_first": "FST-S3-004",
    "privacy_local_first": "FST-S3-005",
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


def identity(split: str, cluster: str, family: int, variant: int) -> tuple[str, str]:
    code = {
        "natural_connector": "NC",
        "ordinary_web": "OW",
        "mixed_local_first": "ML",
        "privacy_local_first": "PL",
    }[cluster]
    family_id = f"AST-S3-SF-{code}-{split.upper()}-{family + 1:04d}"
    trajectory_id = f"AST-S3-{code}-{split.upper()}-{family + 1:04d}-{variant + 1:02d}"
    return family_id, trajectory_id


def connector_query(operation: str, split: str, family: int, variant: int) -> str:
    offset = family + (0 if split == "train" else 20000)
    nonce = f"{offset + 901:05d}-{variant + 17:02d}"
    return {
        "github_repository": f"northstar-{nonce}/quartz-ledger-{offset % 29 + 3}",
        "github_release": f"mariner-{nonce}/signal-engine-{offset % 31 + 5}",
        "github_commit": (
            f"willow-{nonce}/archive-core@"
            f"{hashlib.sha256(nonce.encode()).hexdigest()[:12]}"
        ),
        "github_code": f"violet-{nonce}/index-kit:src/record_{variant + 1}.py",
        "package_release": (
            ("pypi", "npm", "crates")[offset % 3]
            + f":synthetic-natural-{nonce}"
        ),
        "scholarly_record": f"10.9999/natural.route.{nonce}",
        "weather": f"Fictional Juniper Basin {nonce}",
        "weather_alerts": f"Synthetic Copper Coast {nonce}",
    }[operation]


def connector_request(operation: str, query: str, language: str, variant: int) -> str:
    zh = {
        "github_repository": (
            f"查出 GitHub 仓库 `{query}` 的默认分支、许可证字段和公开描述。",
            f"给我 `{query}` 这个 GitHub 项目的仓库元数据，包括默认分支与 license。",
        ),
        "github_release": (
            f"读取 GitHub 项目 `{query}` 最新 release 的 tag、名称与发布时间。",
            f"确认仓库 `{query}` 当前最近一次正式发布的版本标签和发布日期。",
        ),
        "github_commit": (
            f"返回 GitHub 标识 `{query}` 对应提交的作者、时间和完整摘要字段。",
            f"核对 `{query}` 这条明确 commit 的公开元数据与父提交列表。",
        ),
        "github_code": (
            f"读取 GitHub 精确文件标识 `{query}` 的公开内容与 blob 元数据。",
            f"从仓库路径 `{query}` 取得该文件记录，不需要浏览其他页面。",
        ),
        "package_release": (
            f"查询软件包 `{query}` 当前稳定版本、发布时间与发布摘要。",
            f"核对精确包标识 `{query}` 的最新发行记录和版本字段。",
        ),
        "scholarly_record": (
            f"解析论文标识 `{query}`，返回标题、作者与正式发布日期。",
            f"按学术标识 `{query}` 核对期刊、作者列表和出版时间。",
        ),
        "weather": (
            f"取得地区 `{query}` 的当前天气观测、温度和观测时间。",
            f"返回 `{query}` 接下来三天的结构化天气数据和更新时间。",
        ),
        "weather_alerts": (
            f"检查地区 `{query}` 当前生效的官方天气预警及有效期。",
            f"列出 `{query}` 尚未解除的严重天气警报和签发时间。",
        ),
    }
    en = {
        "github_repository": (
            f"Return the default branch, license field, and public description for GitHub repository `{query}`.",
            f"Inspect repository metadata for the exact GitHub project `{query}`, including its default branch and license.",
        ),
        "github_release": (
            f"Get the tag, title, and publication time of the latest GitHub release for `{query}`.",
            f"Identify the most recent formal release and release date for repository `{query}`.",
        ),
        "github_commit": (
            f"Retrieve author, timestamp, parents, and summary metadata for exact GitHub commit `{query}`.",
            f"Resolve the named commit `{query}` and report its public commit record.",
        ),
        "github_code": (
            f"Read the public file record and blob metadata for exact GitHub path `{query}`.",
            f"Retrieve the repository file identified by `{query}` and return its recorded content.",
        ),
        "package_release": (
            f"Look up the stable version, release time, and release metadata for package `{query}`.",
            f"Resolve exact package identifier `{query}` and report its latest published version fields.",
        ),
        "scholarly_record": (
            f"Resolve scholarly identifier `{query}` and return title, authors, venue, and publication date.",
            f"Look up the academic record identified by `{query}`, including journal and author metadata.",
        ),
        "weather": (
            f"Retrieve current observations, temperature, and observation time for region `{query}`.",
            f"Return the next three days of recorded forecast data for `{query}` with its update time.",
        ),
        "weather_alerts": (
            f"Retrieve active official weather alerts and validity windows for region `{query}`.",
            f"List unresolved severe-weather warnings and issue times for `{query}`.",
        ),
    }
    options = zh[operation] if language == "zh" else en[operation]
    return options[(variant // 2) % len(options)]


def connector_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    operation = CONNECTOR_OPERATIONS[family % len(CONNECTOR_OPERATIONS)]
    query = connector_query(operation, split, family, variant)
    language = "zh" if variant % 2 == 0 else "en"
    semantic_family_id, trajectory_id = identity(
        split, "natural_connector", family, variant
    )
    return {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": trajectory_id,
        "source_seed_id": "ST-ACT-005",
        "semantic_family_id": semantic_family_id,
        "split": split,
        "language": language,
        "network_policy": "auto_public",
        "request": connector_request(operation, query, language, variant),
        "workspace_files": [],
        "turns": [
            pilot._turn(
                "connector_lookup", {"operation": operation, "query": query}, "initial"
            )
        ],
        "prelude": [],
        "expected_backend_executions": 1,
        "private_oracle_digest": "",
        "failure_cluster": "natural_connector",
        "failure_signature_id": SIGNATURES["natural_connector"],
    }


def web_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    offset = family + (0 if split == "train" else 20000)
    subjects = (
        "community greenhouse visiting notice",
        "local arts venue opening-hours page",
        "vendor support announcement",
        "public transit maintenance bulletin",
        "neighborhood event schedule",
    )
    query = f"Fictional {subjects[family % len(subjects)]} slate-{offset + 71}-{variant + 9}"
    language = "zh" if variant % 2 == 0 else "en"
    request = (
        f"从普通公开页面查找 `{query}` 的当前公告并给出页面来源。"
        if language == "zh"
        else f"Find the current announcement for `{query}` on ordinary public pages and cite the page source."
    )
    semantic_family_id, trajectory_id = identity(split, "ordinary_web", family, variant)
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
        "turns": [pilot._turn("web_search", {"query": query, "max_results": 5}, "initial")],
        "prelude": [],
        "expected_backend_executions": 1,
        "private_oracle_digest": "",
        "failure_cluster": "ordinary_web",
        "failure_signature_id": SIGNATURES["ordinary_web"],
    }


def inherited_candidate(
    split: str, cluster: str, family: int, variant: int
) -> dict[str, Any]:
    if cluster == "mixed_local_first":
        seed = "ST-ACT-011" if family % 2 == 0 else "ST-ACT-012"
        group = family + (900 if split == "train" else 20900)
    else:
        seed = "ST-ACT-013" if family % 2 == 0 else "ST-ACT-014"
        group = family + (1100 if split == "train" else 21100)
    candidate = pilot._instantiate(seed, group, variant)
    semantic_family_id, trajectory_id = identity(split, cluster, family, variant)
    candidate.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": semantic_family_id,
            "split": split,
            "private_oracle_digest": "",
            "failure_cluster": cluster,
            "failure_signature_id": SIGNATURES[cluster],
        }
    )
    return candidate


def new_candidates() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for split, counts in NEW_FAMILY_COUNTS.items():
        for cluster, family_count in counts.items():
            for family in range(family_count):
                for variant in range(VARIANTS):
                    if cluster == "natural_connector":
                        row = connector_candidate(split, family, variant)
                    elif cluster == "ordinary_web":
                        row = web_candidate(split, family, variant)
                    else:
                        row = inherited_candidate(split, cluster, family, variant)
                    result.append(row)
    return result


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
            "training_intent": "natural_route_transfer_without_answer_label_shortcut",
        }
    )
    return row, validation


def stable_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = read_jsonl(STAGE1 / "stage_sft.train.jsonl")
    if len(rows) != 500 or any(row["stage"] != "selector" for row in rows):
        raise RuntimeError("Stage1 stable selector source changed")
    decoder = json.JSONDecoder()
    contamination_candidates: list[dict[str, Any]] = []
    result: list[dict[str, Any]] = []
    marker = "User: Task state: "
    for row in rows:
        item = dict(row)
        item["source_failure_cluster"] = item["failure_cluster"]
        item["failure_cluster"] = "stable_selector_replay"
        item["failure_signature_id"] = SIGNATURES["stable_selector_replay"]
        item["training_intent"] = "preserve_stage1_selector_and_completion_boundaries"
        if parse_tool_selection(str(item["target"])) != item["target_operation"]:
            raise RuntimeError(f"stable selector target changed: {item['trajectory_id']}")
        start = str(item["prompt"]).find(marker)
        if start < 0:
            raise RuntimeError(f"stable prompt lacks task state: {item['trajectory_id']}")
        task_state, _end = decoder.raw_decode(str(item["prompt"])[start + len(marker) :])
        contamination_candidates.append(
            {
                "trajectory_id": item["trajectory_id"],
                "request": task_state["immutable_request"],
            }
        )
        result.append(item)
    return result, contamination_candidates


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    if not PREREGISTRATION.is_file() or not STAGE2_RESULT.is_file():
        raise RuntimeError("Stage3 preregistration/result evidence is missing")
    source_manifest = json.loads((STAGE1 / "manifest.json").read_text(encoding="utf-8"))
    if source_manifest["counts"]["train"] != 500:
        raise RuntimeError("Stage1 source manifest changed")

    stable, stable_contamination = stable_rows()
    candidates = new_candidates()
    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, 1):
        stage, validation = selected_stage(candidate)
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

    train = [*stable, *(row for row in stages if row["split"] == "train")]
    dev = [row for row in stages if row["split"] == "dev"]
    if len(train) != 1400 or len(dev) != 176:
        raise RuntimeError(f"split count changed: train={len(train)} dev={len(dev)}")
    expected_train = Counter(
        {
            "stable_selector_replay": 500,
            "natural_connector": 400,
            "ordinary_web": 100,
            "mixed_local_first": 200,
            "privacy_local_first": 200,
        }
    )
    expected_dev = Counter(
        {
            "natural_connector": 64,
            "ordinary_web": 16,
            "mixed_local_first": 48,
            "privacy_local_first": 48,
        }
    )
    if Counter(row["failure_cluster"] for row in train) != expected_train:
        raise RuntimeError("train quota changed")
    if Counter(row["failure_cluster"] for row in dev) != expected_dev:
        raise RuntimeError("dev quota changed")
    if len({row["text"] for row in [*train, *dev]}) != len(train) + len(dev):
        raise RuntimeError("exact stage duplicate detected")
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    if train_families & dev_families:
        raise RuntimeError("semantic family crosses train/dev")
    contamination = round1._holdout_contamination(
        [*stable_contamination, *candidates]
    )

    OUTPUT.mkdir(parents=True)
    write_jsonl(OUTPUT / "stage_sft.train.jsonl", train)
    write_jsonl(OUTPUT / "stage_sft.dev.jsonl", dev)
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        (
            {"prompt": row["prompt"], "target": row["target"], "text": row["text"]}
            for row in train
        ),
    )
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        (
            {"prompt": row["prompt"], "target": row["target"], "text": row["text"]}
            for row in dev
        ),
    )
    write_jsonl(OUTPUT / "new_candidate_validation.jsonl", validations)
    write_json(
        OUTPUT / "hard_negative_registry.json",
        {
            "schema_version": "rwkv-lh.stage3-hard-negatives.v1",
            "observed_failures": {
                "natural_connector": "Stage2 synthetic dev 64/64 connector while ECRA natural connector was 0/20",
                "completion_stop": "Stage2 regressed three frozen completion selectors and interrupted 20 ECRA cases",
            },
            "rules": [
                "connector questions must be natural tasks without route-answer labels",
                "ordinary public pages remain connector hard negatives",
                "complete observations must preserve final_answer through the full Stage1 selector replay",
            ],
        },
    )
    (OUTPUT / "README.md").write_text(
        "# RWKV-LH Stage 3 natural-route + stop state tuning\n\n"
        "1400 train rows combine the complete Stage1 selector replay with natural connector, "
        "ordinary-web, mixed-local-first, and privacy-local-first boundaries. Targets are "
        "Controller-rendered selector transitions, not generic task answers. Training requires "
        "target_suffix and BOS 0.\n",
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
        "artifact_kind": "failure_grounded_natural_route_and_stop_state_tuning",
        "purpose": "Correct Stage2 route transfer and stopping regressions without task-answer SFT.",
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
            "stage1_dataset": str(STAGE1.relative_to(ROOT)),
            "stage1_manifest_sha256": sha256(STAGE1 / "manifest.json"),
            "stage2_result": str(STAGE2_RESULT.relative_to(ROOT)),
            "stage2_result_sha256": sha256(STAGE2_RESULT),
            "preregistration": str(PREREGISTRATION.relative_to(ROOT)),
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
        },
        "files": files,
        "generation": f"uv run python {Path(__file__).resolve()}",
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"] | {"contamination": contamination}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
