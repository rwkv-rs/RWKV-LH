"""Replay sealed raw source groups, then audit a sealed membership-only selection."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Mapping

from rwkv_lh import statetune_core as core
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace
from rwkv_lh.role_trace_artifacts import build_artifacts, write_artifacts

SOURCE_SCHEMA = "rwkv-lh.role-trace-selected-sources.v1"
SELECTION_SCHEMA = "rwkv-lh.statetune-row-selection.v1"


def sealed(reference: Mapping) -> dict:
    core.require(isinstance(reference, Mapping) and set(reference) == {"path", "sha256"},
                 "an exact sealed reference is required")
    trace._source_path(Path(reference["path"]))
    return core.read_sealed_json(reference["path"], reference["sha256"])


def read_selection(reference: Mapping, role: str) -> dict:
    selection = sealed(reference)
    core.require(selection.get("schema_version") == SELECTION_SCHEMA and selection.get("role") == role,
                 "unknown or mismatched row selection registration")
    kept, counts = selection.get("kept_sample_ids"), selection.get("counts")
    core.require(isinstance(kept, list) and kept and all(isinstance(x, str) and x for x in kept)
                 and len(set(kept)) == len(kept), "row selection requires unique nonempty sample IDs")
    core.require(isinstance(counts, Mapping) and set(counts) == {"train", "dev", "confirmation"}
                 and all(type(n) is int and n >= 0 for n in counts.values()) and sum(counts.values()) == len(kept),
                 "row selection counts differ from kept IDs")
    evidence = selection.get("policy_evidence_refs")
    core.require(isinstance(evidence, list) and evidence, "row selection requires pinned policy evidence")
    for reference in evidence:
        core.require(isinstance(reference, Mapping) and set(reference) == {"path", "sha256"},
                     "row selection requires pinned policy evidence")
        trace._source_path(Path(reference["path"]))
        core.verify_file(reference["path"], reference["sha256"])
    return selection


def select_rows(rows: list[dict], selection: Mapping) -> list[dict]:
    indexed = {row["sample_id"]: row for row in rows}
    core.require(len(indexed) == len(rows), "re-extracted rows have duplicate sample IDs")
    core.require(set(selection["kept_sample_ids"]) <= set(indexed),
                 "row selection names sample IDs absent from re-extraction")
    selected = [indexed[key] for key in selection["kept_sample_ids"]]
    observed = {split: sum(row.get("split") == split for row in selected)
                for split in ("train", "dev", "confirmation")}
    core.require(observed == dict(selection["counts"]), "row selection counts differ from re-extracted splits")
    return selected


def _scoped_waiver(group: Mapping, source: Mapping, role: str) -> dict | None:
    reference = group.get("equivalence_waiver")
    reviews = group.get("waiver_reviews")
    if reference is None:
        core.require(reviews is None, "waiver scope reviews require a waiver")
        return None
    document = sealed(reference)
    core.require(isinstance(reviews, list) and len(reviews) == 2, "waiver scope requires two pinned reviews")
    reviewers = set()
    for review_ref in reviews:
        review = sealed(review_ref)
        reviewer = review.get("reviewer")
        core.require(isinstance(reviewer, str) and reviewer in document.get("reviewers", [])
                     and reviewer not in reviewers, "waiver scope reviewers differ from the accepted waiver")
        core.require(review.get("decision") == "accept"
                     and review.get("registration_sha256") == group["source_registration"]["sha256"]
                     and review.get("waiver_sha256") == reference["sha256"]
                     and review.get("wrapper_sha256") == core.sha256_file(__file__)
                     and review.get("role") == role
                     and type(review.get("source_count")) is int
                     and review["source_count"] == len(source.get("source_runs", [])) > 0,
                     "waiver scope review does not bind these sources, role and replay wrapper")
        reviewers.add(reviewer)
    return trace.read_equivalence_waiver(Path(reference["path"]), reference["sha256"])


def _replay_group(group: Mapping, output: Path, role: str) -> tuple[dict, list[dict]]:
    core.require(isinstance(group, Mapping)
                 and {"source_registration", "candidate_manifest"} <= set(group)
                 and not set(group) - {"source_registration", "candidate_manifest", "equivalence_waiver", "waiver_reviews"},
                 "selected source group fields differ")
    source_ref, candidate_ref = group["source_registration"], group["candidate_manifest"]
    source_document = sealed(source_ref)
    candidate = sealed(candidate_ref)
    core.require(candidate.get("provenance", {}).get("source_registration_sha256") == source_ref["sha256"],
                 "raw candidate source registration differs")
    waiver_ref = group.get("equivalence_waiver")
    expected_waiver = waiver_ref["sha256"] if waiver_ref else None
    core.require(candidate.get("provenance", {}).get("equivalence_waiver_sha256") == expected_waiver,
                 "raw candidate admission waiver differs from selected source group")
    waiver = _scoped_waiver(group, source_document, role)
    reproduced = trace.extract_registration(Path(source_ref["path"]), output, roles=[role],
        equivalence_waiver=waiver, equivalence_waiver_sha256=expected_waiver)
    core.require(reproduced == candidate, "raw candidate audit differs from production re-extraction")
    original = Path(candidate_ref["path"]).parent
    core.require((output/"manifest.json").read_bytes() == Path(candidate_ref["path"]).read_bytes(),
                 "raw candidate manifest bytes differ from production re-extraction")
    for name, identity in candidate["files"].items():
        core.require(Path(name).name == name and name not in {"", ".", ".."}, "raw candidate member must be direct")
        path = trace._source_path(original/name)
        core.verify_file(path, identity["sha256"])
        core.require(path.read_bytes() == (output/name).read_bytes(), "raw candidate member bytes differ")
    rows = [json.loads(line) for line in (output/"candidates.jsonl").read_text().splitlines()]
    return candidate, rows


def extract_selected_registration(registration_path: Path, output: Path, *, roles: list[str],
                                  prior_regression: Mapping | None = None,
                                  expected_regression_fingerprint: str | None = None) -> dict:
    """Raw integrity is checked before filtering; only final quality can become valid.

    Every group uses the unchanged production extractor and its own exact waiver.
    A first freeze has no prior. Reuse requires the caller's independently pinned
    prior and fingerprint, and the selection must retain those same evaluation rows.
    """
    output = trace.validate_output_path(output)
    registration_path = trace._source_path(Path(registration_path))
    registration = json.loads(registration_path.read_text())
    core.require(set(registration) == {"schema_version", "role", "source_groups", "row_selection"}
                 and registration["schema_version"] == SOURCE_SCHEMA
                 and roles == [registration["role"]], "selected source registration differs")
    groups = registration["source_groups"]
    core.require(isinstance(groups, list) and groups, "selected sources require nonempty raw source groups")
    selection = read_selection(registration["row_selection"], roles[0])
    output.parent.mkdir(parents=True, exist_ok=True)
    rows, source_runs, identities, conditions = [], [], set(), []
    with tempfile.TemporaryDirectory(prefix=".selected-replay-", dir=output.parent) as directory:
        for index, group in enumerate(groups):
            candidate, incoming = _replay_group(group, Path(directory)/str(index), roles[0])
            core.require(set(candidate["counts_by_role"]) == set(roles), "raw source group mixes training roles")
            for run in candidate["provenance"]["source_runs"]:
                identity = (run["source_run_id"], run["run_id"])
                core.require(identity not in identities, "selected sources repeat a source run")
                identities.add(identity)
                source_runs.append(run)
            conditions.append((candidate["coverage_requirements"], candidate["provenance"]["coverage_scope_sha256"]))
            rows.extend(incoming)
    core.require(all(condition == conditions[0] for condition in conditions), "selected source coverage contracts differ")
    selected = select_rows(rows, selection)
    provenance = {"requested_roles": roles, "source_registration_sha256": core.sha256_file(registration_path),
        "source_runs": source_runs, "source_groups": groups,
        "coverage_scope_sha256": conditions[0][1], "row_selection": registration["row_selection"],
        "selection_helper_sha256": core.sha256_file(__file__), "recomputed_rows": len(rows),
        "equivalence_waiver_sha256": None, "output_kind": "candidate_audit_only", "training_started": False}
    if prior_regression is not None:
        expected = [row for split in ("dev", "confirmation") for row in prior_regression["samples_by_split"][split]]
        actual = [row for row in selected if row["split"] != "train"]
        core.require(sorted(actual, key=lambda r:r["sample_id"]) == sorted(expected, key=lambda r:r["sample_id"]),
                     "selected evaluation members differ from pinned prior regression")
        selected = [row for row in selected if row["split"] == "train"]
    bundle = build_artifacts(selected, provenance=provenance, coverage_requirements=conditions[0][0],
        prior_regression=prior_regression, expected_regression_fingerprint=expected_regression_fingerprint)
    core.require(bundle.manifest["counts_by_role"].get(roles[0]) == selection["counts"], "selected audited counts differ")
    return write_artifacts(output, bundle)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    print(json.dumps(extract_selected_registration(args.registration, args.output, roles=[registration["role"]])))


if __name__ == "__main__":
    main()
