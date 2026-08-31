#!/usr/bin/env python3
"""Create S58 by removing one hidden-generator label contradiction from S56."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path("/home/chase/GitHub/RWKV-LH")
S56 = ROOT / "data/datasets/rwkv_lh_network_selector_full_request_last_s56_v1"
S55 = ROOT / "data/datasets/rwkv_lh_network_selector_true_workflow_s55_v1"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S58_IDENTIFIABLE_CANONICAL_FIRST_OPERATION_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_identifiable_s58_v1"

S56_CASES_SHA256 = "8bd02a2368f29657bbd87d8ba103a410ec92fd04cc5c99a8286ac49064548697"
S56_MANIFEST_SHA256 = "9c2a890366800c7332a9382331118c6400236662682f7393bd74832af1025d96"
S55_CASES_SHA256 = "f183b5ef6389dd4549d245f05be2e9933f9b5efb8bbecaf23ae2184a75de02fe"
PREREGISTRATION_SHA256 = "48ee8fbd558e41ad41851bb862706c2a363e3abcca85374c2374b2c9127a0902"
EXPECTED_ROWS = 18293
EXPECTED_SPLITS = {"train": 13143, "dev": 2571, "test": 2579}
EXPECTED_CORRECTIONS = {"train": 20, "dev": 6, "test": 6}
POLICY = "explicit-path-first-operation.read-file.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S58 dataset")
    for path, expected in {
        S56 / "cases.jsonl": S56_CASES_SHA256,
        S56 / "manifest.json": S56_MANIFEST_SHA256,
        S55 / "cases.jsonl": S55_CASES_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
    }.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"S58 frozen input changed: {path}")

    s55_rows = read_jsonl(S55 / "cases.jsonl")
    s55 = {str(row["sample_id"]): row for row in s55_rows}
    if len(s55) != len(s55_rows) or len(s55_rows) != 1280:
        raise RuntimeError("S55 source identities are not unique")
    source_rows = read_jsonl(S56 / "cases.jsonl")
    if len(source_rows) != EXPECTED_ROWS:
        raise RuntimeError("S56 source row count changed")

    result: list[dict[str, Any]] = []
    corrections: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    source_split_counts: Counter[tuple[str, str]] = Counter()
    label_counts: Counter[tuple[str, str, str]] = Counter()
    prompt_hashes: set[str] = set()
    for source in source_rows:
        row = dict(source)
        split = str(row["split"])
        source_dataset = str(row["source_dataset"])
        original_label = str(row["label"])
        family = ""
        corrected = False
        if source_dataset == "s55":
            source_id = str(row["source_sample_id"])
            if source_id not in s55:
                raise RuntimeError("S58 cannot resolve an S55 source sample")
            provenance = s55[source_id]
            if (
                provenance["split"] != split
                or int(provenance["trajectory_position"])
                != int(row["trajectory_position"])
                or provenance["label"] != original_label
            ):
                raise RuntimeError("S58/S55 source provenance changed")
            family = str(provenance["family"])
            corrected = (
                family == "discount_ledger_release"
                and int(row["trajectory_position"]) == 0
                and original_label == "list_directory"
            )
        if corrected:
            row["label"] = "read_file"
            corrections[split] += 1
        row.update(
            {
                "schema_version": "rwkv-lh.network-selector-identifiable-prefix.s58.v1",
                "dataset_version": "rwkv-lh.network-selector.identifiable-s58.v1",
                "source_label": original_label,
                "source_family": family,
                "label_corrected": corrected,
                "label_policy": POLICY,
                "label_correction_reason": (
                    "canonical-read-file-when-all-input-paths-are-explicit"
                    if corrected
                    else "source-label-retained"
                ),
            }
        )
        if row["bootstrap"] != source["bootstrap"] or row["step"] != source["step"]:
            raise RuntimeError("S58 changed a rendered input component")
        if row["rendered_input"] != source["rendered_input"]:
            raise RuntimeError("S58 changed rendered input bytes")
        digest = hashlib.sha256(row["rendered_input"].encode("utf-8")).hexdigest()
        if digest != row["rendered_input_sha256"]:
            raise RuntimeError("S58 rendered input digest changed")
        step = json.loads(str(row["step"]).removeprefix("SelectorStepV5: "))
        if list(step)[-1] != "current_requirement" or not str(
            step["current_requirement"]
        ).strip():
            raise RuntimeError("S58 full current requirement is not last")
        split_counts[split] += 1
        source_split_counts[(source_dataset, split)] += 1
        label_counts[(source_dataset, split, str(row["label"]))] += 1
        prompt_hashes.add(digest)
        result.append(row)

    if dict(split_counts) != EXPECTED_SPLITS:
        raise RuntimeError(f"S58 split counts changed: {split_counts}")
    if dict(corrections) != EXPECTED_CORRECTIONS:
        raise RuntimeError(f"S58 correction counts changed: {corrections}")
    if len(prompt_hashes) != EXPECTED_ROWS:
        raise RuntimeError("S58 rendered prompts are not unique")
    if any(
        row["label_corrected"]
        and not (
            row["source_dataset"] == "s55"
            and row["source_family"] == "discount_ledger_release"
            and row["trajectory_position"] == 0
            and row["source_label"] == "list_directory"
            and row["label"] == "read_file"
        )
        for row in result
    ):
        raise RuntimeError("S58 correction escaped its global family boundary")

    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases = staging / "cases.jsonl"
    with cases.open("x", encoding="utf-8") as stream:
        for row in result:
            stream.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
    manifest = {
        "schema_version": "rwkv-lh.network-selector-identifiable-manifest.s58.v1",
        "dataset_version": "rwkv-lh.network-selector.identifiable-s58.v1",
        "purpose": "V5 25-class Hidden+MLP selection with identifiable canonical first operations",
        "source": {
            "s56_cases_sha256": S56_CASES_SHA256,
            "s56_manifest_sha256": S56_MANIFEST_SHA256,
            "s55_cases_sha256": S55_CASES_SHA256,
        },
        "generation": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "preregistration": str(PREREGISTRATION.relative_to(ROOT)),
            "preregistration_sha256": PREREGISTRATION_SHA256,
        },
        "rows": len(result),
        "split_counts": dict(sorted(split_counts.items())),
        "correction_policy": POLICY,
        "correction_counts": dict(sorted(corrections.items())),
        "source_split_counts": {
            f"{source}:{split}": count
            for (source, split), count in sorted(source_split_counts.items())
        },
        "source_split_label_counts": {
            f"{source}:{split}:{label}": count
            for (source, split, label), count in sorted(label_counts.items())
        },
        "validation": {
            "all_rendered_inputs_byte_identical_to_s56": True,
            "all_sample_ids_and_splits_unchanged": True,
            "rendered_prompt_duplicates": 0,
            "complete_current_requirement_last": True,
            "test_used_for_training_or_dev_selection": False,
            "generated_rwkv_text": False,
            "raw_rwkv_output_modified": False,
            "only_hidden_generator_label_contradiction_removed": True,
        },
        "files": {
            "cases.jsonl": {
                "rows": len(result),
                "bytes": cases.stat().st_size,
                "sha256": sha256_file(cases),
            }
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S58 identifiable V5 Selector dataset\n\n"
        "S56 inputs are byte-identical. One family-wide hidden-generator label "
        "contradiction is canonicalized to `read_file`; see `manifest.json`.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s58_dataset_complete",
                "rows": len(result),
                "corrections": dict(corrections),
                "cases_sha256": manifest["files"]["cases.jsonl"]["sha256"],
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
