"""Pure generation evidence checks for the production-trace dataset consumer.

No calls are made to a model, service or workspace. A committed candidate must
reconstruct through the existing context validator; a rejected candidate must
have an actual rollback record. Neither outcome independently grants a label.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from typing import Any

from rwkv_lh.exact_tool_selector.input_protocol import network_selector_input_protocol
from rwkv_lh.exact_tool_selector.native_network_client import (
    NATIVE_SELECTOR_CHECKPOINT_TRANSPORT, NATIVE_SELECTOR_LANE_ID,
)
from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID, NATIVE_SELECTOR_DECODER_PROTOCOL,
    NativeNetworkToolSelection,
)
from rwkv_lh.exact_tool_selector.network_protocol import NetworkSelectorInput
from rwkv_lh.goal_state_protocols import selector_intent_v6
from rwkv_lh.model_io import parse_model_command_with_trace
from rwkv_lh.model_session import CandidateGeneration, SessionSampling, _restore_attested_stop_suffix
from rwkv_lh.role_trace_context import TraceContextError, reconstruct_context
from rwkv_lh.schema import ModelCheckpoint, ModelCheckpointStatus, ModelLaneKind
from rwkv_lh.token_budget import tokenizer


class GenerationEvidenceError(ValueError):
    """Durable generation evidence contains a contradiction."""


class GenerationEvidenceMissing(GenerationEvidenceError):
    """A required original request, response or outcome was not retained."""


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _equal(actual: Any, expected: Any, field: str) -> None:
    if actual != expected or isinstance(actual, bool) != isinstance(expected, bool):
        raise GenerationEvidenceError(f"generation {field} mismatch")


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise GenerationEvidenceMissing(f"missing generation {field}")
    return value


def _digest(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise GenerationEvidenceError(f"generation {field} is not lowercase SHA-256")
    return value


def _unique(rows: Sequence[Any], field: str):
    if not rows:
        raise GenerationEvidenceMissing(f"missing generation {field}")
    if len(rows) != 1:
        raise GenerationEvidenceError(f"ambiguous generation {field}")
    return rows[0]


def _context(checkpoint_id: str, checkpoints: Mapping, trace: Sequence[Mapping]) -> dict:
    try:
        return reconstruct_context(checkpoint_id, checkpoints, trace)
    except TraceContextError as exc:
        # Absence is auditable exclusion; corruption must reject the batch.
        if exc.reason.startswith("missing_") and "ambiguous" not in exc.reason:
            raise GenerationEvidenceMissing(str(exc)) from exc
        raise GenerationEvidenceError(str(exc)) from exc


def validate_generation_evidence(
    request_id: str, input_checkpoint: ModelCheckpoint,
    raw_generation: Mapping[str, Any], model_trace: Sequence[Mapping[str, Any]],
    checkpoints: Mapping[str, ModelCheckpoint | Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind one current JSON generation to its exact input and durable outcome.

    Pass the input checkpoint from its boundary snapshot and the retained full
    checkpoint map. The map's version of that input is replaced only in the local
    validation view, so later metadata cannot substitute for boundary evidence.
    Both committed and rolled-back outputs retain their original outcome; the
    extraction caller decides which label authorities may use each outcome.
    """
    _nonempty(request_id, "request_id")
    if not isinstance(raw_generation, Mapping):
        raise GenerationEvidenceMissing("missing raw generation")
    if any(not isinstance(row, Mapping) for row in model_trace):
        raise GenerationEvidenceError("model trace contains a non-object event")
    _equal(raw_generation.get("request_id"), request_id, "raw request_id")
    start_index, start = _unique([
        (index, row) for index, row in enumerate(model_trace)
        if row.get("type") == "model_session_generation_started" and row.get("request_id") == request_id
    ], "request start")
    returned_index, returned = _unique([
        (index, row) for index, row in enumerate(model_trace)
        if row.get("type") == "model_session_generation_returned" and row.get("request_id") == request_id
    ], "request response")
    if not start_index < returned_index:
        raise GenerationEvidenceError("generation response precedes request")
    if input_checkpoint.transport not in {"native_rwkv", "prompt_replay"}:
        raise GenerationEvidenceError("unsupported JSON generation transport")
    _equal(input_checkpoint.status, ModelCheckpointStatus.COMMITTED, "input status")
    native = input_checkpoint.transport == "native_rwkv"
    input_digest = input_checkpoint.native_state_digest if native else input_checkpoint.transcript_digest
    _equal(start.get("input_checkpoint_id"), input_checkpoint.checkpoint_id, "input checkpoint")
    _equal(start.get("input_digest"), input_digest, "input digest")
    for label, event in (("start", start), ("response", returned)):
        _equal(event.get("lane_id"), input_checkpoint.lane_id, f"{label} lane")
        _equal(event.get("state_transport"), input_checkpoint.transport, f"{label} transport")
        if "lane_kind" in event:
            _equal(event["lane_kind"], input_checkpoint.lane_kind.value, f"{label} lane kind")
    _equal(returned.get("raw_generation"), raw_generation, "raw response record")
    output = raw_generation.get("raw_output")
    if not isinstance(output, str):
        raise GenerationEvidenceMissing("missing generation raw output")
    _equal(returned.get("raw_output"), output, "response raw output")
    _equal(raw_generation.get("raw_output_sha256"), _sha(output), "raw output SHA")
    _equal(raw_generation.get("raw_output_utf8_bytes"), len(output.encode("utf-8")), "raw output byte count")
    _equal(returned.get("finish_reason"), raw_generation.get("finish_reason"), "finish reason")
    _equal(raw_generation.get("postprocessed"), False, "postprocessed")
    _equal(raw_generation.get("state_profile_id"), input_checkpoint.state_profile_id, "State profile")
    _equal(raw_generation.get("state_profile_sha256"), input_checkpoint.state_profile_sha256, "State SHA")
    if raw_generation.get("response_model") not in {"", input_checkpoint.model}:
        raise GenerationEvidenceError("generation response model mismatch")
    if not isinstance(start.get("sampling"), Mapping):
        raise GenerationEvidenceMissing("missing generation sampling")
    _equal(raw_generation.get("sampling"), start["sampling"], "sampling")
    if type(start.get("max_tokens")) is not int or start["max_tokens"] < 1:
        raise GenerationEvidenceError("generation output budget is invalid")
    _equal(raw_generation.get("max_output_tokens"), start["max_tokens"], "output budget")
    candidate_id = _nonempty(raw_generation.get("candidate_id"), "candidate id")
    candidate_checkpoint_id = _nonempty(returned.get("candidate_checkpoint_id"), "candidate checkpoint")
    response_digest = _digest(returned.get("candidate_digest"), "candidate digest")
    _equal(returned.get("candidate_id"), candidate_id, "response candidate id")
    if candidate_checkpoint_id == input_checkpoint.checkpoint_id:
        raise GenerationEvidenceError("generation candidate aliases its input")
    outcomes = [
        (index, row) for index, row in enumerate(model_trace)
        if row.get("type") in {"model_session_candidate_committed", "model_session_candidate_rolled_back"}
        and (row.get("candidate_id") == candidate_id
             or row.get("checkpoint_id", row.get("candidate_checkpoint_id")) == candidate_checkpoint_id)
    ]
    outcome_index, outcome = _unique(outcomes, "candidate outcome")
    if outcome_index <= returned_index:
        raise GenerationEvidenceError("generation outcome precedes response")
    _equal(outcome.get("candidate_id"), candidate_id, "outcome candidate id")
    _equal(outcome.get("lane_id"), input_checkpoint.lane_id, "outcome lane")
    _equal(outcome.get("state_transport"), input_checkpoint.transport, "outcome transport")
    selected_checkpoints = dict(checkpoints)
    selected_checkpoints[input_checkpoint.checkpoint_id] = input_checkpoint
    committed = outcome["type"] == "model_session_candidate_committed"
    if committed:
        _equal(outcome.get("checkpoint_id"), candidate_checkpoint_id, "committed checkpoint")
        candidate = selected_checkpoints.get(candidate_checkpoint_id)
        if candidate is None:
            raise GenerationEvidenceMissing("missing durable generation candidate checkpoint")
        if not isinstance(candidate, ModelCheckpoint):
            try:
                candidate = ModelCheckpoint.from_dict(candidate)
            except (TypeError, ValueError, KeyError) as exc:
                raise GenerationEvidenceError("invalid generation candidate checkpoint") from exc
        _equal(candidate.parent_checkpoint_id, input_checkpoint.checkpoint_id, "candidate parent")
        _equal(returned.get("candidate_digest"), candidate.native_state_digest if native else candidate.transcript_digest, "candidate digest")
        _context(candidate_checkpoint_id, selected_checkpoints, model_trace)
        try:
            generated = CandidateGeneration(
                request_id=request_id, candidate_id=candidate_id, parent=input_checkpoint,
                checkpoint=candidate, raw_output=output,
                finish_reason=str(raw_generation.get("finish_reason") or ""),
                sampling=SessionSampling(**dict(raw_generation["sampling"])),
                max_output_tokens=raw_generation["max_output_tokens"],
                raw_token_ids=tuple(raw_generation.get("raw_token_ids") or ()),
            )
            # Use precisely the live parser's restoration rule: only a proven
            # Markdown fence is restored; conversation stops never enter JSON.
            parse_text, _restored = _restore_attested_stop_suffix(generated)
            command, _trace = parse_model_command_with_trace(parse_text)
        except (ValueError, TypeError, KeyError) as exc:
            raise GenerationEvidenceError("committed generation lacks its original parsed command") from exc
        _equal(outcome.get("command_digest"), command.digest, "committed command digest")
    else:
        _equal(outcome.get("candidate_checkpoint_id"), candidate_checkpoint_id, "rolled-back checkpoint")
        _equal(outcome.get("restored_checkpoint_id"), input_checkpoint.checkpoint_id, "rollback restored checkpoint")
        if native:
            # This is an opaque WKV-state digest, not the transcript/semantic
            # chain hash. A discarded State cannot be re-created without RWKV;
            # cross-bind the original response to independent rollback telemetry.
            if "candidate_digest" not in outcome:
                raise GenerationEvidenceMissing("missing native rollback candidate digest")
            _equal(_digest(outcome["candidate_digest"], "rollback candidate digest"), response_digest, "native rollback candidate digest")
        else:
            _equal(response_digest, _sha(input_checkpoint.transcript + output), "rollback replay transcript digest")
            if "candidate_digest" in outcome:
                _equal(outcome["candidate_digest"], response_digest, "rollback candidate digest")
        _context(input_checkpoint.checkpoint_id, selected_checkpoints, model_trace)
    return {
        "request_id": request_id, "candidate_id": candidate_id,
        "candidate_checkpoint_id": candidate_checkpoint_id,
        "input_checkpoint_id": input_checkpoint.checkpoint_id,
        "start_index": start_index, "returned_index": returned_index,
        "outcome_index": outcome_index, "outcome": "committed" if committed else "rolled_back",
    }


