"""RWKV prompt framing shared by planner, verifier, and final writer."""

from __future__ import annotations

import re
from typing import Any


ASSISTANT_HEADER = "### Assistant"
JSON_CALL_STOP_SUFFIXES = (
    "\n### Tool Output",
    "### Tool Output",
    "\n### User",
    "### User",
    "\n### Assistant",
    "### Assistant",
    "\n**Tool Call:**",
    "\nUser:",
    "\nSystem:",
    "\nAssistant:",
)
_HIDDEN_THOUGHT = re.compile(r"<think>[\s\S]*?</think>", flags=re.IGNORECASE)


def assistant_json_prefix(*, prefill_object: bool = True) -> str:
    prefix = f"{ASSISTANT_HEADER}\n```json\n"
    return prefix + ("{" if prefill_object else "")


def visible_model_text(value: Any) -> str:
    text = str(value or "")
    return _HIDDEN_THOUGHT.sub("", text).replace("</think>", "").strip()


__all__ = ["JSON_CALL_STOP_SUFFIXES", "assistant_json_prefix", "visible_model_text"]
