"""Deterministic audit artifacts for already verified production-trace samples.

This module does not extract role examples, invent labels, read regression files,
freeze datasets, or authorize training. The caller must prove provenance, rebuild
inputs with the production builders, and derive the coverage flags from durable
facts before passing samples here. Every written record is an audit candidate.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import ctypes
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any


ROLES = (
    "selector_intent", "executor_args", "auditor_step", "finalizer_answer",
    "auditor_final",
)
SPLITS = ("train", "dev", "confirmation")
SPLIT_SALT = "rwkv-lh-role-trace-family-v1"
SPLIT_BUCKETS = 10_000
SPLIT_BOUNDARIES = (8_000, 9_000, 10_000)
REQUIRED_COVERAGE = (
    "failed_last_action", "nonempty_error_type", "directory_target", "py_root",
    "json_root", "directory_root", "mutate", "execute", "missing_target",
)
SIMILARITY_THRESHOLD = 0.95
NGRAM_BYTES = 5
ARTIFACT_SCHEMA = "rwkv-lh-role-trace-artifacts-v1"
REGRESSION_SCHEMA = "rwkv-lh-role-trace-regression-candidate-v1"


@dataclass(frozen=True)
class ArtifactBundle:
    samples_by_split: dict[str, list[dict[str, Any]]]
    manifest: dict[str, Any]
    regression_candidate: dict[str, Any] | None


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("artifact values must be finite UTF-8 JSON") from exc


def _copy_json(value: Any) -> Any:
    return json.loads(_canonical_bytes(value))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def split_project_family(project_family: str) -> str:
    """Assign an exact family id to the fixed 80/10/10 SHA-256 partition."""
    if not isinstance(project_family, str) or not project_family.strip():
        raise ValueError("project_family must be nonempty text")
    digest = hashlib.sha256(
        SPLIT_SALT.encode("utf-8") + b"\0" + project_family.encode("utf-8")
    ).hexdigest()
    bucket = int(digest, 16) % SPLIT_BUCKETS
    for split, end in zip(SPLITS, SPLIT_BOUNDARIES, strict=True):
        if bucket < end:
            return split
    raise AssertionError("split boundaries do not cover every bucket")


def _split_algorithm() -> dict[str, Any]:
    return {
        "name": "sha256_project_family_modulo",
        "salt": SPLIT_SALT,
        "input": "UTF8(salt) + 0x00 + UTF8(exact_project_family)",
        "digest_integer": "unsigned big-endian, full 256-bit digest",
        "modulo": SPLIT_BUCKETS,
        "bucket_ranges": {
            "train": [0, 7999], "dev": [8000, 8999], "confirmation": [9000, 9999],
        },
        "ratios": {"train": 0.8, "dev": 0.1, "confirmation": 0.1},
    }


def _grams(text: str) -> Counter[bytes]:
    raw = text.encode("utf-8")
    return Counter(raw[index:index + NGRAM_BYTES] for index in range(len(raw) - NGRAM_BYTES + 1))


def _cosine_parts(left: Counter[bytes], right: Counter[bytes]) -> tuple[int, int, int]:
    if len(left) > len(right):
        left, right = right, left
    dot = sum(count * right.get(gram, 0) for gram, count in left.items())
    return dot, sum(count * count for count in left.values()), sum(count * count for count in right.values())


def byte_5gram_cosine(left: str, right: str) -> float:
    """Cosine of unpadded UTF-8 byte 5-gram counts; identical short inputs are 1."""
    dot, left_sq, right_sq = _cosine_parts(_grams(left), _grams(right))
    if not left_sq or not right_sq:
        return float(left == right)
    return min(1.0, dot / math.sqrt(left_sq * right_sq))


def _validated_row(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("each sample must be a JSON object")
    row = _copy_json(dict(raw))
    for field in ("sample_id", "role", "project_family", "input_text", "target_text"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            raise ValueError(f"sample field {field} must be nonempty text")
    if row["role"] not in ROLES:
        raise ValueError(f"unknown sample role: {row['role']}")
    coverage = row.get("coverage")
    if not isinstance(coverage, dict) or any(
        type(coverage.get(flag)) is not bool for flag in REQUIRED_COVERAGE
    ):
        raise ValueError("coverage must contain every required flag as a boolean")
    expected_split = split_project_family(row["project_family"])
    if "split" in row and row["split"] != expected_split:
        raise ValueError("sample split disagrees with fixed project-family assignment")
    row["split"] = expected_split
    return row


def validate_coverage_requirements(value: Any, roles: list[str]) -> dict[str, list[str]]:
    if not isinstance(value, Mapping) or set(value) != set(roles):
        raise ValueError("coverage requirements must name exactly the requested roles")
    result = {}
    for role, flags in value.items():
        if (role not in ROLES or not isinstance(flags, list) or not flags
                or any(not isinstance(flag, str) or flag not in REQUIRED_COVERAGE for flag in flags)
                or len(flags) != len(set(flags))):
            raise ValueError("coverage requirements must contain nonempty unique known flags")
        result[role] = sorted(flags)
    return dict(sorted(result.items()))


def _regression_candidate(samples_by_split: Mapping[str, list[dict[str, Any]]], roles: list[str],
                          coverage_requirements: Mapping[str, list[str]], collection_condition: Mapping) -> dict[str, Any]:
    payload = {
        "schema": REGRESSION_SCHEMA,
        "purpose": "candidate_only_owner_freeze_required",
        "roles": roles,
        "coverage_requirements": _copy_json(coverage_requirements),
        "collection_condition": _copy_json(collection_condition),
        "split_algorithm": _split_algorithm(),
        "samples_by_split": {
            split: _copy_json(samples_by_split[split]) for split in ("dev", "confirmation")
        },
    }
    return {**payload, "fingerprint": _sha256(_canonical_bytes(payload))}


def _validate_prior(prior: Mapping[str, Any], expected: str | None) -> dict[str, Any]:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("a pinned expected_regression_fingerprint is required for reuse")
    copied = _copy_json(dict(prior))
    fingerprint = copied.pop("fingerprint", None)
    if fingerprint != expected or _sha256(_canonical_bytes(copied)) != expected:
        raise ValueError("regression fingerprint mismatch; dev/confirmation are immutable")
    if copied.get("schema") != REGRESSION_SCHEMA or copied.get("split_algorithm") != _split_algorithm():
        raise ValueError("regression schema or split algorithm differs")
    roles = copied.get("roles")
    if not isinstance(roles, list) or not roles or roles != sorted(set(roles)) or any(role not in ROLES for role in roles):
        raise ValueError("regression roles are malformed")
    validate_coverage_requirements(copied.get("coverage_requirements"), roles)
    splits = copied.get("samples_by_split")
    if not isinstance(splits, dict) or set(splits) != {"dev", "confirmation"}:
        raise ValueError("regression requires the complete dev/confirmation identity")
    for split, rows in splits.items():
        if not isinstance(rows, list):
            raise ValueError("regression rows must be lists")
        for raw in rows:
            checked = _validated_row(raw)
            if checked != raw or checked["split"] != split or checked["role"] not in roles:
                raise ValueError("regression row identity or split changed")
        if any(not any(row["role"] == role for row in rows) for role in roles):
            raise ValueError("regression requires nonempty dev/confirmation for each role")
    copied["fingerprint"] = fingerprint
    return copied


def _similarity_audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    vectors = [_grams(row["input_text"]) for row in rows]
    comparisons = 0
    violations = []
    for left_index, left in enumerate(rows):
        for right_index in range(left_index + 1, len(rows)):
            right = rows[right_index]
            if left["role"] != right["role"] or left["split"] == right["split"]:
                continue
            comparisons += 1
            dot, left_sq, right_sq = _cosine_parts(vectors[left_index], vectors[right_index])
            if not left_sq or not right_sq:
                exceeds = left["input_text"] == right["input_text"]
                score = float(exceeds)
            else:
                # Exact integer comparison avoids float drift at the fixed 0.95 boundary.
                exceeds = dot * dot * 10_000 >= 9_025 * left_sq * right_sq
                score = min(1.0, dot / math.sqrt(left_sq * right_sq))
            if exceeds:
                violations.append({
                    "role": left["role"], "left_sample_id": left["sample_id"],
                    "right_sample_id": right["sample_id"], "left_split": left["split"],
                    "right_split": right["split"], "cosine": round(score, 12),
                })
    return {"compared_pairs": comparisons, "violations": violations}


def build_artifacts(
    samples: Iterable[Mapping[str, Any]], *, provenance: Mapping[str, Any],
    prior_regression: Mapping[str, Any] | None = None,
    expected_regression_fingerprint: str | None = None,
    coverage_requirements: Mapping[str, list[str]] | None = None,
) -> ArtifactBundle:
    """Audit verified rows; later rounds may add train rows and reuse pinned regression.

    Required row fields are sample_id, role, project_family, input_text (the full
    reconstructed context), target_text, and coverage (all REQUIRED_COVERAGE bools).
    Additional provenance/evidence fields are preserved in the row's identity.
    The optional prior regression is passed in memory: this function never opens
    held-out data. Its independent fingerprint must come from the prior freeze's
    registration, not be recomputed from the supplied rows.
    """
    rows = [_validated_row(row) for row in samples]
    provenance_copy = _copy_json(dict(provenance))
    prior = None
    if prior_regression is not None:
        prior = _validate_prior(prior_regression, expected_regression_fingerprint)
        if any(row["split"] != "train" for row in rows):
            raise ValueError("later rounds may add only train samples")
        if any(row["role"] not in prior["roles"] for row in rows):
            raise ValueError("later rounds cannot change regression roles")
        rows += [row for split in ("dev", "confirmation") for row in prior["samples_by_split"][split]]
    elif expected_regression_fingerprint is not None:
        raise ValueError("expected_regression_fingerprint requires prior_regression")
    ids = [row["sample_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("sample_id must be globally unique")
    rows.sort(key=lambda row: (row["role"], row["project_family"], row["sample_id"]))
    roles = sorted({row["role"] for row in rows})
    requested_roles = provenance_copy.get("requested_roles", roles)
    if (not isinstance(requested_roles, list) or any(role not in ROLES for role in requested_roles)
            or len(set(requested_roles)) != len(requested_roles)):
        raise ValueError("requested_roles must be a role list")
    requirements = validate_coverage_requirements(
        coverage_requirements if coverage_requirements is not None else
        {role: list(REQUIRED_COVERAGE) for role in requested_roles}, requested_roles,
    )
    if prior is not None and requirements != prior["coverage_requirements"]:
        raise ValueError("coverage requirements are immutable with the frozen regression")
    contracts = {_canonical_bytes(row.get("role_data_collection")) for row in provenance_copy.get("source_runs", [])}
    if len(contracts) > 1:
        raise ValueError("one role dataset cannot mix different frozen upstream State conditions")
    collection_condition = {
        "coverage_scope_sha256": provenance_copy.get("coverage_scope_sha256"),
        "role_data_collection": json.loads(next(iter(contracts))) if contracts else None,
    }
    if prior is not None and collection_condition != prior.get("collection_condition"):
        raise ValueError("collection conditions are immutable with the frozen regression")
    samples_by_split = {split: [row for row in rows if row["split"] == split] for split in SPLITS}
    counts = {role: {split: sum(row["role"] == role for row in samples_by_split[split]) for split in SPLITS} for role in roles}
    coverage = {
        role: {flag: sum(row["coverage"][flag] for row in rows if row["role"] == role) for flag in REQUIRED_COVERAGE}
        for role in roles
    }
    similarity = _similarity_audit(rows)
    gates = {
        "nonempty_samples": bool(rows),
        "requested_roles_present": bool(requested_roles) and set(requested_roles) == set(roles),
        "nonempty_role_splits": bool(roles) and all(count > 0 for splits in counts.values() for count in splits.values()),
        "required_coverage_per_role": bool(requirements) and all(
            coverage.get(role, {}).get(flag, 0) > 0 for role, flags in requirements.items() for flag in flags),
        "cross_split_similarity": not similarity["violations"],
    }
    valid = all(gates.values())
    candidate = _regression_candidate(samples_by_split, roles, requirements, collection_condition) if valid else None
    if prior is not None and candidate is not None and candidate != prior:
        raise ValueError("reused regression fingerprint changed")
    manifest = {
        "schema": ARTIFACT_SCHEMA, "purpose": "audit_candidate_only",
        "status": "valid" if valid else "invalid", "provenance": provenance_copy,
        "recomputed_row_count": provenance_copy.get("recomputed_rows"),
        "row_count": len(rows), "counts_by_role": counts,
        "label_authority_counts_by_role": {
            role: dict(sorted(Counter(row.get("label_authority", "unreported")
                                      for row in rows if row["role"] == role).items()))
            for role in roles
        },
        "split_algorithm": _split_algorithm(),
        "similarity_parameters": {
            "name": "count_vector_cosine", "encoding": "utf-8", "ngram_bytes": NGRAM_BYTES,
            "padding": False, "text_field": "input_text", "comparison_scope": "same_role_cross_split",
            "threshold": SIMILARITY_THRESHOLD, "rejection_comparison": ">=",
            "zero_norm": "exact_text_equal_is_one_otherwise_zero",
        },
        "similarity_audit": similarity, "coverage_audit": coverage,
        "required_coverage": list(REQUIRED_COVERAGE), "quality_gates": gates,
        "coverage_requirements": requirements,
        "regression_reused": prior is not None,
        "regression_fingerprint": candidate["fingerprint"] if candidate is not None else None,
    }
    return ArtifactBundle(samples_by_split, manifest, candidate)


def _publish_no_replace(staging: Path, output: Path) -> None:
    """Linux atomic directory publication with RENAME_NOREPLACE (also race-safe)."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "atomic no-replace directory rename is required")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    if renameat2(-100, os.fsencode(staging), -100, os.fsencode(output), 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(output))


