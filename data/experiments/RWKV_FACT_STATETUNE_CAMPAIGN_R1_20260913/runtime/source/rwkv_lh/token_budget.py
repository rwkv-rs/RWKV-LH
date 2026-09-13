"""RWKV-token-aware counting and bounded text projection."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from rwkv_lh.tokenizer import RWKVTokenizer


VOCAB_PATH = Path(__file__).resolve().parent / "data" / "rwkv_vocab_v20230424.txt"


@lru_cache(maxsize=1)
def tokenizer() -> RWKVTokenizer:
    return RWKVTokenizer(str(VOCAB_PATH))


def get_token_count(text: str) -> int:
    return len(tokenizer().encode(str(text or ""))) if text else 0


def smart_truncate(text: str, max_tokens: int) -> tuple[str, str]:
    value = str(text or "")
    limit = max(1, int(max_tokens))
    tokens = tokenizer().encode(value)
    if len(tokens) <= limit:
        return value, ""
    prefix = tokenizer().decode_bytes(tokens[:limit]).decode("utf-8", errors="ignore")
    split = max(prefix.rfind("\n"), prefix.rfind(" "), prefix.rfind("。"))
    if split >= len(prefix) // 2:
        prefix = prefix[: split + 1]
    return prefix, value[len(prefix) :]


__all__ = ["VOCAB_PATH", "get_token_count", "smart_truncate", "tokenizer"]
