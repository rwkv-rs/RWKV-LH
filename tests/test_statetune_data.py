"""Opaque I/O admission fixtures; no scenario generation or formal training."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from rwkv_lh import statetune_core as core, statetune_data as data
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace, selector_intent_v7
from rwkv_lh.role_trace_artifacts import ARTIFACT_SCHEMA, build_artifacts, split_project_family, REQUIRED_COVERAGE
from rwkv_lh.token_budget import VOCAB_PATH, tokenizer


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n")
    return {"path": str(path), "sha256": core.sha256_file(path)}


def row():
    source, target = "opaque input fixture", "opaque target fixture"
    ids = tokenizer().encode(source)
    return {"schema_version": trace.EXTRACTION_SCHEMA, "sample_id": "mechanism-only",
        "role": "selector_intent", "split": "train", "recomputed": True,
        "input_protocol": selector_intent_v7.INPUT_SCHEMA_VERSION,
        "protocol_sha256": core.sha256_file(selector_intent_v7.__file__),
        "input_text": source, "target_text": target, "boundary_event_id": "mock-boundary",
        "input_checkpoint_id": "mock-checkpoint", "label_authority": "executed_fixture",
        "label_evidence_action_ids": ["mock-action"], "target_origin": "raw_model_output",
        "target_token_ids_source": "raw_generation", "target_token_ids": tokenizer().encode(target),
        "target_tokenizer_sha256": core.sha256_file(VOCAB_PATH),
        "context": {"token_ids_complete": True, "token_ids_source": "server_returned",
            "token_ids": [0, *ids], "input_bos_token_ids": [0], "reconstructed_token_ids": ids,
            "local_tokenizer_sha256": core.sha256_file(VOCAB_PATH), "prompt_text": source,
            "initial_state": {"model_sha256": "b" * 64}}}


def frozen(tmp_path):
    sample = row()
    training = write(tmp_path / "train.jsonl", sample)
    regression = write(tmp_path / "regression.json", {"opaque": "must never be parsed by trainer"})
    manifest = {"schema_version": data.DATASET_SCHEMA, "purpose": "frozen_role_training",
        "role": sample["role"], "input_protocol": sample["input_protocol"],
        "protocol_sha256": sample["protocol_sha256"], "model_sha256": "b" * 64,
        "tokenizer_sha256": sample["target_tokenizer_sha256"], "counts": {"train": 1},
        "candidate_audit": {"status": "valid", "quality_gates": {"coverage": True}},
        "train": {"file": "train.jsonl", "sha256": training["sha256"]},
        "regression": {"file": "regression.json", "sha256": regression["sha256"], "fingerprint": "a" * 64}}
    return manifest, write(tmp_path / "manifest.json", manifest)


def admit(reference, **kwargs):
    return data.admit_dataset(reference, role="selector_intent", expected_regression="a" * 64,
        model_sha256="b" * 64, context_tokens=16384, vocab_size=65536, bos_token_id=0, **kwargs)


def test_training_reads_only_train_and_hashes_regression_without_parsing(tmp_path, monkeypatch):
    manifest, reference = frozen(tmp_path)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        assert path.name != "regression.json", "training opened fixed regression text"
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    admitted, samples = admit(reference)
    assert admitted == manifest
    assert samples == [{"sample_id": "mechanism-only", "input_token_ids": row()["context"]["token_ids"],
                        "target_token_ids": row()["target_token_ids"]}]


@pytest.mark.parametrize("change,reason", [
    ({"split": "confirmation"}, "train row"),
    ({"input_protocol": "retired"}, "protocol"),
    ({"target_text": "changed"}, "target"),
    ({"recomputed": False}, "recomputed"),
    ({"label_authority": "pending_human_review"}, "label authority"),
    ({"label_evidence_action_ids": []}, "label authority"),
])
def test_invalid_train_record_cannot_enter_optimizer(change, reason):
    sample = {**row(), **change}
    with pytest.raises(ValueError, match=reason):
        data.normalize_row(sample, role="selector_intent", model_sha256="b" * 64,
                           context_tokens=16384, vocab_size=65536, bos_token_id=0)


@pytest.mark.parametrize("change,reason", [
    ({"token_ids_complete": False}, "complete server"),
    ({"input_bos_token_ids": []}, "BOS"),
    ({"token_ids": [True, 1]}, "invalid training token"),
    ({"initial_state": {"model_sha256": "c" * 64}}, "model"),
])
def test_input_trace_identity_is_not_guessed(change, reason):
    sample = row()
    sample["context"].update(change)
    with pytest.raises(ValueError, match=reason):
        data.normalize_row(sample, role="selector_intent", model_sha256="b" * 64,
                           context_tokens=16384, vocab_size=65536, bos_token_id=0)


def test_regression_mutation_and_dataset_member_escape_are_rejected(tmp_path):
    manifest, reference = frozen(tmp_path)
    (tmp_path / "regression.json").write_text("changed")
    with pytest.raises(ValueError, match="SHA-256"):
        admit(reference)
    manifest["regression"]["file"] = "../elsewhere"
    reference = write(tmp_path / "manifest.json", manifest)
    with pytest.raises(ValueError, match="direct regular"):
        admit(reference)


def test_freezer_reextracts_using_audit_location_before_publishing_dataset(tmp_path, monkeypatch):
    # Mock the already tested extractor at the artifact boundary. No actual
    # production source or role examples are created in this I/O unit test.
    source_ref = write(tmp_path / "source.json", {"unit_test_only": True})
    authorization = write(tmp_path / "owner.json", {"unit_test_only": True})
    candidate = {"schema": ARTIFACT_SCHEMA, "purpose": "audit_candidate_only", "status": "valid",
        "provenance": {"source_registration_sha256": source_ref["sha256"]},
        "counts_by_role": {"selector_intent": {"train": 1, "dev": 1, "confirmation": 1}},
        "regression_fingerprint": "a" * 64, "regression_reused": False}
    candidate_ref = write(tmp_path / "audit.json", candidate)
    registration = {"schema_version": data.FREEZE_SCHEMA, "role": "selector_intent",
        "authorization": authorization, "candidate_manifest": candidate_ref, "source_registration": source_ref,
        "minimum_counts": {"train": 1, "dev": 1, "confirmation": 1}, "regression_fingerprint": "a" * 64}
    registration_ref = write(tmp_path / "freeze.json", registration)
    monkeypatch.setattr(trace, "ROOT", tmp_path)
    def extract(source, output, **kwargs):
        trace.validate_output_path(output)
        output.mkdir(parents=True)
        write(output / "candidates.jsonl", row())
        write(output / "regression_candidate.json", {"unit_test_only": True})
        return candidate
    monkeypatch.setattr(trace, "extract_registration", extract)
    output = tmp_path / "data/datasets/mechanism-only"
    manifest = data.freeze_dataset(registration, registration_reference=registration_ref, output=output)
    assert manifest["schema_version"] == data.DATASET_SCHEMA
    assert (output / "train.jsonl").is_file()
    assert (output / "regression.json").is_file()
    assert not (output / "verified_candidates").exists()
    with pytest.raises(ValueError, match="already exists"):
        data.freeze_dataset(registration, registration_reference=registration_ref, output=output)


def _freeze_fixture(tmp_path, *, waiver_sha=None, rows=None, selection=None):
    """Build a freeze registration around mocked extraction artifacts."""
    source_ref = write(tmp_path / "source.json", {"unit_test_only": True})
    authorization = write(tmp_path / "owner.json", {"unit_test_only": True})
    provenance = {"source_registration_sha256": source_ref["sha256"]}
    if waiver_sha is not None:
        provenance["equivalence_waiver_sha256"] = waiver_sha
    candidate = build_artifacts(rows or _selection_rows(), provenance=provenance).manifest
    registration = {"schema_version": data.FREEZE_SCHEMA, "role": "selector_intent",
        "authorization": authorization, "candidate_manifest": write(tmp_path / "audit.json", candidate),
        "source_registration": source_ref,
        "minimum_counts": {"train": 1, "dev": 1, "confirmation": 1}, "regression_fingerprint": candidate["regression_fingerprint"]}
    if selection is not None:
        registration["row_selection"] = write(tmp_path / "selection.json", selection)
    return candidate, registration


def _mock_extract(monkeypatch, tmp_path, candidate, rows, observed_kwargs):
    def extract(source, output, **kwargs):
        observed_kwargs.update(kwargs)
        trace.validate_output_path(output)
        output.mkdir(parents=True)
        with (output / "candidates.jsonl").open("x") as handle:
            for item in rows:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        write(output / "regression_candidate.json", {"unit_test_only": True})
        return candidate
    monkeypatch.setattr(trace, "ROOT", tmp_path)
    monkeypatch.setattr(trace, "extract_registration", extract)


def _selection_rows():
    families = {}
    for index in range(200):
        family = f"opaque-selection-family-{index}"
        families.setdefault(split_project_family(family), family)
    rows = []
    for index, split in enumerate(["train", "train", "train", "dev", "confirmation"]):
        sample = row()
        sample["sample_id"] = f"RT-{index}"
        sample["split"] = split
        sample["project_family"] = families[split]
        sample["input_text"] = {"train":"A", "dev":"B", "confirmation":"C"}[split] * 100
        sample["coverage"] = {flag: True for flag in REQUIRED_COVERAGE}
        rows.append(sample)
    return rows


def test_freeze_replays_the_candidates_admission_waiver(tmp_path, monkeypatch):
    waiver_document = {"schema_version": trace.EQUIVALENCE_WAIVER_SCHEMA, "decision": "accept",
        "reviewers": ["MOCK-ONE", "MOCK-TWO"],
        "entries": [{"path": "rwkv_lh/harness.py", "frozen_sha256": "c" * 64, "current_sha256": "d" * 64,
                     "rationale": "MOCK waiver for freeze wiring test.",
                     "evidence_refs": ["data/experiments/MOCK/REPORT.md"]}]}
    waiver_ref = write(tmp_path / "waiver.json", waiver_document)
    candidate, registration = _freeze_fixture(tmp_path, waiver_sha=waiver_ref["sha256"])
    registration["equivalence_waiver"] = waiver_ref
    registration_ref = write(tmp_path / "freeze.json", registration)
    observed = {}
    _mock_extract(monkeypatch, tmp_path, candidate, _selection_rows(), observed)
    monkeypatch.setattr(trace, "read_equivalence_waiver",
                        lambda path, sha: {"rwkv_lh/harness.py": ("c" * 64, "d" * 64)})
    manifest = data.freeze_dataset(registration, registration_reference=registration_ref,
                                   output=tmp_path / "data/datasets/waiver-freeze")
    # The freeze re-extraction runs under exactly the pinned admission waiver.
    assert observed["equivalence_waiver"] == {"rwkv_lh/harness.py": ("c" * 64, "d" * 64)}
    assert observed["equivalence_waiver_sha256"] == waiver_ref["sha256"]
    assert manifest["equivalence_waiver_sha256"] == waiver_ref["sha256"]


def test_freeze_rejects_waiver_mismatch_in_either_direction(tmp_path, monkeypatch):
    # Candidate admitted under a waiver, freeze registers none.
    candidate, registration = _freeze_fixture(tmp_path, waiver_sha="e" * 64)
    registration_ref = write(tmp_path / "freeze.json", registration)
    with pytest.raises(ValueError, match="waiver the freeze does not register"):
        data.freeze_dataset(registration, registration_reference=registration_ref,
                            output=tmp_path / "data/datasets/missing-waiver")
    # Freeze registers a waiver whose sha differs from the candidate's admission.
    waiver_ref = write(tmp_path / "other_waiver.json", {"unit_test_only": True})
    (tmp_path / "second").mkdir()
    candidate2, registration2 = _freeze_fixture(tmp_path / "second", waiver_sha="e" * 64)
    registration2["equivalence_waiver"] = waiver_ref
    registration2_ref = write(tmp_path / "freeze2.json", registration2)
    with pytest.raises(ValueError, match="differs from the candidate's admission waiver"):
        data.freeze_dataset(registration2, registration_reference=registration2_ref,
                            output=tmp_path / "data/datasets/wrong-waiver")


def test_freeze_replays_a_registered_row_selection_exactly(tmp_path, monkeypatch):
    policy_evidence = write(tmp_path / "policy_result.json", {"unit_test_only": True})
    selection = {"schema_version": data.SELECTION_SCHEMA, "role": "selector_intent",
        "kept_sample_ids": ["RT-0", "RT-3", "RT-4"],
        "counts": {"train": 1, "dev": 1, "confirmation": 1},
        "policy_evidence_refs": [policy_evidence]}
    candidate, registration = _freeze_fixture(tmp_path, selection=selection)
    registration_ref = write(tmp_path / "freeze.json", registration)
    _mock_extract(monkeypatch, tmp_path, candidate, _selection_rows(), {})
    output = tmp_path / "data/datasets/selected-freeze"
    manifest = data.freeze_dataset(registration, registration_reference=registration_ref, output=output)
    # Only the selected train row is frozen; counts reflect the selection.
    train_rows = [json.loads(line) for line in (output / "train.jsonl").read_text().splitlines() if line]
    assert [item["sample_id"] for item in train_rows] == ["RT-0"]
    assert manifest["counts"] == {"train": 1, "dev": 1, "confirmation": 1}
    assert manifest["row_selection"] == registration["row_selection"]
    regression = json.loads((output / "regression.json").read_text())
    assert [r["sample_id"] for r in regression["samples_by_split"]["dev"]] == ["RT-3"]
    assert [r["sample_id"] for r in regression["samples_by_split"]["confirmation"]] == ["RT-4"]
    assert manifest["candidate_audit"]["row_count"] == 3


@pytest.mark.parametrize("corruption,reason", [
    ({"kept_sample_ids": ["RT-0", "RT-999", "RT-4"]}, "absent from re-extraction"),
    ({"counts": {"train": 2, "dev": 1, "confirmation": 1}}, "counts differ from kept IDs"),
    ({"counts": {"train": 1, "dev": 2, "confirmation": 0}}, "sample counts are not met"),
    ({"kept_sample_ids": ["RT-0", "RT-0", "RT-4"]}, "unique nonempty sample IDs"),
    ({"policy_evidence_refs": []}, "pinned policy evidence"),
    ({"role": "executor_args"}, "mismatched row selection"),
])
def test_freeze_rejects_selection_that_does_not_replay(tmp_path, monkeypatch, corruption, reason):
    policy_evidence = write(tmp_path / "policy_result.json", {"unit_test_only": True})
    selection = {"schema_version": data.SELECTION_SCHEMA, "role": "selector_intent",
        "kept_sample_ids": ["RT-0", "RT-3", "RT-4"],
        "counts": {"train": 1, "dev": 1, "confirmation": 1},
        "policy_evidence_refs": [policy_evidence], **corruption}
    candidate, registration = _freeze_fixture(tmp_path, selection=selection)
    registration_ref = write(tmp_path / "freeze.json", registration)
    _mock_extract(monkeypatch, tmp_path, candidate, _selection_rows(), {})
    with pytest.raises(ValueError, match=reason):
        data.freeze_dataset(registration, registration_reference=registration_ref,
                            output=tmp_path / "data/datasets/bad-selection")


def test_failed_reextraction_does_not_publish_dataset(tmp_path, monkeypatch):
    source_ref = write(tmp_path / "source.json", {"unit_test_only": True})
    candidate = {"schema": ARTIFACT_SCHEMA, "purpose": "audit_candidate_only", "status": "valid",
        "provenance": {"source_registration_sha256": source_ref["sha256"]},
        "counts_by_role": {"selector_intent": {"train": 1, "dev": 1, "confirmation": 1}},
        "regression_fingerprint": "a" * 64, "regression_reused": False}
    registration = {"schema_version": data.FREEZE_SCHEMA, "role": "selector_intent",
        "authorization": source_ref, "candidate_manifest": write(tmp_path / "audit.json", candidate),
        "source_registration": source_ref, "minimum_counts": {"train": 1, "dev": 1, "confirmation": 1},
        "regression_fingerprint": "a" * 64}
    registration_ref = write(tmp_path / "freeze.json", registration)
    monkeypatch.setattr(trace, "ROOT", tmp_path)
    monkeypatch.setattr(trace, "extract_registration", lambda *a, **k: {**candidate, "status": "invalid"})
    output = tmp_path / "data/datasets/mechanism-only"
    with pytest.raises(ValueError, match="re-extraction"):
        data.freeze_dataset(registration, registration_reference=registration_ref, output=output)
    assert not output.exists()
