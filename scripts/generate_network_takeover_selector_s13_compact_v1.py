#!/usr/bin/env python3
"""Build the preregistered S13 compact-natural network Gate dataset."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.takeover_protocol_v4 import NetworkTakeoverInput


ROOT = Path(__file__).resolve().parents[1]
S11 = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s11_v1/cases.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s13_compact_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S13_COMPACT_BOUNDARY_PREREGISTRATION.md"
VERSION = "rwkv-lh.network-takeover-selector.s13.compact.v1"
S11_SHA256 = "553208ddf01e9baa6542fbd95ed653a0615111263a0573be4c388a4ca86f0c17"
ECRA_SHA256 = "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a"
SUPPLEMENT_COUNTS = {
    ("train", "compact_local_only", "DEFER"): 104,
    ("dev", "compact_local_only", "DEFER"): 16,
    ("train", "deterministic_retention", "DEFER"): 104,
    ("dev", "deterministic_retention", "DEFER"): 16,
    ("train", "mixed_local_first", "DEFER"): 156,
    ("dev", "mixed_local_first", "DEFER"): 24,
    ("train", "privacy_local_first", "DEFER"): 52,
    ("dev", "privacy_local_first", "DEFER"): 8,
    ("train", "ordinary_web", "web_search"): 52,
    ("dev", "ordinary_web", "web_search"): 8,
    ("train", "natural_connector", "connector_lookup"): 52,
    ("dev", "natural_connector", "connector_lookup"): 8,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_ngrams(value: str, n: int = 5) -> Counter[bytes]:
    data = value.encode("utf-8")
    return Counter(data[index : index + n] for index in range(max(0, len(data) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(key, 0) for key, count in left.items())
    if not dot:
        return 0.0
    return dot / math.sqrt(
        sum(count * count for count in left.values())
        * sum(count * count for count in right.values())
    )


def rendered_objective(rendered: str) -> str:
    prefix = "NetworkTakeoverQueryV1: "
    if not rendered.startswith(prefix):
        raise RuntimeError("S13 rendered input prefix changed")
    return str(json.loads(rendered[len(prefix) :])["objective"])


def objective(cluster: str, index: int) -> str:
    serial = index + 101
    paths = (
        f"workspace/config/service_{serial}.toml",
        f"inputs/catalog_{serial}.json",
        f"notes/release_target_{serial}.txt",
        f"artifacts/bundle_{serial}.bin",
    )
    zones = ("Europe/Paris", "Asia/Tokyo", "Australia/Sydney", "America/Chicago")
    packages = (f"harbor-kit-{serial}", f"cedar-parser-{serial}", f"quartz-db-{serial}")
    repositories = (f"sample-labs/project-{serial}", f"public-tools/module-{serial}")
    if cluster == "compact_local_only":
        templates = (
            f"Inspect `{paths[0]}` locally and report its declared service name before any outside lookup.",
            f"先读取工作区文件 `{paths[1]}` 的顶层标识；这个步骤只使用本地内容。",
            f"List the entries under `inputs/batch_{serial}` as the immediate workspace action.",
            f"请先计算本地文件 `{paths[3]}` 的 SHA-256，本步骤不调用公共来源。",
            f"Open `{paths[2]}` and return the exact text already stored there; keep this action local.",
            f"在项目中检查 `src/unit_{serial}.py` 是否存在，当前阶段不要发起网络请求。",
        )
    elif cluster == "deterministic_retention":
        templates = (
            f"Use the deterministic clock operation for {zones[index % len(zones)]}; attach the supplied local request number {serial}, without a webpage.",
            f"计算 2023-01-{index % 27 + 1:02d} 与 2023-02-{index % 25 + 1:02d} 之间的日历天数。",
            f"Evaluate the complete arithmetic expression ({serial} * 7) - 3 with the local calculator.",
            f"请用时区工具返回 {zones[index % len(zones)]} 的当前时间，并标注本地请求编号 {serial}，不查询网页。",
            f"Find the exact date interval from 2022-03-{index % 25 + 1:02d} to 2022-04-{index % 24 + 1:02d} deterministically.",
            f"Compute ({serial} + 19) / 4 from the supplied operands only.",
        )
    elif cluster == "mixed_local_first":
        templates = (
            f"Read `{paths[0]}` first to learn its package coordinate; only then can the public release be checked.",
            f"先打开 `{paths[1]}` 取得仓库标识，之后才查询对应的结构化发布记录。",
            f"Obtain the public URL from `{paths[2]}` before fetching that observed address.",
            f"从 `{paths[1]}` 读取城市字段，然后再获取该城市的结构化天气；当前先读文件。",
            f"Inspect `papers/record_{serial}.json` for its DOI before requesting the scholarly record.",
            f"先列出 `references/set_{serial}` 找到目标文件，观察到实体后再进行网页检索。",
            f"Open `alerts/region_{serial}.txt` to determine the region before retrieving public alert metadata.",
            f"Read `vendors/product_{serial}.yaml` first; a later step may inspect its public support page.",
        )
    elif cluster == "privacy_local_first":
        templates = (
            f"Inspect `private/credential_{serial}.txt` locally and do not transmit any value to a web service.",
            f"先在本地读取 `secrets/token_{serial}.json`；不得把其中内容发送到公共查询。",
            f"Check `internal/customer_{serial}.yaml` only inside the workspace and refuse external lookup of private fields.",
            f"本地核对 `restricted/case_{serial}.txt`，任何敏感字符串都不能进入联网参数。",
        )
    elif cluster == "ordinary_web":
        templates = (
            f"Find the current public documentation page for {packages[index % len(packages)]}.",
            f"查询公开网页上 {packages[index % len(packages)]} 的最新兼容性说明。",
            f"Search the public web for today's opening hours of Example Gallery {serial}.",
            f"Retrieve the exact public URL https://example.com/reference/{serial} and record its content.",
        )
    elif cluster == "natural_connector":
        templates = (
            f"Retrieve the structured release record for package {packages[index % len(packages)]}.",
            f"查询仓库 {repositories[index % len(repositories)]} 的结构化最新发布信息。",
            f"Look up structured weather observations for region Test-Region-{serial}.",
            f"Get the scholarly metadata for DOI 10.5555/example.{serial} from the structured source.",
        )
    else:
        raise RuntimeError(f"unknown S13 cluster: {cluster}")
    return templates[index % len(templates)]


def compact_row(split: str, cluster: str, label: str, index: int) -> dict[str, Any]:
    text = objective(cluster, index + (0 if split == "train" else 10_000))
    rendered = NetworkTakeoverInput(text).render()
    return {
        "schema_version": "rwkv-lh.network-takeover-selector-row.s13.v1",
        "dataset_version": VERSION,
        "sample_id": f"NETTAKE-S13-COMPACT-{split.upper()}-{cluster.upper()}-{index:04d}",
        "source_kind": "compact_natural",
        "source_sample_id": f"generated:{split}:{cluster}:{index}",
        "semantic_family_id": f"s13-{split}-{cluster}-{index // 4:04d}",
        "failure_cluster": cluster,
        "split": split,
        "label": label,
        "rendered_input": rendered,
        "selector_input_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "generated_rwkv_text": False,
    }


def main() -> None:
    if sha256_file(S11) != S11_SHA256 or sha256_file(ECRA) != ECRA_SHA256:
        raise RuntimeError("S13 frozen source changed")
    if OUTPUT.exists() or not PROTOCOL.is_file():
        raise RuntimeError("S13 output exists or preregistration is missing")

    rows: list[dict[str, Any]] = []
    for line in S11.read_text(encoding="utf-8").splitlines():
        source = json.loads(line)
        if source["source_kind"] not in {"s10", "coverage"}:
            continue
        value = dict(source)
        value["schema_version"] = "rwkv-lh.network-takeover-selector-row.s13.v1"
        value["dataset_version"] = VERSION
        value["source_sample_id"] = source["sample_id"]
        value["sample_id"] = source["sample_id"].replace("S11", "S13", 1)
        rows.append(value)
    if len(rows) != 1400:
        raise RuntimeError(f"S13 inherited row count changed: {len(rows)}")

    for (split, cluster, label), count in SUPPLEMENT_COUNTS.items():
        rows.extend(compact_row(split, cluster, label, index) for index in range(count))
    if len(rows) != 2000 or len({row["sample_id"] for row in rows}) != 2000:
        raise RuntimeError("S13 row/sample identity changed")

    rendered_labels: dict[str, str] = {}
    for row in rows:
        previous = rendered_labels.setdefault(str(row["rendered_input"]), str(row["label"]))
        if previous != row["label"]:
            raise RuntimeError("S13 contradictory rendered input")
    if len(rendered_labels) != 2000:
        raise RuntimeError("S13 exact rendered duplicates remain")
    families = {
        split: {str(row["semantic_family_id"]) for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S13 semantic family crosses splits")
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter({"train": 1506, "dev": 289, "test": 205}):
        raise RuntimeError(f"S13 split counts changed: {split_counts}")

    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    targets = [(str(case["case_id"]), str(case["instruction"]), byte_ngrams(str(case["instruction"]))) for case in holdout]
    holdout_text = {text for _case_id, text, _grams in targets}
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    exact_overlap = 0
    for row in rows:
        text = rendered_objective(str(row["rendered_input"]))
        exact_overlap += int(text in holdout_text)
        grams = byte_ngrams(text)
        for case_id, _target_text, target_grams in targets:
            score = cosine(grams, target_grams)
            if score > maximum["score"]:
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": case_id}
    if exact_overlap or maximum["score"] >= 0.75:
        raise RuntimeError(f"S13 contamination gate failed: {exact_overlap=} {maximum=}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s13_compact.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S13 compact-natural Gate boundary ablation",
        "counts": {
            "rows": len(rows),
            "splits": dict(sorted(split_counts.items())),
            "labels": dict(sorted(Counter(str(row["label"]) for row in rows).items())),
            "sources": dict(sorted(Counter(str(row["source_kind"]) for row in rows).items())),
            "compact_clusters": dict(sorted(Counter(str(row["failure_cluster"]) for row in rows if row["source_kind"] == "compact_natural").items())),
        },
        "sources": {
            "s11": {"path": str(S11.relative_to(ROOT)), "sha256": S11_SHA256, "included_source_kinds": ["s10", "coverage"]},
            "ecra_contamination_only": {"path": str(ECRA.relative_to(ROOT)), "sha256": ECRA_SHA256},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": {"cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases_path)}},
        "validation": {
            "exact_rendered_input_duplicate_count": 0,
            "contradictory_duplicate_count": 0,
            "family_split_overlap_count": 0,
            "generated_rwkv_text_count": 0,
            "contamination": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "threshold_exclusive": 0.75,
                "exact_overlap_count": exact_overlap,
                "maximum": maximum,
            },
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
