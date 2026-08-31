"""Build Stage-4 balanced route-boundary state-tuning data."""

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


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage4_balanced_boundary_v1"
EXPERIMENT = ROOT / "data/experiments/RWKV_STATE_TUNING_STAGE4_TO_STAGE6_V1_20260827"
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
STAGE3_RESULT = (
    ROOT
    / "data/experiments/RWKV_STATE_TUNING_THREE_STAGE_V1_20260826"
    / "STAGE3_RESULT.md"
)
STAGE1 = ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1"
VERSION = "rwkv-lh.state-tuning.stage4-balanced-boundary.v1"
VARIANTS = 4
FAMILY_COUNTS = {
    "train": {
        "natural_connector_paired": 20,
        "ordinary_web_hard_negative": 40,
        "local_only_network_hard_negative": 40,
        "mixed_local_first_natural": 40,
        "privacy_local_first_natural": 20,
    },
    "dev": {
        "natural_connector_paired": 12,
        "ordinary_web_hard_negative": 12,
        "local_only_network_hard_negative": 12,
        "mixed_local_first_natural": 16,
        "privacy_local_first_natural": 8,
    },
}
SIGNATURES = {
    "stable_selector_replay": "FST-S4-001",
    "natural_connector_paired": "FST-S4-002",
    "ordinary_web_hard_negative": "FST-S4-003",
    "local_only_network_hard_negative": "FST-S4-004",
    "mixed_local_first_natural": "FST-S4-005",
    "privacy_local_first_natural": "FST-S4-006",
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
        "natural_connector_paired": "NC",
        "ordinary_web_hard_negative": "OW",
        "local_only_network_hard_negative": "LO",
        "mixed_local_first_natural": "ML",
        "privacy_local_first_natural": "PL",
    }[cluster]
    family_id = f"AST-S4-SF-{code}-{split.upper()}-{family + 1:04d}"
    trajectory_id = f"AST-S4-{code}-{split.upper()}-{family + 1:04d}-{variant + 1:02d}"
    return family_id, trajectory_id


def _base(
    split: str,
    cluster: str,
    family: int,
    variant: int,
    *,
    source_seed_id: str,
) -> dict[str, Any]:
    semantic_family_id, trajectory_id = identity(split, cluster, family, variant)
    return {
        "schema_version": pilot.CANDIDATE_SCHEMA,
        "trajectory_id": trajectory_id,
        "source_seed_id": source_seed_id,
        "semantic_family_id": semantic_family_id,
        "split": split,
        "language": "zh" if variant % 2 == 0 else "en",
        "network_policy": "offline",
        "request": "",
        "workspace_files": [],
        "turns": [],
        "prelude": [],
        "expected_backend_executions": 0,
        "private_oracle_digest": "",
        "failure_cluster": cluster,
        "failure_signature_id": SIGNATURES[cluster],
    }


def connector_candidate(
    split: str, family: int, variant: int
) -> dict[str, Any]:
    # Reuse the kernel-validated natural connector construction, but allocate a
    # disjoint semantic family and query range for this experiment.
    source_family = family + (400 if split == "train" else 30400)
    row = stage3.connector_candidate(split, source_family, variant)
    semantic_family_id, trajectory_id = identity(
        split, "natural_connector_paired", family, variant
    )
    row.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": semantic_family_id,
            "failure_cluster": "natural_connector_paired",
            "failure_signature_id": SIGNATURES["natural_connector_paired"],
            "contrast_group": f"route-contrast-{split}-{family + 1:04d}",
        }
    )
    return row


