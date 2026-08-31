from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.state_router.protocol import RouterInput
from scripts.generate_state_router_2k_v1 import audit, build_rows


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_state_router_2k_manifest_and_file_hashes_are_frozen() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["dataset_version"] == "rwkv-lh.state-router-2k.v1"
    assert manifest["feature_protocol"] == "rwkv-lh.final-hidden-mean.v1"
    assert manifest["split_protocol"] == "semantic-family-grouped-70-15-15.v1"
    assert manifest["summary_authority"] is False
    assert manifest["controller_and_gate_authority"] is True
    for name, record in manifest["files"].items():
        path = DATA / name
        assert path.stat().st_size == record["bytes"]
        assert sha256(path) == record["sha256"]
    generator = ROOT / manifest["generator"]["path"]
    assert sha256(generator) == manifest["generator"]["sha256"]
    for section in ("sources", "holdouts"):
        for relative, record in manifest[section].items():
            assert sha256(ROOT / relative) == record["sha256"]


def test_state_router_2k_has_grouped_70_15_15_split_and_no_exact_duplicates() -> None:
    rows = read_jsonl(DATA / "samples.jsonl")
    assert len(rows) == 2000
    assert Counter(row["split"] for row in rows) == {
        "train": 1400,
        "dev": 300,
        "test": 300,
    }
    assert len({row["sample_id"] for row in rows}) == 2000

    family_splits: dict[str, set[str]] = defaultdict(set)
    family_sizes: Counter[str] = Counter()
    rendered: set[str] = set()
    for row in rows:
        family_splits[row["semantic_family_id"]].add(row["split"])
        family_sizes[row["semantic_family_id"]] += 1
        text = RouterInput.from_dict(row["input"]).render()
        assert text not in rendered
        rendered.add(text)
    assert len(family_splits) == 250
    assert all(len(splits) == 1 for splits in family_splits.values())
    assert min(family_sizes.values()) >= 7
    assert Counter(next(iter(splits)) for splits in family_splits.values()) == {
        "train": 175,
        "dev": 37,
        "test": 38,
    }


def test_state_router_2k_meets_first_round_design_quotas() -> None:
    rows = read_jsonl(DATA / "samples.jsonl")
    variants = Counter(row["variant_kind"] for row in rows)

    assert sum(row["input"]["mode"] == "fresh" for row in rows) == 400
    assert sum(
        row["variant_kind"].startswith("true_summary") for row in rows
    ) == 300
    assert sum(
        row["input"]["policy_state"] == "network_denied" for row in rows
    ) == 100
    assert variants["summary_conflicts_with_committed_evidence"] == 250
    assert variants["incomplete_summary_partial_evidence"] == 250
    assert variants["misleading_summary_partial_evidence"] == 246
    assert variants["continuation_without_summary"] == 54


def test_state_router_2k_summary_never_changes_mechanical_truth() -> None:
    rows = read_jsonl(DATA / "samples.jsonl")
    by_family: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in rows:
        by_family[row["semantic_family_id"]][row["variant_kind"]] = row

    for variants in by_family.values():
        bare = variants["fresh_bare"]
        true_summary = variants["true_summary"]
        assert bare["labels"]["execution_phase"] == true_summary["labels"]["execution_phase"]
        assert bare["labels"]["route_family"] == true_summary["labels"]["route_family"]
        assert (
            bare["labels"]["network_recommendation"]
            == true_summary["labels"]["network_recommendation"]
        )

        partial = variants["incomplete_summary_partial_evidence"]
        misleading = variants.get("misleading_summary_partial_evidence")
        if misleading is not None:
            assert partial["labels"] == misleading["labels"]

        conflict = variants["summary_conflicts_with_committed_evidence"]
        assert conflict["input"]["evidence_state"] == "evidence_committed"
        assert conflict["labels"]["execution_phase"] == "evidence_committed"


def test_state_router_2k_holdouts_are_audit_only_and_below_threshold() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    contamination = manifest["validation"]["contamination"]

    assert contamination["similarity_version"] == "utf8-byte-ngram-cosine.v1"
    assert contamination["holdout_request_count"] == 210
    assert contamination["maximum_holdout_similarity"] < 0.75
    assert manifest["validation"]["family_split_overlap_count"] == 0
    assert manifest["validation"]["exact_rendered_input_duplicate_count"] == 0


def test_state_router_2k_is_byte_semantically_reproducible_from_generator() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    generated = build_rows()

    assert generated == read_jsonl(DATA / "samples.jsonl")
    assert audit(generated) == manifest["validation"]
