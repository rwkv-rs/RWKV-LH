from __future__ import annotations


from copy import deepcopy
from dataclasses import replace

import pytest

from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION, ModelCommand
from rwkv_lh.model_session import ModelSession, NativeRWKVModelSession
from rwkv_lh.role_trace_context import TraceContextError, bind_server_input_tokens, reconstruct_context
from rwkv_lh.runtime.native_state import NativeStateCacheBinding
from rwkv_lh.schema import ModelEvent, ModelLaneKind
from rwkv_lh.token_budget import tokenizer
from test_model_session import FakeNativeStateClient, QueueClient, settings


RAW = ModelCommand("read_file", {"path": "source.txt"}).canonical
STOP = "\nUser:"


@pytest.mark.parametrize(
    "transport,scope", [("prompt_replay", "full_prompt"), ("native_rwkv", "full_context")],
)
def test_actual_full_input_ids_can_prove_bos_without_guessing(transport, scope):
    context = {
        "transport": transport, "reconstructed_token_ids": [11, 12],
        "token_ids": None, "token_ids_complete": False,
    }
    evidence = {
        "prompt_token_ids": [0, 11, 12], "prompt_token_ids_scope": scope,
        "input_bos_token_count": 1,
    }
    bound = bind_server_input_tokens(context, evidence)
    assert bound["token_ids"] == [0, 11, 12]
    assert bound["input_bos_token_ids"] == [0]
    assert bound["token_ids_complete"] is True
    assert context["token_ids"] is None
    evidence["prompt_token_ids"] = [0, 11, 13]
    with pytest.raises(TraceContextError, match="reconstruction_mismatch"):
        bind_server_input_tokens(context, evidence)


def test_native_delta_ids_never_claim_complete_consumed_state():
    context = {
        "transport": "native_rwkv", "reconstructed_token_ids": [11, 12],
        "token_ids": None, "token_ids_complete": False,
    }
    result = bind_server_input_tokens(
        context, {"prompt_token_ids": [12], "prompt_token_ids_scope": "delta"},
    )
    assert result["token_ids_complete"] is False and result["token_ids"] is None


class TokenNativeClient(FakeNativeStateClient):
    """Keep the full generated stream in WKV while omitting the wire stop."""

    def state_generate(self, **kwargs):
        returned = super().state_generate(**kwargs)
        text = returned.content
        displayed = text[: -len(STOP)] if text.endswith(STOP) else text
        return replace(
            returned,
            content=displayed,
            metadata={"token_ids": tokenizer().encode(text)},
        )


def session_fixture(native: bool = True, *, generated: bool = True):
    client = TokenNativeClient([RAW + STOP]) if native else QueueClient([RAW])
    events = []
    session_type = NativeRWKVModelSession if native else ModelSession
    session = session_type(
        client,
        settings=settings(
            state_profile_id="zero", state_profile_sha256="0" * 64,
            model_sha256="a" * 64,
        ),
        audit_hook=events.append,
    )
    root = session.bootstrap(
        ModelLaneKind.ACTION, "Original exact assignment.",
        [FINAL_ANSWER_DEFINITION], lane_id="CONTEXT:ROOT",
    )
    checkpoints = {root.checkpoint_id: root}
    head = root
    if generated:
        candidate = session.generate(head)
        head = session.commit(candidate, session.parse(candidate))
        checkpoints[head.checkpoint_id] = head
    return session, client, events, checkpoints, root, head


def event(identifier="EV-RESULT"):
    return ModelEvent("action_result", identifier, "CONTEXT:ROOT", {"observed": "ok"})


def test_native_rebuilds_full_stream_across_stop_append_fork_and_empty_ack():
    session, client, events, checkpoints, root, head = session_fixture()
    appended = session.append(head, event())
    checkpoints[appended.checkpoint_id] = appended
    forked = session.fork(appended, ModelLaneKind.ACTION, event("EV-FORK"))
    checkpoints[forked.checkpoint_id] = forked
    acknowledged = session.acknowledge_projected_event(forked, event("EV-ACK"))
    checkpoints[acknowledged.checkpoint_id] = acknowledged

    result = reconstruct_context(acknowledged.checkpoint_id, checkpoints, events)

    assert result["prompt_text"] == client.states[acknowledged.native_state_ref]
    assert result["prompt_text"] == root.transcript + RAW + STOP + appended.transcript + forked.transcript
    assert result["reconstructed_token_ids"] == (
        tokenizer().encode(root.transcript)
        + tokenizer().encode(RAW + STOP)
        + tokenizer().encode(appended.transcript)
        + tokenizer().encode(forked.transcript)
    )
    assert result["segments"][1]["raw_token_ids"] == tokenizer().encode(RAW + STOP)
    assert result["segments"][1]["transport_removed_suffix"] == STOP
    assert result["segments"][-1]["text"] == ""
    assert result["initial_state"]["state_profile_id"] == "zero"
    assert result["initial_state"]["state_profile_sha256"] == "0" * 64
    assert result["token_ids"] is None
    assert result["token_ids_complete"] is False
    assert result["reconstructed_token_ids_include_bos"] is False