def web_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    row = _base(
        split,
        "ordinary_web_hard_negative",
        family,
        variant,
        source_seed_id="ST-S4-WEB",
    )
    offset = family + (700 if split == "train" else 30700)
    nonce = f"{offset + 73:05d}-{variant + 11:02d}"
    subjects = (
        "hosted service incident page",
        "vendor compatibility guide",
        "museum admission notice",
        "community event bulletin",
        "product support policy",
        "public API terms page",
        "transport delay notice",
        "official documentation tutorial",
    )
    subject = subjects[family % len(subjects)]
    name = f"Fictional Larkspur {subject} {nonce}"
    if row["language"] == "zh":
        requests = (
            f"查找 `{name}` 当前普通网页上的说明，并保留页面来源。",
            f"请打开或搜索 `{name}` 的官网页面，核对现在发布的内容。",
        )
    else:
        requests = (
            f"Find the currently published ordinary web page for `{name}` and retain its source.",
            f"Open or search the official website for `{name}` and verify its current notice.",
        )
    row.update(
        {
            "network_policy": "auto_public",
            "request": requests[(variant // 2) % 2],
            "turns": [pilot._turn("web_search", {"query": name, "max_results": 5}, "initial")],
            "expected_backend_executions": 1,
            "contrast_group": f"route-contrast-{split}-{family % max(1, FAMILY_COUNTS[split]['natural_connector_paired']) + 1:04d}",
        }
    )
    return row


def local_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    row = _base(
        split,
        "local_only_network_hard_negative",
        family,
        variant,
        source_seed_id="ST-S4-LOCAL",
    )
    offset = family + (1000 if split == "train" else 31000)
    nonce = f"S4-{offset + 1:05d}-{variant + 1:02d}"
    operation_slot = family % 8
    language = row["language"]
    if operation_slot == 0:
        path = f"workspace/config-{offset + 1}-{variant + 1}.json"
        content = {"feature": {"enabled": False}, "preserve": nonce}
        row["workspace_files"] = [pilot._workspace_file(path, json.dumps(content) + "\n")]
        row["request"] = (
            f"将本地 `{path}` 的 feature.enabled 改为 true，并保留其他字段。"
            if language == "zh"
            else f"Set feature.enabled to true in local `{path}` while preserving every other field."
        )
        row["turns"] = [pilot._turn("patch_json", {"path": path, "updates": {"feature": {"enabled": True}}}, "initial")]
    elif operation_slot in {1, 2}:
        # The existing seed provides validated safe argv and fixtures. Odd/even
        # group parity selects check_command versus run_command.
        group = offset * 2 + (0 if operation_slot == 1 else 1) - variant
        inherited = pilot._instantiate("ST-ACT-019", group, variant)
        row["workspace_files"] = inherited["workspace_files"]
        row["turns"] = inherited["turns"]
        operation = row["turns"][0]["target_operation"]
        argv = row["turns"][0]["target_params"]["argv"]
        row["request"] = (
            f"在当前工作区执行本地{'只读检查' if operation == 'check_command' else '生成步骤'}，argv={json.dumps(argv, ensure_ascii=False)}。"
            if language == "zh"
            else f"Run the local {'read-only check' if operation == 'check_command' else 'generation step'} in this workspace with argv={json.dumps(argv)}."
        )
    elif operation_slot == 3:
        path = f"workspace/notes-{offset + 1}-{variant + 1}.txt"
        row["workspace_files"] = [pilot._workspace_file(path, f"local marker {nonce}\n")]
        row["request"] = (
            f"读取本地文件 `{path}` 并报告 marker。"
            if language == "zh"
            else f"Read local file `{path}` and report its marker."
        )
        row["turns"] = [pilot._turn("read_file", {"path": path}, "initial")]
    elif operation_slot == 4:
        path = f"workspace/record-{offset + 1}-{variant + 1}.json"
        row["workspace_files"] = [pilot._workspace_file(path, json.dumps({"marker": nonce, "count": offset}) + "\n")]
        row["request"] = (
            f"解析本地 JSON `{path}` 并返回 count。"
            if language == "zh"
            else f"Parse local JSON `{path}` and return its count."
        )
        row["turns"] = [pilot._turn("read_json", {"path": path}, "initial")]
    elif operation_slot == 5:
        parent = f"workspace/input-{offset + 1}-{variant + 1}"
        row["workspace_files"] = [pilot._workspace_file(f"{parent}/item-{nonce}.txt", "fixture\n")]
        row["request"] = (
            f"查看本地目录 `{parent}` 中有哪些成员。"
            if language == "zh"
            else f"Inspect which members exist in local directory `{parent}`."
        )
        row["turns"] = [pilot._turn("list_directory", {"path": parent, "recursive": False}, "initial")]
    elif operation_slot == 6:
        path = f"workspace/artifact-{offset + 1}-{variant + 1}.bin"
        row["workspace_files"] = [pilot._workspace_file(path, f"binary-like-{nonce}\n")]
        row["request"] = (
            f"计算本地 `{path}` 的 SHA-256。"
            if language == "zh"
            else f"Calculate the SHA-256 digest of local `{path}`."
        )
        row["turns"] = [pilot._turn("file_digest", {"path": path}, "initial")]
    else:
        expression = f"({offset % 47 + 11}*{variant + 7})+{offset % 13 + 3}"
        row["request"] = (
            f"精确计算 `{expression}`。"
            if language == "zh"
            else f"Calculate `{expression}` exactly."
        )
        row["turns"] = [pilot._turn("calculator", {"expression": expression}, "initial")]
    return row


def mixed_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    row = _base(
        split,
        "mixed_local_first_natural",
        family,
        variant,
        source_seed_id="ST-S4-MIXED",
    )
    row["network_policy"] = "auto_public"
    row["expected_backend_executions"] = 1
    offset = family + (1300 if split == "train" else 31300)
    nonce = f"{offset + 1:05d}-{variant + 1:02d}"
    language = row["language"]
    slot = family % 8
    if slot == 0:
        path, value = f"inputs/package-{nonce}.json", {"package": f"pypi:observed-{nonce}"}
        second = pilot._turn("connector_lookup", {"operation": "package_release", "query": value["package"]}, "after_read")
        request = (f"从 `{path}` 取得包标识，再核对其当前发行版。", f"Read the package identifier from `{path}`, then check its current release.")
        first = pilot._turn("read_json", {"path": path}, "initial")
        content = json.dumps(value) + "\n"
    elif slot == 1:
        path, value = f"inputs/repository-{nonce}.txt", f"synthetic-{nonce}/project"
        second = pilot._turn("connector_lookup", {"operation": "github_release", "query": value}, "after_read")
        request = (f"读取 `{path}` 中的仓库名，再检查它的最新 release。", f"Read the repository name in `{path}`, then inspect its latest release.")
        first = pilot._turn("read_file", {"path": path}, "initial")
        content = value + "\n"
    elif slot == 2:
        path, value = f"inputs/service-{nonce}.txt", f"Fictional service status {nonce}"
        second = pilot._turn("web_search", {"query": value, "max_results": 5}, "after_read")
        request = (f"先从 `{path}` 确认服务名称，然后查看其当前公开状态。", f"Use `{path}` to identify the service, then inspect its current public status.")
        first = pilot._turn("read_file", {"path": path}, "initial")
        content = value + "\n"
    elif slot == 3:
        path, value = f"inputs/city-{nonce}.json", {"region": f"Observed Ridge {nonce}"}
        second = pilot._turn("connector_lookup", {"operation": "weather", "query": value["region"]}, "after_read")
        request = (f"读取 `{path}` 的地区，再获取该地区的结构化天气。", f"Read the region from `{path}`, then retrieve its structured weather.")
        first = pilot._turn("read_json", {"path": path}, "initial")
        content = json.dumps(value) + "\n"
    elif slot == 4:
        path, value = f"inputs/paper-{nonce}.json", {"doi": f"10.9999/stage4.{nonce}"}
        second = pilot._turn("connector_lookup", {"operation": "scholarly_record", "query": value["doi"]}, "after_read")
        request = (f"从 `{path}` 读取 DOI，再取得对应论文记录。", f"Read the DOI from `{path}`, then retrieve the matching scholarly record.")
        first = pilot._turn("read_json", {"path": path}, "initial")
        content = json.dumps(value) + "\n"
    elif slot == 5:
        path, value = f"inputs/expression-{nonce}.txt", f"({offset % 31 + 5}+{variant + 8})*3"
        second = pilot._turn("calculator", {"expression": value}, "after_read")
        request = (f"读取 `{path}` 中的表达式，再精确计算。", f"Read the expression in `{path}`, then calculate it exactly.")
        first = pilot._turn("read_file", {"path": path}, "initial")
        content = value + "\n"
        row["expected_backend_executions"] = 0
    elif slot == 6:
        path, value = f"inputs/timezone-{nonce}.json", {"timezone": ("Asia/Seoul", "Europe/Prague", "UTC", "America/Chicago")[variant]}
        second = pilot._turn("current_time", {"timezone": value["timezone"]}, "after_read")
        request = (f"读取 `{path}` 的 IANA 时区，再返回当前时间。", f"Read the IANA timezone from `{path}`, then return its current time.")
        first = pilot._turn("read_json", {"path": path}, "initial")
        content = json.dumps(value) + "\n"
        row["expected_backend_executions"] = 0
    else:
        path, value = f"inputs/url-{nonce}.txt", f"https://synthetic.invalid/docs/{nonce}"
        second = pilot._turn("web_search", {"query": value, "max_results": 5}, "after_read")
        request = (f"从 `{path}` 取得公开文档 URL，然后读取其当前内容。", f"Get the public documentation URL from `{path}`, then retrieve its current content.")
        first = pilot._turn("read_file", {"path": path}, "initial")
        content = value + "\n"
    row.update(
        {
            "request": request[0] if language == "zh" else request[1],
            "workspace_files": [pilot._workspace_file(path, content)],
            "turns": [first, second],
        }
    )
    return row


def privacy_candidate(split: str, family: int, variant: int) -> dict[str, Any]:
    seed = "ST-ACT-013" if family % 2 == 0 else "ST-ACT-014"
    group = family + (1700 if split == "train" else 31700)
    row = pilot._instantiate(seed, group, variant)
    semantic_family_id, trajectory_id = identity(
        split, "privacy_local_first_natural", family, variant
    )
    row.update(
        {
            "trajectory_id": trajectory_id,
            "semantic_family_id": semantic_family_id,
            "split": split,
            "failure_cluster": "privacy_local_first_natural",
            "failure_signature_id": SIGNATURES["privacy_local_first_natural"],
        }
    )
    return row


def candidates() -> list[dict[str, Any]]:
    builders = {
        "natural_connector_paired": connector_candidate,
        "ordinary_web_hard_negative": web_candidate,
        "local_only_network_hard_negative": local_candidate,
        "mixed_local_first_natural": mixed_candidate,
        "privacy_local_first_natural": privacy_candidate,
    }
    result: list[dict[str, Any]] = []
    for split, quotas in FAMILY_COUNTS.items():
        for cluster, count in quotas.items():
            for family in range(count):
                for variant in range(VARIANTS):
                    result.append(builders[cluster](split, family, variant))
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
            "training_intent": "paired_boundary_correction_without_task_answer_sft",
            "contrast_group": candidate.get("contrast_group", ""),
        }
    )
    return row, validation


