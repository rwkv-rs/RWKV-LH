"""Native vllm-rwkv text transport for the existing Goal Supervisor contracts.

The System/User/Bot rendering matches vllm.tokenizers.rwkv_defaults with
open_think. The role payload and system instruction are supplied unchanged by
the existing Supervisor builder; this module only owns the wire envelope.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.protocol import CompletionResponse, RWKVProtocolError, TextCompletionRequest

BACKEND_PROFILE = "vllm-rwkv-native"
TRANSPORT = "vllm_rwkv_completions"
INPUT_ENVELOPE = "rwkv_native_bot_open_think"
GENERATION_PREFILL = "<think"
STATE_PROFILE_ID = "zero"
STATE_PROFILE_SHA256 = "0" * 64


def build_completion_payload(
    *, model: str, system_prompt: str, payload_text: str, max_tokens: int,
) -> dict[str, Any]:
    prompt = (
        f"System✿{system_prompt}✿\nUser✿{payload_text}✿\nBot✿{GENERATION_PREFILL}"
    )
    body = TextCompletionRequest(
        prompt=prompt, max_tokens=max_tokens, temperature=0.1,
        top_p=1.0, top_k=0, presence_penalty=0.0, frequency_penalty=0.0,
        penalty_decay=0.996, stop=("✿",), stop_token_ids=(0,),
        add_special_tokens=True, return_token_ids=True,
    ).payload(model, sampler_mode="native")
    # Each ordinary completion starts independently from explicit zero State.
    # No Executor sampling context, checkpoint or native State handle is used.
    body["vllm_xargs"] = {
        "rwkv_state_profile": STATE_PROFILE_ID,
        "rwkv_state_profile_sha256": STATE_PROFILE_SHA256,
    }
    return body


def decode_completion(
    data: Mapping[str, Any], *, latency_ms: float, attempts: int,
) -> CompletionResponse:
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], Mapping):
        raise RWKVProtocolError("native Supervisor requires exactly one completion choice")
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        raise RWKVProtocolError(
            f"native Supervisor completion did not finish: {choice.get('finish_reason')!r}"
        )
    raw = choice.get("text")
    if not isinstance(raw, str) or not raw.startswith(">"):
        raise RWKVProtocolError("native Supervisor text must continue the sent <think prefill")
    if data.get("usage") is not None and not isinstance(data["usage"], Mapping):
        raise RWKVProtocolError("native Supervisor usage must be an object")
    for name, tokens in (
        ("prompt_token_ids", data.get("prompt_token_ids")),
        ("token_ids", choice.get("token_ids")),
    ):
        if tokens is not None and (
            not isinstance(tokens, list)
            or any(not isinstance(token, int) or isinstance(token, bool) or token < 0 for token in tokens)
        ):
            raise RWKVProtocolError(f"{name} must be non-negative integer token IDs")
    try:
        return OpenAICompatibleRWKVClient._completion_response(data, latency_ms, attempts)
    except (ValueError, TypeError, OverflowError) as exc:
        raise RWKVProtocolError("native Supervisor response metadata is invalid") from exc