def test_replay_uses_one_complete_transcript_without_restoring_unsent_stop():
    session, _, events, checkpoints, _, head = session_fixture(native=False)
    head = session.append(head, event())
    checkpoints[head.checkpoint_id] = head
    head = session.fork(head, ModelLaneKind.ACTION, event("EV-FORK"))
    checkpoints[head.checkpoint_id] = head
    head = session.acknowledge_projected_event(head, event("EV-ACK"))
    checkpoints[head.checkpoint_id] = head

    result = reconstruct_context(head.checkpoint_id, checkpoints, events)

    assert result["prompt_text"] == head.transcript
    assert result["reconstructed_token_ids"] == tokenizer().encode(head.transcript)
    assert result["transport"] == "prompt_replay"
    assert result["token_ids_complete"] is False


@pytest.mark.parametrize("native", [False, True])
def test_rollover_starts_from_fresh_state_not_archived_parent(native):
    session, _, events, checkpoints, _, old = session_fixture(native=native)
    compact = session.rollover(
        old, "Fresh exact assignment.", [FINAL_ANSWER_DEFINITION],
        events=(), input_limit=10000, rollover_id="RO-CONTEXT",
    )
    # The archived chain is not a physical dependency of this fresh State.
    result = reconstruct_context(compact.checkpoint_id, {compact.checkpoint_id: compact}, events)
    assert result["prompt_text"] == compact.transcript
    assert "Original exact assignment." not in result["prompt_text"]
    assert result["initial_state"]["reset_checkpoint_id"] == compact.checkpoint_id
    assert result["chain_evidence"][0]["discarded_parent_checkpoint_id"] == old.checkpoint_id


@pytest.mark.parametrize("native", [False, True])
def test_disclosure_is_an_audited_delta(native):
    session, _, events, checkpoints, _, head = session_fixture(native=native, generated=False)
    disclosed = session.disclose_tool(head, FINAL_ANSWER_DEFINITION)
    checkpoints[disclosed.checkpoint_id] = disclosed
    result = reconstruct_context(disclosed.checkpoint_id, checkpoints, events)
    expected = head.transcript + disclosed.transcript if native else disclosed.transcript
    assert result["prompt_text"] == expected


@pytest.mark.parametrize("kind", ["transcript_digest", "token_count", "model_sha256", "state_profile_sha256"])
def test_checkpoint_corruption_is_rejected(kind):
    _, _, events, checkpoints, _, head = session_fixture(generated=False)
    damaged = deepcopy(head.to_dict())
    if kind == "model_sha256":
        damaged["native_state_metadata"][kind] = ""
    elif kind == "token_count":
        damaged[kind] += 1
    else:
        damaged[kind] = ""
    checkpoints[head.checkpoint_id] = damaged
    with pytest.raises(TraceContextError):
        reconstruct_context(head.checkpoint_id, checkpoints, events)


@pytest.mark.parametrize("field", ["parent_state_digest", "state_chain_digest", "event_ids_digest", "delta_digest"])
def test_native_binding_semantic_corruption_is_rejected_even_with_new_digest(field):
    session, _, events, checkpoints, _, head = session_fixture(generated=False)
    appended = session.append(head, event())
    damaged = deepcopy(appended.to_dict())
    metadata = damaged["native_state_metadata"]
    metadata["cache_binding"][field] = "b" * 64
    metadata["cache_binding_digest"] = NativeStateCacheBinding.from_mapping(metadata["cache_binding"]).digest
    checkpoints[appended.checkpoint_id] = damaged
    with pytest.raises(TraceContextError):
        reconstruct_context(appended.checkpoint_id, checkpoints, events)


@pytest.mark.parametrize("missing_type", [
    "model_session_generation_started",
    "model_session_generation_returned",
    "model_session_candidate_committed",
])
def test_native_generation_requires_request_response_and_commit_evidence(missing_type):
    _, _, events, checkpoints, _, head = session_fixture()
    events = [item for item in events if item["type"] != missing_type]
    with pytest.raises(TraceContextError):
        reconstruct_context(head.checkpoint_id, checkpoints, events)


