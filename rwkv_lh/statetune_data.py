"""Freeze verified production candidates; training reads only the train split."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping

from rwkv_lh import statetune_core as core
from rwkv_lh import role_trace_selection as selection_api
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace
from rwkv_lh.role_trace_artifacts import ARTIFACT_SCHEMA, _canonical_bytes, _publish_no_replace, build_artifacts
from rwkv_lh.token_budget import VOCAB_PATH, tokenizer

FREEZE_SCHEMA = "rwkv-lh.statetune-data-freeze.v1"
DATASET_SCHEMA = "rwkv-lh.statetune-role-dataset.v1"
SELECTION_SCHEMA = "rwkv-lh.statetune-row-selection.v1"


def sealed(reference: Mapping[str, Any]) -> dict:
    core.require(isinstance(reference, Mapping) and set(reference) == {"path", "sha256"},
                 "an exact sealed reference is required")
    trace._source_path(Path(reference["path"]))
    return core.read_sealed_json(reference["path"], reference["sha256"])


def _member(root: Path, reference: Mapping[str, Any]) -> Path:
    name = reference.get("file")
    core.require(isinstance(name, str) and Path(name).name == name and name not in {"", ".", ".."},
                 "dataset member must be a direct regular file")
    return core.verify_file(root / name, reference["sha256"])


def _protocol(role: str) -> tuple[str, str]:
    if role == "direct_actor":
        from rwkv_lh.direct_trace_data import protocol_identity
        return protocol_identity()
    core.require(role in trace.ROLE_MODULES, "unknown training role")
    module = trace.ROLE_MODULES[role]
    return module.INPUT_SCHEMA_VERSION, core.sha256_file(module.__file__)


def normalize_row(row: Mapping, *, role: str, model_sha256: str, context_tokens: int,
                  vocab_size: int, bos_token_id: int, expected_split: str = "train") -> dict:
    if role == "direct_actor":
        from rwkv_lh.direct_trace_data import normalize_direct_row
        return normalize_direct_row(row, model_sha256=model_sha256, context_tokens=context_tokens,
                                    vocab_size=vocab_size, bos_token_id=bos_token_id, expected_split=expected_split)
    protocol, protocol_sha = _protocol(role)
    core.require(expected_split in {"train", "dev", "confirmation"}, "unknown registered split")
    core.require(row.get("schema_version") == trace.EXTRACTION_SCHEMA and row.get("role") == role
                 and row.get("recomputed") is True and row.get("split") == expected_split,
                 f"a recomputed production {expected_split} row is required")
    core.require((row.get("input_protocol"), row.get("protocol_sha256")) == (protocol, protocol_sha),
                 "training row protocol differs")
    context = row.get("context", {})
    core.require(context.get("token_ids_complete") is True and context.get("token_ids_source") == "server_returned",
                 "complete server input token IDs are required; no BOS reconstruction")
    vocab_sha = core.sha256_file(VOCAB_PATH)
    core.require(context.get("local_tokenizer_sha256") == vocab_sha == row.get("target_tokenizer_sha256"),
                 "training tokenizer differs")
    core.require(context.get("initial_state", {}).get("model_sha256") == model_sha256,
                 "training source model differs")
    source, target = context.get("token_ids"), row.get("target_token_ids")
    core.require(all(isinstance(ids, list) and ids and all(type(t) is int and 0 <= t < vocab_size for t in ids)
                     for ids in (source, target)), "invalid training token IDs")
    core.require(context.get("input_bos_token_ids") == [bos_token_id] and source[:1] == [bos_token_id]
                 and source[1:] == context.get("reconstructed_token_ids"), "server input BOS/token alignment differs")
    core.require(tokenizer().decode_bytes(source[1:]).decode("utf-8") == row.get("input_text")
                 and row.get("input_text") == context.get("prompt_text"), "training input text differs from token trace")
    core.require(tokenizer().decode_bytes(target).decode("utf-8") == row.get("target_text"),
                 "training target differs from token trace")
    core.require(len(source) + len(target) - 1 <= context_tokens, "sample exceeds context; truncation is forbidden")
    core.require(bool(row.get("sample_id")) and bool(row.get("boundary_event_id"))
                 and bool(row.get("input_checkpoint_id")) and bool(row.get("label_authority")),
                 "training sample lacks source boundary or label authority")
    authority = row["label_authority"]
    reviewed = authority == "human_double_review" and isinstance(row.get("human_reviewers"), list) \
        and len(set(row["human_reviewers"])) >= 2
    executed = authority == "executed_fixture" and role in {"selector_intent", "executor_args"} \
        and bool(row.get("label_evidence_action_ids"))
    contracted = authority == "planner_contract" and role == "selector_intent"
    core.require(reviewed or executed or contracted, "training label authority lacks admissible evidence")
    return {"sample_id": row["sample_id"], "input_token_ids": list(source), "target_token_ids": list(target)}


def _read_selection(registration: Mapping, candidate: Mapping, role: str) -> dict | None:
    """Load the sealed post-extraction row selection, if one is registered.

    A selection is the registered outcome of the preregistered review and
    similarity-dedup pipeline (e.g. 210→20). It never adds or edits rows —
    it only names which re-extracted sample IDs survive into training — and
    its own evidence chain (dispositions, dedup policy result) is pinned by
    sha inside the document.
    """
    reference = registration.get("row_selection")
    if reference is None:
        return None
    return selection_api.read_selection(reference, role)


def freeze_dataset(registration: Mapping, *, registration_reference: Mapping, output: Path) -> dict:
    """An explicit owner-scoped freeze, re-extracted from the original trace.

    The registration pins candidate, source, regression, minimum counts and
    written authorization. A valid audit alone never publishes a dataset.
    """
    if registration.get("role") == "direct_actor":
        from rwkv_lh.direct_trace_data import freeze_direct_dataset
        return freeze_direct_dataset(registration, registration_reference=registration_reference, output=output)
    core.require(registration.get("schema_version") == FREEZE_SCHEMA, "unknown dataset freeze registration")
    role = registration["role"]
    protocol, protocol_sha = _protocol(role)
    core.verify_file(registration["authorization"]["path"], registration["authorization"]["sha256"])
    candidate_ref, source_ref = registration["candidate_manifest"], registration["source_registration"]
    candidate = sealed(candidate_ref)
    core.require(candidate.get("schema") == ARTIFACT_SCHEMA and candidate.get("purpose") == "audit_candidate_only"
                 and candidate.get("status") == "valid", "candidate quality audit is not valid")
    core.require(candidate.get("provenance", {}).get("source_registration_sha256") == source_ref["sha256"],
                 "candidate source registration differs")
    source_document = sealed(source_ref)
    selected_source = source_document.get("schema_version") == selection_api.SOURCE_SCHEMA
    waiver_ref = registration.get("equivalence_waiver")
    waiver = None
    if waiver_ref is not None:
        # The freeze must replay exactly the admission the candidate used:
        # same double-reviewed waiver document, pinned by the same sha.
        core.require(candidate.get("provenance", {}).get("equivalence_waiver_sha256") == waiver_ref["sha256"],
                     "freeze waiver differs from the candidate's admission waiver")
        waiver = trace.read_equivalence_waiver(Path(waiver_ref["path"]), waiver_ref["sha256"])
    else:
        core.require(not candidate.get("provenance", {}).get("equivalence_waiver_sha256"),
                     "candidate was admitted under a waiver the freeze does not register")
    selection = _read_selection(registration, candidate, role)
    if selected_source:
        core.require(waiver_ref is None, "selected sources register waivers per raw source group")
        core.require(selection is not None and registration["row_selection"] == source_document["row_selection"]
                     == candidate.get("provenance", {}).get("row_selection"),
                     "selected candidate membership registration differs")
    counts = candidate["counts_by_role"]
    core.require(set(counts) == {role}, "freeze must contain exactly the current role")
    effective_counts = dict(selection["counts"]) if selection is not None else dict(counts[role])
    minimum = registration["minimum_counts"]
    core.require(set(minimum) == {"train", "dev", "confirmation"}
                 and all(type(n) is int and n > 0 and effective_counts[split] >= n for split, n in minimum.items()),
                 "pre-registered role sample counts are not met")
    fingerprint = registration["regression_fingerprint"]
    core.require(candidate["regression_fingerprint"] == fingerprint, "frozen regression fingerprint differs")
    prior_ref = registration.get("prior_regression")
    core.require(bool(prior_ref) == candidate["regression_reused"], "regression reuse registration differs")
    prior = sealed(prior_ref) if prior_ref else None
    output = Path(output).absolute()
    trace._source_path(output)
    core.require(not output.exists() and not output.is_symlink(), "dataset output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.freeze-", dir=output.parent))
    audit_parent = trace.ROOT / "data/experiments"
    audit_parent.mkdir(parents=True, exist_ok=True)
    audit_temporary = Path(tempfile.mkdtemp(prefix=".statetune-freeze-audit-", dir=audit_parent))
    try:
        audit_root = audit_temporary / "verified_candidates"
        if selected_source:
            reproduced = selection_api.extract_selected_registration(Path(source_ref["path"]), audit_root,
                roles=[role], prior_regression=prior,
                expected_regression_fingerprint=fingerprint if prior else None)
        else:
            reproduced = trace.extract_registration(Path(source_ref["path"]), audit_root, roles=[role],
                prior_regression=prior, expected_regression_fingerprint=fingerprint if prior else None,
                equivalence_waiver=waiver,
                equivalence_waiver_sha256=waiver_ref["sha256"] if waiver is not None else None)
        core.require(reproduced == candidate, "candidate audit differs from production re-extraction")
        all_rows = [json.loads(line) for line in (audit_root / "candidates.jsonl").read_text().splitlines() if line]
        core.require(all(row.get("context", {}).get("token_ids_complete") is True for row in all_rows),
                     "dataset contains incomplete server input token traces")
        if selection is not None and not selected_source:
            all_rows = selection_api.select_rows(all_rows, selection)
            audit_rows = all_rows
            if prior is not None:
                expected = [row for split in ("dev", "confirmation") for row in prior["samples_by_split"][split]]
                core.require(sorted((r for r in all_rows if r["split"] != "train"), key=lambda r:r["sample_id"])
                             == sorted(expected, key=lambda r:r["sample_id"]),
                             "selected regression members differ from pinned prior")
                audit_rows = [row for row in all_rows if row["split"] == "train"]
            effective = build_artifacts(audit_rows, provenance=candidate["provenance"],
                coverage_requirements=candidate.get("coverage_requirements"), prior_regression=prior,
                expected_regression_fingerprint=fingerprint if prior else None)
            core.require(effective.manifest["status"] == "valid", "selected candidate quality audit is not valid")
            core.require(effective.manifest["regression_fingerprint"] == fingerprint,
                         "selected regression differs; re-register a fully audited selected-source candidate")
            candidate = effective.manifest
            (audit_root / "regression_candidate.json").write_bytes(
                _canonical_bytes(effective.regression_candidate) + b"\n")
        model_shas = {row["context"]["initial_state"]["model_sha256"] for row in all_rows}
        core.require(len(model_shas) == 1, "one role dataset cannot mix model identities")
        training = [row for row in all_rows if row["split"] == "train"]
        (staging / "train.jsonl").write_bytes(b"".join(_canonical_bytes(row) + b"\n" for row in training))
        shutil.copyfile(audit_root / "regression_candidate.json", staging / "regression.json")
        manifest = {"schema_version": DATASET_SCHEMA, "purpose": "frozen_role_training",
            "role": role, "input_protocol": protocol, "protocol_sha256": protocol_sha,
            "tokenizer_sha256": core.sha256_file(VOCAB_PATH), "model_sha256": next(iter(model_shas)),
            "freeze_registration": dict(registration_reference), "authorization": registration["authorization"],
            "counts": effective_counts, "candidate_audit": candidate,
            "equivalence_waiver_sha256": waiver_ref["sha256"] if waiver is not None else None,
            "row_selection": dict(registration["row_selection"]) if selection is not None else None,
            "train": {"file": "train.jsonl", "sha256": core.sha256_file(staging / "train.jsonl")},
            "regression": {"file": "regression.json", "sha256": core.sha256_file(staging / "regression.json"),
                           "fingerprint": fingerprint}}
        (staging / "manifest.json").write_bytes(_canonical_bytes(manifest) + b"\n")
        _publish_no_replace(staging, output)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)
        shutil.rmtree(audit_temporary)


def admit_dataset(reference: Mapping, *, role: str, expected_regression: str, model_sha256: str,
                  context_tokens: int, vocab_size: int, bos_token_id: int) -> tuple[dict, list[dict]]:
    manifest = sealed(reference)
    core.require(manifest.get("schema_version") == DATASET_SCHEMA and manifest.get("purpose") == "frozen_role_training",
                 "training requires a frozen role dataset")
    protocol, protocol_sha = _protocol(role)
    core.require((manifest.get("role"), manifest.get("input_protocol"), manifest.get("protocol_sha256"))
                 == (role, protocol, protocol_sha), "frozen dataset role/protocol differs")
    core.require(manifest["model_sha256"] == model_sha256 and manifest["tokenizer_sha256"] == core.sha256_file(VOCAB_PATH),
                 "frozen dataset model/tokenizer differs")
    core.require(manifest["regression"]["fingerprint"] == expected_regression, "immutable regression differs")
    core.require(manifest["candidate_audit"]["status"] == "valid"
                 and all(manifest["candidate_audit"]["quality_gates"].values()), "frozen candidate audit failed")
    root = Path(reference["path"]).parent
    # Hash the regression bytes only. No evaluation text or labels enter training.
    _member(root, manifest["regression"])
    train_path = _member(root, manifest["train"])
    rows = [normalize_row(json.loads(line), role=role, model_sha256=model_sha256, context_tokens=context_tokens,
                          vocab_size=vocab_size, bos_token_id=bos_token_id)
            for line in train_path.read_text().splitlines() if line]
    core.require(len(rows) == manifest["counts"]["train"] > 0
                 and len({row["sample_id"] for row in rows}) == len(rows), "train sample counts or unique identities differ")
    return manifest, rows