def _finite(value: Any, field: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value):
        raise GenerationEvidenceError(f"Selector {field} must be a finite logit")
    return float(value)


def _selector_trace(selection: NativeNetworkToolSelection) -> None:
    trace = selection.decoder_trace
    _equal(trace.get("prompt_token_count"), selection.input_token_count, "Selector prompt token count")
    suffixes = {
        label: tokenizer().encode(selector_intent_v6.TARGET_PREFIX + label)
        for label in selection.eligible_labels
    }
    selected_ids = suffixes[selection.selected_operation]
    raw_ids = trace.get("token_ids")
    if not isinstance(raw_ids, list) or any(type(token) is not int for token in raw_ids):
        raise GenerationEvidenceError("Selector token IDs must be original integer IDs")
    _equal(raw_ids, selected_ids, "Selector suffix tokens")
    decisions = trace.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(selected_ids):
        raise GenerationEvidenceError("Selector decoder decisions do not cover every token")
    for position, (chosen, decision) in enumerate(zip(selected_ids, decisions, strict=True)):
        if not isinstance(decision, Mapping):
            raise GenerationEvidenceError("Selector decoder decision must be an object")
        prefix = selected_ids[:position]
        allowed = sorted({ids[position] for ids in suffixes.values()
                          if len(ids) > position and ids[:position] == prefix})
        _equal(decision.get("position"), position, "Selector decoder position")
        _equal(decision.get("allowed_token_ids"), allowed, "Selector eligible trie tokens")
        logits = decision.get("allowed_token_logits")
        if not isinstance(logits, Mapping) or set(logits) != {str(token) for token in allowed}:
            raise GenerationEvidenceError("Selector decoder logits do not cover the exact eligible tokens")
        values = {token: _finite(logits[str(token)], "allowed token logit") for token in allowed}
        ordered = sorted(allowed, key=lambda token: (-values[token], token))
        _equal(decision.get("chosen_token_id"), chosen, "Selector chosen token")
        if chosen != ordered[0]:
            raise GenerationEvidenceError("Selector token is not the recorded eligible-logit argmax")
        _equal(_finite(decision.get("chosen_token_logit"), "chosen token logit"), values[chosen], "Selector chosen logit")
        margin = values[ordered[0]] - values[ordered[1]] if len(ordered) > 1 else None
        _equal(decision.get("chosen_vs_runner_up_margin"), margin, "Selector runner-up margin")