@pytest.mark.parametrize("corruption", ["missing", "boolean", "wrong_text", "unknown_id", "raw_sha", "request_id"])
def test_native_generated_tokens_and_raw_identity_are_checked(corruption):
    _, _, events, checkpoints, _, head = session_fixture()
    returned = next(item for item in events if item["type"] == "model_session_generation_returned")
    raw = returned["raw_generation"]
    if corruption == "missing":
        raw["raw_token_ids"] = []
    elif corruption == "boolean":
        raw["raw_token_ids"] = [True]
    elif corruption == "wrong_text":
        raw["raw_token_ids"] = tokenizer().encode("unrelated")
    elif corruption == "unknown_id":
        raw["raw_token_ids"] = [10**10]
    elif corruption == "raw_sha":
        raw["raw_output_sha256"] = "b" * 64
    else:
        raw["request_id"] = "wrong-request"
    with pytest.raises(TraceContextError):
        reconstruct_context(head.checkpoint_id, checkpoints, events)


def test_native_preserves_raw_token_segmentation_instead_of_reencoding_generation():
    _, _, events, checkpoints, root, head = session_fixture()
    raw = next(item["raw_generation"] for item in events if item["type"] == "model_session_generation_returned")
    actual_ids = [token for byte in (RAW + STOP).encode() for token in tokenizer().encode_bytes(bytes([byte]))]
    raw["raw_token_ids"] = actual_ids
    result = reconstruct_context(head.checkpoint_id, checkpoints, events)
    assert result["reconstructed_token_ids"] == tokenizer().encode(root.transcript) + actual_ids
    assert actual_ids != tokenizer().encode(RAW + STOP)


def test_audit_causal_order_must_match_consumed_checkpoint_order():
    _, _, events, checkpoints, _, head = session_fixture()
    events[1], events[2] = events[2], events[1]
    with pytest.raises(TraceContextError):
        reconstruct_context(head.checkpoint_id, checkpoints, events)


@pytest.mark.parametrize("damage", ["missing_parent", "cycle", "missing_audit", "duplicate_audit", "foreign_lane"])
def test_context_rejects_missing_or_ambiguous_lineage(damage):
    session, _, events, checkpoints, root, head = session_fixture(generated=False)
    appended = session.append(head, event())
    checkpoints[appended.checkpoint_id] = appended
    if damage == "missing_parent":
        del checkpoints[root.checkpoint_id]
    elif damage == "cycle":
        appended.parent_checkpoint_id = appended.checkpoint_id
    elif damage == "missing_audit":
        events.pop()
    elif damage == "duplicate_audit":
        events.append(deepcopy(events[-1]))
    else:
        events[-1]["lane_id"] = "OTHER-LANE"
    with pytest.raises(TraceContextError):
        reconstruct_context(appended.checkpoint_id, checkpoints, events)


def test_uncommitted_or_rolled_back_candidate_cannot_be_a_training_input():
    session, _, events, checkpoints, _, head = session_fixture(generated=False)
    candidate = session.generate(head)
    session.rollback(candidate)
    checkpoints[candidate.checkpoint.checkpoint_id] = candidate.checkpoint
    with pytest.raises(TraceContextError):
        reconstruct_context(candidate.checkpoint.checkpoint_id, checkpoints, events)


@pytest.mark.parametrize("acknowledgement", [False, True])
def test_append_audits_cannot_borrow_a_missing_event_id_from_checkpoint(acknowledgement):
    session, _, events, checkpoints, _, head = session_fixture(generated=False)
    operation = session.acknowledge_projected_event if acknowledgement else session.append
    appended = operation(head, event())
    checkpoints[appended.checkpoint_id] = appended
    del events[-1]["event_id"]
    with pytest.raises(TraceContextError, match="missing_appended_event_id"):
        reconstruct_context(appended.checkpoint_id, checkpoints, events)


@pytest.mark.parametrize("field", ["sampling", "max_output_tokens", "response_model"])
def test_generation_request_and_response_parameters_are_bound(field):
    _, _, events, checkpoints, _, head = session_fixture()
    raw = next(item["raw_generation"] for item in events if item["type"] == "model_session_generation_returned")
    raw[field] = {"temperature": 0.9} if field == "sampling" else (1 if field == "max_output_tokens" else "other-model")
    with pytest.raises(TraceContextError, match="raw_generation_identity_mismatch"):
        reconstruct_context(head.checkpoint_id, checkpoints, events)
