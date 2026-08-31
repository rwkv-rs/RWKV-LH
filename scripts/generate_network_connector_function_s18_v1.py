#!/usr/bin/env python3
"""Freeze the 2,000-row S18 connector-vs-other function-head projection."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_description_s6_v1/queries.jsonl"
FEATURE_MANIFEST = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s6_query_features/FEATURE_MANIFEST.json"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S18_CONNECTOR_FUNCTION_HEAD_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_connector_function_s18_v1"
SOURCE_SHA = "d60ad4a2404fda0f9401a5858070bb5e3063d408be68c9f88e1c0431eed1313c"
FEATURE_MANIFEST_SHA = "d2b6cf2ecd5c42981f390f94ce779ab2c36349829e185a4e310e78be9500b002"
VERSION = "rwkv-lh.network-connector-function.s18.v1"
GROUP_COUNTS = {
    "connector_positive": 690,
    "web": 310,
    "read_file": 250,
    "read_json": 150,
    "deterministic": 150,
    "other_local_read": 150,
    "workspace_mutation": 150,
    "control_process": 150,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def group(label: str) -> str:
    if label == "connector_lookup":
        return "connector_positive"
    if label == "web_search":
        return "web"
    if label == "read_file":
        return "read_file"
    if label == "read_json":
        return "read_json"
    if label in {"calculator", "date_diff", "current_time"}:
        return "deterministic"
    if label in {"list_directory", "search_text", "file_digest", "bind_evidence"}:
        return "other_local_read"
    if label in {
        "write_file", "write_json", "patch_json", "replace_text", "remove_line",
        "append_file", "make_directory", "copy_file", "move_file", "delete_file",
    }:
        return "workspace_mutation"
    if label in {"final_answer", "ABSTAIN", "check_command", "run_command"}:
        return "control_process"
    raise ValueError(f"S18 unmapped label: {label}")


def rank(row: dict[str, object]) -> tuple[str, str]:
    identity = f"S18|{row['sample_id']}|{row['semantic_family_id']}".encode("utf-8")
    return hashlib.sha256(identity).hexdigest(), str(row["sample_id"])


def main() -> None:
    if OUTPUT.exists() or not PROTOCOL.is_file():
        raise RuntimeError("S18 output exists or preregistration is missing")
    if sha256_file(SOURCE) != SOURCE_SHA or sha256_file(FEATURE_MANIFEST) != FEATURE_MANIFEST_SHA:
        raise RuntimeError("S18 frozen source identity changed")
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    buckets: dict[str, list[tuple[int, dict[str, object]]]] = {name: [] for name in GROUP_COUNTS}
    for index, row in enumerate(source_rows):
        if row["split"] != "train":
            continue
        buckets[group(str(row["label"]))].append((index, row))
    selected: list[dict[str, object]] = []
    for name, count in GROUP_COUNTS.items():
        candidates = sorted(buckets[name], key=lambda item: rank(item[1]))
        if name == "connector_positive" and len(candidates) != count:
            raise RuntimeError("S18 connector train cardinality changed")
        if len(candidates) < count:
            raise RuntimeError(f"S18 group {name} lacks rows")
        for source_index, row in candidates[:count]:
            selected.append(
                {
                    "schema_version": "rwkv-lh.network-connector-function-row.s18.v1",
                    "dataset_version": VERSION,
                    "sample_id": f"CONNFN-S18-{row['sample_id']}",
                    "source_index": source_index,
                    "source_sample_id": row["sample_id"],
                    "semantic_family_id": row["semantic_family_id"],
                    "source_kind": row["source_kind"],
                    "source_label": row["label"],
                    "binary_label": "CONNECTOR" if row["label"] == "connector_lookup" else "OTHER",
                    "selection_group": name,
                    "split": "train",
                    "selector_input_sha256": row["selector_input_sha256"],
                }
            )
    selected.sort(key=lambda row: (str(row["selection_group"]), rank({"sample_id": row["source_sample_id"], "semantic_family_id": row["semantic_family_id"]})))
    counts = Counter(str(row["selection_group"]) for row in selected)
    labels = Counter(str(row["binary_label"]) for row in selected)
    if len(selected) != 2000 or counts != Counter(GROUP_COUNTS) or labels != Counter({"OTHER": 1310, "CONNECTOR": 690}):
        raise RuntimeError("S18 frozen counts changed")
    if len({row["source_sample_id"] for row in selected}) != 2000:
        raise RuntimeError("S18 selected source rows are not unique")
    unique_families = len(
        {
            (str(row["source_kind"]), str(row["semantic_family_id"]))
            for row in selected
        }
    )
    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s18_connector.", dir=OUTPUT.parent))
    cases = staging / "cases.jsonl"
    with cases.open("w", encoding="utf-8") as stream:
        for row in selected:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S18-CONNECTOR-N0 function head",
        "counts": {"rows": 2000, "binary_labels": dict(sorted(labels.items())), "groups": dict(sorted(counts.items()))},
        "unique_source_kind_families": unique_families,
        "family_note": "Causal turns from one source family may share a family id; source train/dev/test family isolation is inherited unchanged.",
        "selection": "all connector positives; SHA256('S18|sample_id|semantic_family_id') rank within every fixed negative group",
        "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA},
        "feature_manifest": {"path": str(FEATURE_MANIFEST.relative_to(ROOT)), "sha256": FEATURE_MANIFEST_SHA},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generator_sha256": sha256_file(Path(__file__)),
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generated_rwkv_text_count": 0,
        "sampling_invocation_count": 0,
        "files": {"cases.jsonl": {"rows": 2000, "sha256": sha256_file(cases)}},
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