def validate_selector_generation(
    raw: Mapping[str, Any], checkpoint: ModelCheckpoint, network_input: NetworkSelectorInput,
) -> dict[str, Any]:
    """Bind one unprocessed Selector lane to its input, decoder and checkpoint."""
    try:
        selection = NativeNetworkToolSelection.from_dict(raw)
    except (ValueError, TypeError, KeyError) as exc:
        raise GenerationEvidenceError(str(exc)) from exc
    protocol = network_selector_input_protocol(selector_intent_v6.INPUT_SCHEMA_VERSION)
    metadata = checkpoint.native_state_metadata or {}
    transcript = protocol.render_bootstrap(network_input) + "\n" + protocol.render_step(network_input)
    expected = {
        "input_protocol": selector_intent_v6.INPUT_SCHEMA_VERSION,
        "model": selection.model, "model_sha256": selection.model_sha256,
        "decoder_id": NATIVE_SELECTOR_DECODER_ID,
        "decoder_protocol": NATIVE_SELECTOR_DECODER_PROTOCOL,
        "decoder_sha256": selection.decoder_sha256,
        "decoder_trace_sha256": selection.decoder_trace_sha256,
        "profile_id": selection.profile_id, "profile_sha256": selection.profile_sha256,
        "menu_order_id": network_input.menu_order_id,
        "input_digest": protocol.input_digest(network_input),
        "menu_digest": protocol.menu_digest(network_input),
        "eligible_labels": list(network_input.eligible_labels),
        "state_policy": "fresh_initial_state_per_evaluation",
        "selection_rule": "native_eligible_suffix_trie_vocab_argmax",
        "generated_rwkv_text": False, "downstream_decoder_trained": False,
        "postprocessed": False, "authoritative": False,
    }
    for field, value in expected.items():
        _equal(metadata.get(field), value, f"Selector checkpoint {field}")
    for field in ("input_digest", "menu_digest", "eligible_labels", "state_policy", "selection_rule"):
        _equal(raw.get(field), expected[field], f"Selector raw {field}")
    _equal(selection.decoder_id, NATIVE_SELECTOR_DECODER_ID, "Selector decoder id")
    _equal(selection.decoder_protocol, NATIVE_SELECTOR_DECODER_PROTOCOL, "Selector decoder protocol")
    for field in ("postprocessed", "downstream_decoder_trained", "generated_text"):
        _equal(raw.get(field), False, f"Selector raw {field}")
    for field, value in (
        ("checkpoint_id", selection.selector_checkpoint_id), ("lane_id", NATIVE_SELECTOR_LANE_ID),
        ("transport", NATIVE_SELECTOR_CHECKPOINT_TRANSPORT),
        ("lane_kind", ModelLaneKind.SELECTOR), ("status", ModelCheckpointStatus.COMMITTED),
        ("parent_checkpoint_id", None), ("model", selection.model),
        ("state_profile_id", selection.profile_id), ("state_profile_sha256", selection.profile_sha256),
        ("transcript", transcript), ("transcript_digest", _sha(transcript)),
        ("token_count", selection.input_token_count),
    ):
        _equal(getattr(checkpoint, field), value, f"Selector {field}")
    _selector_trace(selection)
    return {
        "request_id": selection.trace_id, "checkpoint_id": checkpoint.checkpoint_id,
        "decoder_trace_sha256": selection.decoder_trace_sha256,
        "input_digest": selection.input_digest, "menu_digest": selection.menu_digest,
        "menu_order_id": network_input.menu_order_id,
        # The server may prepend BOS; a count is not a retained input token list.
        "server_input_token_count": selection.input_token_count,
        "token_ids_complete": False,
    }


__all__ = [
    "GenerationEvidenceError", "GenerationEvidenceMissing",
    "validate_generation_evidence", "validate_selector_generation",
]
