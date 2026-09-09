"""Opaque artifact fixtures only; these are not role-training examples."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json

import pytest


def _artifacts():
    return importlib.import_module("rwkv_lh.role_trace_artifacts")


def _samples(role="selector_intent"):
    required = (
        "failed_last_action", "nonempty_error_type", "directory_target",
        "py_root", "json_root", "directory_root", "mutate", "execute",
        "missing_target",
    )
    return [
        {
            "sample_id": f"{role}-{index}",
            "role": role,
            "project_family": family,
            "input_text": character * 16,
            "target_text": "opaque artifact test payload",
            "coverage": dict.fromkeys(required, True),
            "evidence": {"unit_test_only": True},
        }
        for index, (family, character) in enumerate([
            ("artifact-unit-family-0", "α"),
            ("artifact-unit-family-4", "β"),
            ("artifact-unit-family-7", "γ"),
        ])
    ]


def _provenance():
    return {
        "source_runs": [{"run_id": "artifact-unit-test", "source_trace_sha256": "a" * 64}],
        "extractor_sha256": "b" * 64,
        "protocol_sha256": {"unit-test-protocol.py": "c" * 64},
        "recomputed_rows": 3,
    }


def test_fixed_family_split_and_order_independent_identity():
    api = _artifacts()
    assert [api.split_project_family(row["project_family"]) for row in _samples()] == [
        "train", "dev", "confirmation",
    ]
    first = api.build_artifacts(_samples(), provenance=_provenance())
    second = api.build_artifacts(reversed(_samples()), provenance=_provenance())
    assert first.manifest == second.manifest
    assert first.samples_by_split == second.samples_by_split
    assert first.regression_candidate == second.regression_candidate
    assert first.manifest["status"] == "valid"


def test_requested_role_with_no_samples_cannot_pass_other_roles_coverage():
    api = _artifacts()
    provenance = {**_provenance(), "requested_roles": ["selector_intent", "executor_args"]}
    result = api.build_artifacts(_samples(), provenance=provenance)
    assert result.manifest["status"] == "invalid"
    assert result.manifest["quality_gates"]["requested_roles_present"] is False
    assert result.regression_candidate is None


def test_focused_role_coverage_is_frozen_with_immutable_regression():
    api = _artifacts()
    rows = _samples("selector_intent")
    for row in rows:
        row["coverage"] = dict.fromkeys(api.REQUIRED_COVERAGE, False)
        row["coverage"]["directory_target"] = True
    scope = {"selector_intent": ["directory_target"]}
    bundle = api.build_artifacts(rows, provenance=_provenance(), coverage_requirements=scope)
    assert bundle.manifest["status"] == "valid"
    assert bundle.manifest["coverage_audit"]["selector_intent"]["execute"] == 0
    assert bundle.regression_candidate["coverage_requirements"] == scope
    train = [row for row in rows if api.split_project_family(row["project_family"]) == "train"]
    with pytest.raises(ValueError, match="coverage.*immutable"):
        api.build_artifacts(train, provenance=_provenance(),
                            coverage_requirements={"selector_intent": ["execute"]},
                            prior_regression=bundle.regression_candidate,
                            expected_regression_fingerprint=bundle.regression_candidate["fingerprint"])


def test_cross_split_similarity_invalidates_without_deleting_rows():
    api = _artifacts()
    rows = _samples()
    rows[1]["input_text"] = rows[0]["input_text"]
    result = api.build_artifacts(rows, provenance=_provenance())
    assert result.manifest["status"] == "invalid"
    assert result.manifest["quality_gates"]["cross_split_similarity"] is False
    assert len(result.manifest["similarity_audit"]["violations"]) == 1
    assert sum(map(len, result.samples_by_split.values())) == 3
    assert result.regression_candidate is None


def test_similarity_uses_utf8_bytes_and_fixed_threshold():
    api = _artifacts()
    assert api.byte_5gram_cosine("αβγ", "αβγ") == 1.0
    assert api.byte_5gram_cosine("αβγ", "δεζ") == 0.0
    assert api.byte_5gram_cosine("αβγ", "αβδ") == 0.5
    assert api.byte_5gram_cosine("ab", "ab") == 1.0
    assert api.byte_5gram_cosine("ab", "ac") == 0.0
    result = api.build_artifacts(_samples(), provenance=_provenance())
    parameters = result.manifest["similarity_parameters"]
    assert parameters["encoding"] == "utf-8"
    assert parameters["ngram_bytes"] == 5
    assert parameters["threshold"] == 0.95
    assert parameters["text_field"] == "input_text"


@pytest.mark.parametrize(("suffix_length", "expected"), [(35, False), (36, True)])
def test_similarity_gate_on_both_sides_of_point_95(suffix_length, expected):
    rows = _samples()
    rows[0]["input_text"] = "a" * 100
    rows[1]["input_text"] = "a" * 100 + "b" * suffix_length
    result = _artifacts().build_artifacts(rows, provenance=_provenance())
    assert result.manifest["quality_gates"]["cross_split_similarity"] is expected


@pytest.mark.parametrize("coverage", [
    "failed_last_action", "nonempty_error_type", "directory_target", "py_root",
    "json_root", "directory_root", "mutate", "execute", "missing_target",
])
def test_each_coverage_gap_invalidates(coverage):
    rows = _samples()
    for row in rows:
        row["coverage"][coverage] = False
    result = _artifacts().build_artifacts(rows, provenance=_provenance())
    assert result.manifest["status"] == "invalid"
    assert result.manifest["coverage_audit"]["selector_intent"][coverage] == 0


def test_one_role_cannot_cover_another_role_gap():
    rows = _samples() + _samples("executor_args")
    for row in rows[:3]:
        row["coverage"]["execute"] = False
    result = _artifacts().build_artifacts(rows, provenance=_provenance())
    assert result.manifest["status"] == "invalid"
    assert result.manifest["coverage_audit"]["selector_intent"]["execute"] == 0
    assert result.manifest["coverage_audit"]["executor_args"]["execute"] == 3


def test_missing_split_per_role_is_invalid():
    result = _artifacts().build_artifacts(_samples()[:2], provenance=_provenance())
    assert result.manifest["status"] == "invalid"
    assert result.manifest["quality_gates"]["nonempty_role_splits"] is False


def test_no_samples_is_an_explicit_invalid_audit():
    result = _artifacts().build_artifacts([], provenance=_provenance())
    assert result.manifest["status"] == "invalid"
    assert result.manifest["quality_gates"]["nonempty_samples"] is False
    assert result.regression_candidate is None


def test_reuse_regression_requires_pin_and_unchanged_rows():
    api = _artifacts()
    first = api.build_artifacts(_samples(), provenance=_provenance())
    prior = first.regression_candidate
    expected = prior["fingerprint"]
    fresh = _samples()[:1]
    fresh[0]["sample_id"] = "later-train"
    later = api.build_artifacts(
        fresh, provenance=_provenance(), prior_regression=prior,
        expected_regression_fingerprint=expected,
    )
    assert later.regression_candidate == prior
    assert later.samples_by_split["dev"] == first.samples_by_split["dev"]
    assert later.samples_by_split["confirmation"] == first.samples_by_split["confirmation"]
    assert later.samples_by_split["train"][0]["sample_id"] == "later-train"
    with pytest.raises(ValueError, match="fingerprint"):
        api.build_artifacts(fresh, provenance=_provenance(), prior_regression=prior)
    tampered = copy.deepcopy(prior)
    tampered["samples_by_split"]["dev"][0]["target_text"] = "changed"
    with pytest.raises(ValueError, match="fingerprint"):
        api.build_artifacts(
            fresh, provenance=_provenance(), prior_regression=tampered,
            expected_regression_fingerprint=expected,
        )


def test_later_round_cannot_add_dev_or_confirmation():
    api = _artifacts()
    prior = api.build_artifacts(_samples(), provenance=_provenance()).regression_candidate
    with pytest.raises(ValueError, match="train"):
        api.build_artifacts(
            _samples(), provenance=_provenance(), prior_regression=prior,
            expected_regression_fingerprint=prior["fingerprint"],
        )


def test_family_assignment_cannot_be_overridden_by_record():
    rows = _samples()
    rows[0]["split"] = "dev"
    with pytest.raises(ValueError, match="family"):
        _artifacts().build_artifacts(rows, provenance=_provenance())


@pytest.mark.parametrize("mutation", ["duplicate_id", "unknown_role", "nonboolean_coverage", "invalid_json"])
def test_rejects_malformed_artifact_records(mutation):
    rows = _samples()
    if mutation == "duplicate_id":
        rows[1]["sample_id"] = rows[0]["sample_id"]
    elif mutation == "unknown_role":
        rows[0]["role"] = "unknown"
    elif mutation == "nonboolean_coverage":
        rows[0]["coverage"]["execute"] = 1
    else:
        rows[0]["evidence"] = {"score": float("nan")}
    with pytest.raises(ValueError):
        _artifacts().build_artifacts(rows, provenance=_provenance())


def test_deterministic_atomic_audit_write_and_no_overwrite(tmp_path):
    api = _artifacts()
    result = api.build_artifacts(_samples(), provenance=_provenance())
    first, second = tmp_path / "first", tmp_path / "second"
    manifest = api.write_artifacts(first, result)
    api.write_artifacts(second, result)
    assert manifest == json.loads((first / "manifest.json").read_text())
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }
    assert not (first / "train.jsonl").exists()
    assert len((first / "candidates.jsonl").read_text().splitlines()) == 3
    assert (first / "manifest.sha256").exists()
    assert (first / "manifest.sha256").read_text() == (
        hashlib.sha256((first / "manifest.json").read_bytes()).hexdigest()
        + "  manifest.json\n"
    )
    for filename, identity in manifest["files"].items():
        content = (first / filename).read_bytes()
        assert identity == {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    with pytest.raises(FileExistsError):
        api.write_artifacts(first, result)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["first", "second"]


def test_invalid_audit_does_not_emit_regression_candidate(tmp_path):
    api = _artifacts()
    invalid = api.build_artifacts(_samples()[:1], provenance=_provenance())
    output = tmp_path / "invalid"
    api.write_artifacts(output, invalid)
    assert (output / "candidates.jsonl").exists()
    assert not (output / "regression_candidate.json").exists()


def test_write_failure_leaves_no_partial_output(tmp_path, monkeypatch):
    api = _artifacts()
    result = api.build_artifacts(_samples(), provenance=_provenance())
    def fail_rename(*_args, **_kwargs):
        raise OSError("injected rename failure")
    monkeypatch.setattr(api, "_publish_no_replace", fail_rename)
    with pytest.raises(OSError, match="injected"):
        api.write_artifacts(tmp_path / "failed", result)
    assert list(tmp_path.iterdir()) == []


def test_output_created_during_publication_is_never_overwritten(tmp_path, monkeypatch):
    api = _artifacts()
    publish = api._publish_no_replace
    result = api.build_artifacts(_samples(), provenance=_provenance())
    output = tmp_path / "raced"

    def competing_writer(staging, destination):
        destination.mkdir()
        return publish(staging, destination)

    monkeypatch.setattr(api, "_publish_no_replace", competing_writer)
    with pytest.raises(FileExistsError):
        api.write_artifacts(output, result)
    assert output.is_dir()
    assert list(output.iterdir()) == []
    assert list(tmp_path.iterdir()) == [output]
