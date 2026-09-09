"""Generation identity checks over fake transports; never training examples."""

from __future__ import annotations

from copy import deepcopy
import importlib

import pytest

from rwkv_lh.exact_tool_selector.network_protocol import NetworkSelectorInput
from rwkv_lh.model_io import canonical_digest
from rwkv_lh.role_trace_inputs import rebuild_role_input
from test_role_trace_context import session_fixture
from test_role_trace_dataset_integration import mock_controller_case  # noqa: F401
from test_role_trace_inputs import controller_role_snapshots  # noqa: F401


def _api():
    return importlib.import_module("rwkv_lh.role_trace_generation")


def _generation(native=True):
    _session, _client, trace, checkpoints, parent, candidate = session_fixture(native=native)
    returned = next(row for row in trace if row["type"] == "model_session_generation_returned")
    return parent, deepcopy(returned["raw_generation"]), deepcopy(trace), checkpoints, candidate


@pytest.mark.parametrize("native", [True, False])
def test_generation_binds_one_real_session_request_response_and_commit(native):
    parent, raw, trace, checkpoints, candidate = _generation(native)
    result = _api().validate_generation_evidence(raw["request_id"], parent, raw, trace, checkpoints)
    assert result["outcome"] == "committed"
    assert result["candidate_checkpoint_id"] == candidate.checkpoint_id
    assert result["start_index"] < result["returned_index"] < result["outcome_index"]


@pytest.mark.parametrize(("kind", "field", "value"), [
    ("model_session_generation_started", "input_digest", "f" * 64),
    ("model_session_generation_started", "lane_id", "OTHER-LANE"),
    ("model_session_generation_started", "state_transport", "prompt_replay"),
    ("model_session_generation_started", "max_tokens", 2),
    ("model_session_generation_returned", "candidate_id", "OTHER-CANDIDATE"),
    ("model_session_generation_returned", "candidate_digest", "f" * 64),
    ("model_session_generation_returned", "raw_output", "different raw bytes"),
    ("model_session_generation_returned", "finish_reason", "length"),
    ("model_session_candidate_committed", "command_digest", "f" * 64),
])
def test_current_generation_rejects_rebound_audit_field(kind, field, value):
    parent, raw, trace, checkpoints, _candidate = _generation()
    next(row for row in trace if row["type"] == kind)[field] = value
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_generation_evidence(raw["request_id"], parent, raw, trace, checkpoints)


def test_current_generation_rejects_response_before_request():
    parent, raw, trace, checkpoints, _candidate = _generation()
    start = next(index for index, row in enumerate(trace) if row["type"] == "model_session_generation_started")
    returned = next(index for index, row in enumerate(trace) if row["type"] == "model_session_generation_returned")
    trace[start], trace[returned] = trace[returned], trace[start]
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_generation_evidence(raw["request_id"], parent, raw, trace, checkpoints)


@pytest.mark.parametrize("kind", [
    "model_session_generation_started", "model_session_generation_returned",
    "model_session_candidate_committed",
])
def test_missing_current_generation_evidence_is_an_explicit_exclusion(kind):
    parent, raw, trace, checkpoints, _candidate = _generation()
    trace = [row for row in trace if row["type"] != kind]
    with pytest.raises(_api().GenerationEvidenceMissing):
        _api().validate_generation_evidence(raw["request_id"], parent, raw, trace, checkpoints)


def test_rejected_generation_requires_a_real_rollback_to_its_input():
    session, _client, trace, checkpoints, parent, _head = session_fixture(generated=False)
    candidate = session.generate(parent)
    session.rollback(candidate, error="test-only rejection")
    raw = candidate.raw_record()
    result = _api().validate_generation_evidence(raw["request_id"], parent, raw, trace, checkpoints)
    assert result["outcome"] == "rolled_back"
    next(row for row in trace if row["type"] == "model_session_candidate_rolled_back")["restored_checkpoint_id"] = "WRONG-PARENT"
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_generation_evidence(raw["request_id"], parent, raw, trace, checkpoints)


@pytest.mark.parametrize("native", [True, False])
@pytest.mark.parametrize("digest", ["", "f" * 64])
def test_rollback_cannot_lose_or_change_its_candidate_digest(native, digest):
    session, _client, trace, checkpoints, parent, _head = session_fixture(native=native, generated=False)
    candidate = session.generate(parent)
    session.rollback(candidate, error="test-only rollback")
    returned = next(row for row in trace if row["type"] == "model_session_generation_returned")
    returned["candidate_digest"] = digest
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_generation_evidence(candidate.request_id, parent, candidate.raw_record(), trace, checkpoints)


