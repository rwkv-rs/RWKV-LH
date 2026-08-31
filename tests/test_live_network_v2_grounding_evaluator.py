from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

from rwkv_lh.schema import ModelLaneKind


ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = (
    ROOT
    / "temp/run_current_architecture_live_network_e2e_v4_grounded_profile_20260829.py"
)
SPEC = importlib.util.spec_from_file_location("rwkv_lh_v2_grounding_test", EVALUATOR)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
verify_grounding = MODULE.verify_grounding
verify_state_stability = MODULE.verify_state_stability


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
