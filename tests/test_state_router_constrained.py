from __future__ import annotations

from rwkv_lh.state_router.protocol import (
    HEAD_LABELS,
    ContextMode,
    EvidenceState,
    PolicyState,
    RouterInput,
)
from rwkv_lh.tokenizer import RWKVTokenizer
from scripts.evaluate_state_router_constrained_logits_v1 import (
    codes_for,
    constrained_prompt,
)


def test_constrained_scheme_uses_frozen_unique_single_token_codes() -> None:
    tokenizer = RWKVTokenizer()
    router_input = RouterInput(
        mode=ContextMode.FRESH,
        summary=None,
        evidence_state=EvidenceState.NONE,
        policy_state=PolicyState.NETWORK_ALLOWED,
        request="Read local pyproject.toml.",
        trace_id="RTR-C-PROMPT",
    )
    for head, labels in HEAD_LABELS.items():
        codes = codes_for(head)
        assert list(codes) == list(labels)
        assert len(set(codes.values())) == len(labels)
        assert all(len(tokenizer.encode(f" {code}")) == 1 for code in codes.values())
        prompt = constrained_prompt(router_input, head)
        assert prompt.endswith("Code:")
        assert router_input.render() in prompt
        assert "Reply with exactly one allowed code" in prompt
