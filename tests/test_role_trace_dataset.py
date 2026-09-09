"""Source admission and immutable trace checks, never role training fixtures."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest


def _api():
    from rwkv_lh.goal_state_protocols import role_trace_dataset_v1
    return role_trace_dataset_v1


def test_pipeline_rejects_protected_source_before_opening(tmp_path, monkeypatch):
    api = _api()
    protected = tmp_path / "data" / "acceptance" / "sealed.json"
    original = Path.read_bytes
    def sentinel(path):
        if path == protected:
            pytest.fail("Protected source was opened")
        return original(path)
    monkeypatch.setattr(Path, "read_bytes", sentinel)
    with pytest.raises(api.DatasetIntegrityError, match="protected"):
        api.read_registration(protected)


def test_pipeline_rejects_unknown_source_schema(tmp_path):
    api = _api()
    path = tmp_path / "registration.json"
    path.write_text(json.dumps({"schema_version": "retired", "source_runs": []}))
    with pytest.raises(api.DatasetIntegrityError, match="schema"):
        api.read_registration(path)


def test_pipeline_rejects_synthetic_source_without_reading_artifacts(tmp_path):
    api = _api()
    record = {
        "run_id": "RUN", "source_run_id": "BASELINE", "project_family": "project-a",
        "suite": "realprojectdevv1", "source_kind": "authored_reference",
        "collection_mode": "all_zero", "artifacts": {},
    }
    with pytest.raises(api.DatasetIntegrityError, match="production_trace"):
        api.load_source_run(record, base_dir=tmp_path)


def test_pipeline_requires_complete_artifact_set_before_reading(tmp_path):
    api = _api()
    record = {
        "run_id": "RUN", "source_run_id": "BASELINE", "project_family": "project-a",
        "suite": "realprojectdevv1", "source_kind": "production_trace",
        "collection_mode": "all_zero", "artifacts": {},
    }
    with pytest.raises(api.DatasetIntegrityError, match="artifact"):
        api.load_source_run(record, base_dir=tmp_path)


def test_pipeline_refuses_off_manifest_bytes(tmp_path):
    api = _api()
    path = tmp_path / "trace.json"
    path.write_text("[]")
    with pytest.raises(api.DatasetIntegrityError, match="SHA"):
        api.read_artifact({"path": str(path), "sha256": "0" * 64}, tmp_path)


def test_pipeline_refuses_symlink_into_protected_source(tmp_path):
    api = _api()
    target = tmp_path / "data" / "acceptance" / "sealed.json"
    target.parent.mkdir(parents=True)
    link = tmp_path / "ordinary.json"
    link.symlink_to(target)
    with pytest.raises(api.DatasetIntegrityError, match="protected"):
        api.read_artifact({"path": str(link), "sha256": "0" * 64}, tmp_path)


def test_pipeline_cannot_create_formal_dataset_version(tmp_path):
    api = _api()
    destination = tmp_path / "data" / "datasets" / "new_role_v1"
    with pytest.raises(api.DatasetIntegrityError, match="audit output"):
        api.validate_output_path(destination)
    assert not destination.exists()


def test_pipeline_verifies_raw_token_stream_instead_of_retokenizing_display_text():
    api = _api()
    from rwkv_lh.token_budget import tokenizer
    text = '{"function":"read_file","params":{"path":"a.py"}}'
    raw = {
        "raw_output": text, "raw_output_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "raw_token_ids": tokenizer().encode(text), "finish_reason": "stop",
        "state_profile_id": "zero", "state_profile_sha256": "0" * 64,
        "postprocessed": False,
    }
    assert api.validate_raw_generation(raw)[0] == text
    raw["raw_token_ids"] = tokenizer().encode("different")
    with pytest.raises(api.DatasetIntegrityError, match="token"):
        api.validate_raw_generation(raw)


@pytest.mark.parametrize("finish", ["length", "error", ""])
def test_pipeline_excludes_non_natural_generation(finish):
    api = _api()
    with pytest.raises(api.SampleExcluded, match="finish_reason"):
        api.validate_raw_generation({"finish_reason": finish})


def test_pipeline_missing_token_ids_are_exclusion_not_guessed_label():
    api = _api()
    with pytest.raises(api.SampleExcluded, match="token"):
        api.validate_raw_generation({"finish_reason": "stop", "raw_output": "{}", "raw_token_ids": []})


def test_pipeline_family_registration_is_unique(tmp_path):
    api = _api()
    path = tmp_path / "registration.json"
    run = {"run_id": "R", "source_run_id": "BASE", "project_family": "family-a"}
    path.write_text(json.dumps({"schema_version": api.SOURCE_REGISTRATION_SCHEMA,
                                "source_runs": [run, dict(run, project_family="family-b")]}))
    with pytest.raises(api.DatasetIntegrityError, match="duplicate"):
        api.read_registration(path)


def test_pipeline_json_duplicate_keys_are_rejected(tmp_path):
    api = _api()
    path = tmp_path / "registration.json"
    path.write_text('{"schema_version":"a","schema_version":"b"}')
    with pytest.raises(api.DatasetIntegrityError, match="duplicate"):
        api.read_registration(path)
