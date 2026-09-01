from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
import re
from types import SimpleNamespace
from typing import Any

from rwkv_lh.schema import ModelLaneKind


_SPACE = re.compile(r"\s+")


def _normalize_text(value: object) -> str:
    return _SPACE.sub(" ", str(value or "")).strip().casefold()


def _exact_span_windows(evidence: list[dict[str, Any]]) -> set[str]:
    windows: set[str] = set()
    for external in evidence:
        for record in external.get("records") or ():
            if not isinstance(record, Mapping):
                continue
            for span in record.get("exact_spans") or ():
                if not isinstance(span, Mapping):
                    continue
                tokens = _normalize_text(span.get("text")).split()
                for start in range(max(0, len(tokens) - 4)):
                    fragment = " ".join(tokens[start : start + 5])
                    if len(fragment) >= 24 and not fragment.startswith(
                        ("http://", "https://")
                    ):
                        windows.add(fragment)
    return windows


def _artifact_path(workspace: Path, contract: Mapping[str, Any]) -> Path:
    relative = Path(str(contract.get("path") or ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("expected artifact path is not workspace-relative")
    root = workspace.resolve()
    resolved = (workspace / relative).resolve()
    if resolved != root and root not in resolved.parents:
        raise RuntimeError("expected artifact escaped the workspace")
    return resolved


def verify_grounding(
    workspace: Path,
    contract: Mapping[str, Any],
    evidence: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    path = _artifact_path(workspace, contract)
    serialized = json.dumps(
        evidence,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    normalized_evidence = _normalize_text(serialized)
    summary: dict[str, Any] = {
        "committed_external_evidence_actions": len(evidence),
        "serialized_evidence_sha256": hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest(),
        "grounded_fields_checked": 0,
        "grounded_fields_matched": 0,
        "required_text_fragments": int(
            contract.get("minimum_grounded_fragments") or 0
        ),
        "matched_text_fragments": 0,
    }
    if not path.is_file():
        return summary, ["grounding target artifact is missing"]
    if contract.get("type") == "json":
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            return summary, [
                f"grounding target JSON is invalid: {type(exc).__name__}: {exc}"
            ]
        if not isinstance(artifact, Mapping):
            return summary, ["grounding target JSON root is not an object"]
        for field, field_contract in dict(contract.get("fields") or {}).items():
            if not dict(field_contract).get("grounded"):
                continue
            summary["grounded_fields_checked"] += 1
            observed = _normalize_text(artifact.get(field))
            if observed and observed in normalized_evidence:
                summary["grounded_fields_matched"] += 1
            else:
                failures.append(
                    f"grounded field {field!r} does not occur in committed network evidence"
                )
        return summary, failures
    if contract.get("type") != "text":
        return summary, ["unsupported grounding artifact type"]
    required = int(contract.get("minimum_grounded_fragments") or 0)
    if required <= 0:
        return summary, failures
    artifact = _normalize_text(path.read_text(encoding="utf-8"))
    matched = sorted(
        fragment
        for fragment in _exact_span_windows(evidence)
        if fragment in artifact
    )
    summary["matched_text_fragments"] = len(matched)
    summary["matched_text_fragment_sha256"] = [
        hashlib.sha256(fragment.encode("utf-8")).hexdigest()
        for fragment in matched[:required]
    ]
    if len(matched) < required:
        failures.append(
            f"grounded exact-span fragments {len(matched)} is below required {required}"
        )
    return summary, failures


def verify_state_stability(
    state: Any,
    *,
    executor_profile_id: str,
    executor_profile_sha256: str,
    selector_profile_id: str,
    selector_profile_sha256: str,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    expected = {
        ModelLaneKind.ACTION: (executor_profile_id, executor_profile_sha256),
        ModelLaneKind.SELECTOR: (selector_profile_id, selector_profile_sha256),
    }
    by_lane: dict[str, list[Any]] = defaultdict(list)
    for checkpoint in state.model_states.values():
        by_lane[str(checkpoint.lane_id)].append(checkpoint)
    switches = 0
    lane_records: list[dict[str, Any]] = []
    for lane_id, checkpoints in sorted(by_lane.items()):
        ordered = sorted(
            checkpoints,
            key=lambda item: (item.created_at, item.checkpoint_id),
        )
        observed = [
            (str(item.state_profile_id), str(item.state_profile_sha256))
            for item in ordered
        ]
        lane_switches = sum(
            left != right for left, right in zip(observed, observed[1:])
        )
        switches += lane_switches
        lane_kind = ordered[0].lane_kind
        expected_pair = expected[lane_kind]
        if any(item.lane_kind is not lane_kind for item in ordered):
            failures.append(f"lane kind changed within {lane_id}")
        if any(pair != expected_pair for pair in observed):
            failures.append(f"state profile differs from frozen identity in {lane_id}")
        if lane_switches:
            failures.append(
                f"state profile switched {lane_switches} time(s) in {lane_id}"
            )
        lane_records.append(
            {
                "lane_id": lane_id,
                "lane_kind": lane_kind.value,
                "checkpoint_count": len(ordered),
                "profile_id": expected_pair[0],
                "profile_sha256": expected_pair[1],
                "profile_switches": lane_switches,
            }
        )
    observed_kinds = {record["lane_kind"] for record in lane_records}
    for lane_kind in (ModelLaneKind.ACTION.value, ModelLaneKind.SELECTOR.value):
        if lane_kind not in observed_kinds:
            failures.append(f"no {lane_kind} lane was persisted")
    return {
        "profile_switches_within_run": switches,
        "lane_count": len(lane_records),
        "lanes": lane_records,
    }, failures


def _evidence() -> list[dict[str, object]]:
    return [
        {
            "status": "evidence_committed",
            "records": [
                {
                    "title": "Current package record",
                    "url": "https://example.test/package",
                    "structured_fields": {"name": "anyio", "version": "4.10.0"},
                    "exact_spans": [
                        {
                            "text": (
                                "This package provides structured concurrency for Python "
                                "and remains available from the public index."
                            )
                        }
                    ],
                }
            ],
        }
    ]


def test_grounded_json_fields_must_occur_in_committed_evidence(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts/package.json"
    artifact.parent.mkdir()
    artifact.write_text(
        json.dumps({"name": "anyio", "version": "4.10.0"}), encoding="utf-8"
    )
    contract = {
        "path": "artifacts/package.json",
        "type": "json",
        "fields": {
            "name": {"grounded": True},
            "version": {"grounded": True},
        },
    }

    summary, failures = verify_grounding(tmp_path, contract, _evidence())

    assert failures == []
    assert summary["grounded_fields_checked"] == 2
    assert summary["grounded_fields_matched"] == 2
    artifact.write_text(
        json.dumps({"name": "anyio", "version": "invented"}), encoding="utf-8"
    )
    _summary, failures = verify_grounding(tmp_path, contract, _evidence())
    assert failures == [
        "grounded field 'version' does not occur in committed network evidence"
    ]


def test_grounded_text_requires_a_fixed_five_token_exact_span(tmp_path: Path) -> None:
    artifact = tmp_path / "artifacts/note.md"
    artifact.parent.mkdir()
    artifact.write_text(
        "Evidence: structured concurrency for Python and remains available.\n",
        encoding="utf-8",
    )
    contract = {
        "path": "artifacts/note.md",
        "type": "text",
        "minimum_grounded_fragments": 1,
    }

    summary, failures = verify_grounding(tmp_path, contract, _evidence())

    assert failures == []
    assert summary["matched_text_fragments"] >= 1


def _checkpoint(
    checkpoint_id: str,
    lane_id: str,
    lane_kind: ModelLaneKind,
    profile_id: str,
    profile_sha256: str,
    created_at: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        checkpoint_id=checkpoint_id,
        lane_id=lane_id,
        lane_kind=lane_kind,
        state_profile_id=profile_id,
        state_profile_sha256=profile_sha256,
        created_at=created_at,
    )


def test_state_profile_is_constant_per_task_lane_and_switches_fail() -> None:
    executor_sha = "a" * 64
    selector_sha = "0" * 64
    state = SimpleNamespace(
        model_states={
            "A1": _checkpoint(
                "A1", "LANE:ACTION", ModelLaneKind.ACTION, "G6", executor_sha, "1"
            ),
            "A2": _checkpoint(
                "A2", "LANE:ACTION", ModelLaneKind.ACTION, "G6", executor_sha, "2"
            ),
            "S1": _checkpoint(
                "S1", "LANE:SELECTOR", ModelLaneKind.SELECTOR, "zero", selector_sha, "1"
            ),
        }
    )
    summary, failures = verify_state_stability(
        state,
        executor_profile_id="G6",
        executor_profile_sha256=executor_sha,
        selector_profile_id="zero",
        selector_profile_sha256=selector_sha,
    )
    assert failures == []
    assert summary["profile_switches_within_run"] == 0

    state.model_states["A2"].state_profile_id = "G3"
    state.model_states["A2"].state_profile_sha256 = "b" * 64
    summary, failures = verify_state_stability(
        state,
        executor_profile_id="G6",
        executor_profile_sha256=executor_sha,
        selector_profile_id="zero",
        selector_profile_sha256=selector_sha,
    )
    assert summary["profile_switches_within_run"] == 1
    assert any("switched" in failure for failure in failures)