@pytest.mark.parametrize("native", [True, False])
def test_rollback_emits_independent_candidate_digest(native):
    session, _client, trace, _checkpoints, parent, _head = session_fixture(native=native, generated=False)
    candidate = session.generate(parent)
    session.rollback(candidate, error="test-only rollback")
    rolled_back = next(row for row in trace if row["type"] == "model_session_candidate_rolled_back")
    assert rolled_back["candidate_digest"] == (
        candidate.checkpoint.native_state_digest if native else candidate.checkpoint.transcript_digest
    )


def test_native_rollback_without_retained_digest_is_missing_evidence():
    session, _client, trace, checkpoints, parent, _head = session_fixture(generated=False)
    candidate = session.generate(parent)
    session.rollback(candidate, error="test-only rollback")
    next(row for row in trace if row["type"] == "model_session_candidate_rolled_back").pop("candidate_digest", None)
    with pytest.raises(_api().GenerationEvidenceMissing):
        _api().validate_generation_evidence(candidate.request_id, parent, candidate.raw_record(), trace, checkpoints)


def _selector(case):
    final = case["final"]
    staged = next(final.causal_records[key] for key in final.causal_order
                  if final.causal_records[key].event_type == "exact_tool_selection_staged")
    raw = deepcopy(staged.payload["selection"]["raw_selection"]["lane_selections"]["canonical"])
    checkpoint = deepcopy(final.model_states[raw["selector_checkpoint_id"]])
    snapshot = next(item for item in case["snapshots"]
                    if item.causal_records[item.causal_order[-1]].event_type == "goal_role_input_boundary")
    rebuilt = rebuild_role_input("selector_intent", snapshot, {
        "boundary_event_id": snapshot.causal_order[-1], "menu_order_id": "canonical",
    })
    network = NetworkSelectorInput.create(
        current_subtask=rebuilt["network_input"]["current_subtask"],
        current_progress=rebuilt["network_input"]["current_progress"],
        eligible_labels=rebuilt["network_input"]["eligible_labels"],
        menu_order_id="canonical",
    )
    return raw, checkpoint, network


def test_selector_attests_exact_current_decoder_and_checkpoint(mock_controller_case):
    raw, checkpoint, network = _selector(mock_controller_case)
    result = _api().validate_selector_generation(raw, checkpoint, network)
    assert result["decoder_trace_sha256"] == raw["decoder_trace_sha256"]
    assert result["token_ids_complete"] is False


def test_selector_cannot_claim_another_checkpoint_transport(mock_controller_case):
    raw, checkpoint, network = _selector(mock_controller_case)
    checkpoint.transport = "prompt_replay"
    with pytest.raises(_api().GenerationEvidenceError, match="transport"):
        _api().validate_selector_generation(raw, checkpoint, network)


@pytest.mark.parametrize("field", [
    "decoder_id", "decoder_protocol", "decoder_sha256", "decoder_trace_sha256",
    "menu_order_id", "input_digest", "menu_digest", "eligible_labels",
])
def test_selector_metadata_must_bind_its_raw_request(field, mock_controller_case):
    raw, checkpoint, network = _selector(mock_controller_case)
    checkpoint.native_state_metadata[field] = "different"
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_selector_generation(raw, checkpoint, network)


@pytest.mark.parametrize("field", ["postprocessed", "downstream_decoder_trained", "generated_text"])
def test_selector_cannot_promote_processed_outputs(field, mock_controller_case):
    raw, checkpoint, network = _selector(mock_controller_case)
    raw[field] = True
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_selector_generation(raw, checkpoint, network)


def test_selector_rehashed_decoder_trace_still_must_match_checkpoint(mock_controller_case):
    raw, checkpoint, network = _selector(mock_controller_case)
    raw["decoder_trace"]["decisions"][0]["chosen_token_logit"] += 1
    raw["decoder_trace_sha256"] = canonical_digest(raw["decoder_trace"])
    with pytest.raises(_api().GenerationEvidenceError):
        _api().validate_selector_generation(raw, checkpoint, network)


def test_selector_rejects_invalid_argmax_even_if_both_trace_hashes_change(mock_controller_case):
    raw, checkpoint, network = _selector(mock_controller_case)
    raw["decoder_trace"]["decisions"][0]["chosen_token_logit"] += 1
    digest = canonical_digest(raw["decoder_trace"])
    raw["decoder_trace_sha256"] = digest
    checkpoint.native_state_metadata["decoder_trace_sha256"] = digest
    with pytest.raises(_api().GenerationEvidenceError, match="logit"):
        _api().validate_selector_generation(raw, checkpoint, network)
