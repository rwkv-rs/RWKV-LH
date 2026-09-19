"""Wire result for Selector decisions made by the frozen G1J LM head."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    validate_network_label,
)
from rwkv_lh.model_io import canonical_digest


NATIVE_SELECTOR_OUTPUT_SCHEMA_VERSION = (
    "rwkv-lh.native-exact-tool-selector-output.v1"
)
NATIVE_SELECTOR_DECODER_ID = "rwkv_lh_g1j_selector_native_trie_v1"
NATIVE_SELECTOR_DECODER_PROTOCOL = "rwkv-lh.native-eligible-suffix-trie.v1"


def _sha256(value: str, name: str) -> str:
    selected = str(value or "")
    if len(selected) != 64 or any(
        character not in "0123456789abcdef" for character in selected
    ):
        raise ValueError(f"native Selector {name} must be lowercase SHA-256")
    return selected


@dataclass(frozen=True)
class NativeNetworkToolSelection:
    """Immutable native eligible-trie decision with vocabulary-logit evidence."""

    selection_id: str
    trace_id: str
    selected_operation: str
    input_digest: str
    menu_digest: str
    selector_checkpoint_id: str
    input_token_count: int
    model: str
    model_sha256: str
    decoder_id: str
    decoder_sha256: str
    decoder_protocol: str
    profile_id: str
    profile_sha256: str
    decoder_trace: Mapping[str, Any]
    eligible_labels: tuple[str, ...] = NETWORK_EXACT_TOOL_LABELS
    schema_version: str = NATIVE_SELECTOR_OUTPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != NATIVE_SELECTOR_OUTPUT_SCHEMA_VERSION:
            raise ValueError("unsupported native Selector output schema")
        required = (
            self.selection_id,
            self.trace_id,
            self.selector_checkpoint_id,
            self.model,
            self.decoder_id,
            self.decoder_protocol,
            self.profile_id,
        )
        if any(not str(value or "").strip() for value in required):
            raise ValueError("native Selector output identity fields must be non-empty")
        _sha256(self.input_digest, "input digest")
        _sha256(self.menu_digest, "menu digest")
        _sha256(self.model_sha256, "model digest")
        _sha256(self.decoder_sha256, "decoder digest")
        _sha256(self.profile_sha256, "profile digest")
        if self.input_token_count < 1:
            raise ValueError("native Selector input token count must be positive")
        eligible = tuple(str(item) for item in self.eligible_labels)
        if not eligible or len(set(eligible)) != len(eligible):
            raise ValueError("native Selector eligible labels must be unique")
        if set(eligible) - set(NETWORK_EXACT_TOOL_LABELS):
            raise ValueError("native Selector eligible labels contain unknown values")
        expected = tuple(
            label for label in NETWORK_EXACT_TOOL_LABELS if label in set(eligible)
        )
        if eligible != expected:
            raise ValueError("native Selector eligible labels differ from class order")
        object.__setattr__(self, "eligible_labels", eligible)
        selected = validate_network_label(self.selected_operation)
        if selected not in eligible:
            raise ValueError("native Selector selected an ineligible operation")
        trace = dict(self.decoder_trace)
        if (
            trace.get("schema_version")
            != "rwkv-lh.native-role-suffix-selection.v1"
            or trace.get("selected_label") != selected
            or tuple(str(item) for item in trace.get("candidate_labels") or ())
            != eligible
            or not isinstance(trace.get("decisions"), list)
            or not trace.get("decisions")
        ):
            raise ValueError("native Selector decoder trace is inconsistent")
        object.__setattr__(self, "decoder_trace", trace)

    @property
    def decoder_trace_sha256(self) -> str:
        return canonical_digest(dict(self.decoder_trace))

    def raw_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "selection_id": self.selection_id,
            "trace_id": self.trace_id,
            "class_order": list(NETWORK_EXACT_TOOL_LABELS),
            "eligible_labels": list(self.eligible_labels),
            "selection_rule": "native_eligible_suffix_trie_vocab_argmax",
            "selected_operation": self.selected_operation,
            "input_digest": self.input_digest,
            "menu_digest": self.menu_digest,
            "selector_checkpoint_id": self.selector_checkpoint_id,
            "input_token_count": self.input_token_count,
            "state_policy": "fresh_initial_state_per_evaluation",
            "model": self.model,
            "model_sha256": self.model_sha256,
            "decoder_id": self.decoder_id,
            "decoder_sha256": self.decoder_sha256,
            "decoder_protocol": self.decoder_protocol,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "decoder_trace": dict(self.decoder_trace),
            "decoder_trace_sha256": self.decoder_trace_sha256,
            "downstream_decoder_trained": False,
            "postprocessed": False,
            "generated_text": False,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NativeNetworkToolSelection":
        class_order = value.get("class_order")
        if class_order is not None and tuple(str(item) for item in class_order) != (
            NETWORK_EXACT_TOOL_LABELS
        ):
            raise ValueError("native Selector output class order changed")
        trace = value.get("decoder_trace")
        if not isinstance(trace, Mapping):
            raise TypeError("native Selector decoder trace must be an object")
        selected = cls(
            schema_version=str(value.get("schema_version") or ""),
            selection_id=str(value.get("selection_id") or ""),
            trace_id=str(value.get("trace_id") or ""),
            selected_operation=str(value.get("selected_operation") or ""),
            input_digest=str(value.get("input_digest") or ""),
            menu_digest=str(value.get("menu_digest") or ""),
            selector_checkpoint_id=str(
                value.get("selector_checkpoint_id") or ""
            ),
            input_token_count=int(value.get("input_token_count") or 0),
            model=str(value.get("model") or ""),
            model_sha256=str(value.get("model_sha256") or ""),
            decoder_id=str(value.get("decoder_id") or ""),
            decoder_sha256=str(value.get("decoder_sha256") or ""),
            decoder_protocol=str(value.get("decoder_protocol") or ""),
            profile_id=str(value.get("profile_id") or ""),
            profile_sha256=str(value.get("profile_sha256") or ""),
            decoder_trace=dict(trace),
            eligible_labels=tuple(
                str(item) for item in value.get("eligible_labels") or ()
            ),
        )
        if value.get("decoder_trace_sha256") not in {
            None,
            selected.decoder_trace_sha256,
        }:
            raise ValueError("native Selector decoder trace digest mismatch")
        return selected


__all__ = [
    "NATIVE_SELECTOR_DECODER_ID",
    "NATIVE_SELECTOR_DECODER_PROTOCOL",
    "NATIVE_SELECTOR_OUTPUT_SCHEMA_VERSION",
    "NativeNetworkToolSelection",
]