def stable_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows, contamination = stage3.stable_rows()
    for row in rows:
        row["failure_signature_id"] = SIGNATURES["stable_selector_replay"]
        row["training_intent"] = "preserve_stage1_selector_safety_and_stopping"
    return rows, contamination


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite existing dataset: {OUTPUT}")
    if not PREREGISTRATION.is_file() or not STAGE3_RESULT.is_file():
        raise RuntimeError("Stage4 preregistration or Stage3 result is missing")
    stable, stable_contamination = stable_rows()
    raw_candidates = candidates()
    stages: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    for index, candidate in enumerate(raw_candidates, 1):
        try:
            stage, validation = selected_stage(candidate)
        except Exception as exc:
            raise RuntimeError(
                f"controller replay failed at {index}/{len(raw_candidates)} "
                f"for {candidate['trajectory_id']} ({candidate['failure_cluster']})"
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
            print(f"controller replay {index}/{len(raw_candidates)}", flush=True)

    train = [*stable, *(row for row in stages if row["split"] == "train")]
    dev = [row for row in stages if row["split"] == "dev"]
    expected_train = Counter(
        {"stable_selector_replay": 500}
        | {cluster: families * VARIANTS for cluster, families in FAMILY_COUNTS["train"].items()}
    )
    expected_dev = Counter(
        {cluster: families * VARIANTS for cluster, families in FAMILY_COUNTS["dev"].items()}
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
        [*stable_contamination, *raw_candidates]
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
        OUTPUT / "hard_negative_registry.json",
        {
            "schema_version": "rwkv-lh.stage4-hard-negatives.v1",
            "source_failures": {
                "ordinary_web": "Stage3 21/25; four cases selected connector_lookup",
                "local_only": "Stage3 local network false-positive rate 0.30",
                "mixed_local_first": "Stage3 2/20",
                "privacy_local_first": "Stage3 2/10",
                "stopping": "Stage3 failed/interrupted 8/120",
            },
            "design": [
                "connector positives are outnumbered by ordinary-web and local-first counterexamples",
                "mixed tasks cover read_file, read_json and downstream network or deterministic tools",
                "all targets are replayed selector transitions; no task answer is trained",
                "the complete Stage1 selector replay anchors stopping and protocol correction",
            ],
        },
    )
    (OUTPUT / "README.md").write_text(
        "# RWKV-LH Stage4 balanced boundary state tuning\n\n"
        "A failure-grounded correction set for Stage3 online/connector over-calibration. "
        "It retains the complete Stage1 selector replay and adds paired natural connector, "
        "ordinary-web, local-only, mixed-local-first, and privacy-local-first transitions.\n",
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
        "artifact_kind": "failure_grounded_balanced_boundary_state_tuning",
        "purpose": "Correct Stage3 online/connector over-calibration while retaining Stage1 safety and stopping.",
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
            "stage3_result": str(STAGE3_RESULT.relative_to(ROOT)),
            "stage3_result_sha256": sha256(STAGE3_RESULT),
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
            "seed": 830,
            "lr_init": "1e-5",
            "lr_final": "2e-6",
        },
        "files": files,
        "generation": f"uv run python {Path(__file__).resolve()}",
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest["counts"] | {"contamination": contamination}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