def write_artifacts(output_dir: str | Path, bundle: ArtifactBundle) -> dict[str, Any]:
    """Write an audit directory atomically; an existing path is never replaced."""
    output = Path(output_dir).absolute()
    if os.path.lexists(output):
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        rows = [row for split in SPLITS for row in bundle.samples_by_split[split]]
        files = {"candidates.jsonl": b"".join(_canonical_bytes(row) + b"\n" for row in rows)}
        if bundle.regression_candidate is not None:
            files["regression_candidate.json"] = _canonical_bytes(bundle.regression_candidate) + b"\n"
        manifest = _copy_json(bundle.manifest)
        review_queue = []
        for exclusion in manifest.get("provenance", {}).get("exclusions", []):
            row = exclusion.pop("review_candidate", None)
            if row is not None:
                review_queue.append(row)
                exclusion["review_candidate_id"] = row["sample_id"]
        if review_queue:
            files["review_queue.jsonl"] = b"".join(_canonical_bytes(row) + b"\n" for row in review_queue)
        manifest["review_candidate_counts_by_role"] = dict(sorted(Counter(row["role"] for row in review_queue).items()))
        manifest["files"] = {
            filename: {"sha256": _sha256(content), "bytes": len(content)}
            for filename, content in sorted(files.items())
        }
        files["manifest.json"] = _canonical_bytes(manifest) + b"\n"
        files["manifest.sha256"] = (_sha256(files["manifest.json"]) + "  manifest.json\n").encode("ascii")
        for filename, content in files.items():
            with (staging / filename).open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        directory_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        _publish_no_replace(staging, output)
        return manifest
    finally:
        if staging.exists():
            shutil.rmtree(staging)
